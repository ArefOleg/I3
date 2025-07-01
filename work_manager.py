#!/usr/bin/env python3
import json
import os
import curses
import textwrap
import subprocess
import tempfile
from datetime import datetime
from curses import wrapper
from collections import namedtuple

# Конфигурация
TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task_logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Минимальные размеры окна
MIN_HEIGHT = 15
MIN_WIDTH = 80

# Структура задачи
Task = namedtuple("Task", ["jira_id", "title", "description"])

class TaskManagerTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.tasks = []
        self.selected_idx = 0
        self.top_idx = 0
        self.mode = "task_list"  # Или "task_detail"
        self.task_detail_section = 0  # 0: описание, 1: объекты, 2: логи
        self.object_idx = 0
        self.log_idx = 0
        self.description_scroll = 0
        self.load_tasks()
        self.init_curses()
        self.run()

    def init_curses(self):
        # Настройка цветов
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)     # Информация
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)    # Предупреждение
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)      # Заголовки
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)     # Выделение
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)   # Объекты
        curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)      # Логи
        
        # Оптимизация ввода
        self.stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        curses.curs_set(0)  # Скрыть курсор

    def check_window_size(self):
        """Проверить размер окна"""
        h, w = self.stdscr.getmaxyx()
        return h >= MIN_HEIGHT and w >= MIN_WIDTH

    def load_tasks(self):
        """Загрузить задачи из файла"""
        self.tasks = []
        if not os.path.exists(TASKS_FILE):
            return
        
        try:
            with open(TASKS_FILE, "r") as f:
                data = json.load(f)
                for task in data:
                    # Обеспечим обратную совместимость со старыми задачами
                    if "description" not in task:
                        task["description"] = ""
                    self.tasks.append(Task(task["jira_id"], task["title"], task["description"]))
        except (json.JSONDecodeError, TypeError):
            pass

    def save_tasks(self):
        """Сохранить задачи в файл"""
        with open(TASKS_FILE, "w") as f:
            tasks_data = [{
                "jira_id": t.jira_id, 
                "title": t.title,
                "description": t.description
            } for t in self.tasks]
            json.dump(tasks_data, f, indent=2)

    def load_objects(self, jira_id):
        """Загрузить объекты для задачи"""
        file_path = os.path.join(LOG_DIR, f"{jira_id}_objects.json")
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            return []

    def save_objects(self, jira_id, objects):
        """Сохранить объекты для задачи"""
        file_path = os.path.join(LOG_DIR, f"{jira_id}_objects.json")
        with open(file_path, "w") as f:
            json.dump(objects, f, indent=2)

    def load_logs(self, jira_id):
        """Загрузить логи для задачи"""
        file_path = os.path.join(LOG_DIR, f"{jira_id}_logs.json")
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, TypeError):
            return []

    def save_logs(self, jira_id, logs):
        """Сохранить логи для задачи"""
        file_path = os.path.join(LOG_DIR, f"{jira_id}_logs.json")
        with open(file_path, "w") as f:
            json.dump(logs, f, indent=2)

    def input_dialog(self, title, default=""):
        """Диалог ввода текста"""
        h, w = self.stdscr.getmaxyx()
        
        # Создать окно диалога
        win = curses.newwin(3, 50, h//2, (w-50)//2)
        win.border()
        win.addstr(0, 2, f" {title} ")
        win.refresh()
        
        curses.echo()
        curses.curs_set(1)
        
        input_str = default
        win.addstr(1, 1, input_str)
        win.refresh()
        
        while True:
            try:
                ch = win.getch()
            except:
                continue
                
            if ch == 10:  # Enter
                break
            elif ch == 27:  # ESC
                input_str = None
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                input_str = input_str[:-1]
            elif ch >= 32 and ch <= 126:  # Печатаемые символы
                input_str += chr(ch)
            
            win.move(1, 1)
            win.clrtoeol()
            win.addstr(1, 1, input_str)
            win.refresh()
        
        curses.noecho()
        curses.curs_set(0)
        return input_str

    def edit_with_editor(self, content):
        """Редактирование текста во внешнем редакторе Lite-XL"""
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
            if content:
                tmp.write(content.encode('utf-8'))
                tmp.flush()
        
        # Запускаем редактор
        try:
            subprocess.run(["lite-xl", tmp_path], check=True)
        except subprocess.CalledProcessError:
            return None
        
        # Читаем результат
        try:
            with open(tmp_path, "r") as f:
                return f.read()
        except IOError:
            return None
        finally:
            # Удаляем временный файл
            os.unlink(tmp_path)

    def add_task(self):
        """Добавить новую задачу"""
        jira_id = self.input_dialog("JIRA ID задачи")
        if jira_id is None or not jira_id.strip():
            return
        
        title = self.input_dialog("Название задачи")
        if title is None:
            return
        
        # Добавляем пустое описание - его можно будет заполнить позже
        self.tasks.append(Task(jira_id, title, ""))
        self.save_tasks()

    def update_task(self):
        """Обновить выбранную задачу"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        task = self.tasks[self.selected_idx]
        
        new_jira_id = self.input_dialog("JIRA ID задачи", task.jira_id)
        if new_jira_id is None:
            return
        
        new_title = self.input_dialog("Название задачи", task.title)
        if new_title is None:
            return
        
        # Обновить имя файлов логов при изменении JIRA ID
        if new_jira_id != task.jira_id:
            old_obj_file = os.path.join(LOG_DIR, f"{task.jira_id}_objects.json")
            new_obj_file = os.path.join(LOG_DIR, f"{new_jira_id}_objects.json")
            old_log_file = os.path.join(LOG_DIR, f"{task.jira_id}_logs.json")
            new_log_file = os.path.join(LOG_DIR, f"{new_jira_id}_logs.json")
            
            if os.path.exists(old_obj_file):
                os.rename(old_obj_file, new_obj_file)
            if os.path.exists(old_log_file):
                os.rename(old_log_file, new_log_file)
        
        self.tasks[self.selected_idx] = Task(new_jira_id, new_title, task.description)
        self.save_tasks()

    def edit_description(self):
        """Редактировать описание задачи во внешнем редакторе"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        task = self.tasks[self.selected_idx]
        new_description = self.edit_with_editor(task.description)
        
        if new_description is not None:
            self.tasks[self.selected_idx] = Task(task.jira_id, task.title, new_description)
            self.save_tasks()
            self.description_scroll = 0  # Сбросить прокрутку

    def delete_task(self):
        """Удалить выбранную задачу"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        task = self.tasks[self.selected_idx]
        
        # Удалить связанные файлы
        obj_file = os.path.join(LOG_DIR, f"{task.jira_id}_objects.json")
        log_file = os.path.join(LOG_DIR, f"{task.jira_id}_logs.json")
        
        if os.path.exists(obj_file):
            os.remove(obj_file)
        if os.path.exists(log_file):
            os.remove(log_file)
        
        del self.tasks[self.selected_idx]
        
        # Обновить индекс выбранной задачи
        if self.selected_idx >= len(self.tasks) and self.tasks:
            self.selected_idx = len(self.tasks) - 1
        elif not self.tasks:
            self.selected_idx = 0
            
        self.save_tasks()

    def add_object(self, jira_id):
        """Добавить новый объект"""
        obj_name = self.input_dialog("Новый объект")
        if obj_name is None or not obj_name.strip():
            return
        
        objects = self.load_objects(jira_id)
        objects.append(obj_name)
        self.save_objects(jira_id, objects)

    def delete_object(self, jira_id):
        """Удалить выбранный объект"""
        objects = self.load_objects(jira_id)
        if not objects or self.object_idx >= len(objects):
            return
        
        del objects[self.object_idx]
        
        # Обновить индекс выбранного объекта
        if self.object_idx >= len(objects) and objects:
            self.object_idx = len(objects) - 1
        elif not objects:
            self.object_idx = 0
            
        self.save_objects(jira_id, objects)

    def add_log_entry(self, jira_id):
        """Добавить запись в лог"""
        log_text = self.input_dialog("Запись в лог")
        if log_text is None or not log_text.strip():
            return
        
        logs = self.load_logs(jira_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Найти или создать запись для сегодняшнего дня
        today_log = next((log for log in logs if log["date"] == today), None)
        if not today_log:
            today_log = {"date": today, "entries": []}
            logs.append(today_log)
        
        today_log["entries"].append(log_text)
        self.save_logs(jira_id, logs)

    def draw_task_list(self):
        """Отрисовать список задач"""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Проверить размер окна
        if not self.check_window_size():
            msg = f"Минимальный размер: {MIN_WIDTH}x{MIN_HEIGHT}"
            self.stdscr.addstr(0, 0, msg, curses.A_BOLD)
            self.stdscr.refresh()
            return
            
        # Заголовок
        title = " Arch Linux Task Manager "
        self.stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
        
        # Подсказки
        help_text = "↑/↓: Навигация | Ctrl+N: Добавить | Ctrl+U: Обновить | Ctrl+D: Удалить | Enter: Детали | q: Выход"
        self.stdscr.addstr(h-1, 0, help_text, curses.A_DIM)
        
        # Заголовки таблицы
        if self.tasks:
            header = f"{'#':<4} {'JIRA ID':<15} {'Название задачи':<50}"
            self.stdscr.addstr(2, 2, header, curses.A_BOLD)
        
        # Список задач
        for idx, task in enumerate(self.tasks[self.top_idx:]):
            line_idx = idx + self.top_idx
            if 3 + idx >= h - 1:  # Не помещается на экран
                break
                
            # Подсветка выбранной строки
            if line_idx == self.selected_idx:
                self.stdscr.addstr(3 + idx, 0, " " * w, curses.color_pair(4))
            
            # Отображение задачи
            task_line = f"{line_idx+1:<4} {task.jira_id:<15} {task.title[:50]:<50}"
            self.stdscr.addstr(3 + idx, 2, task_line)
        
        # Показать индикатор прокрутки
        if self.top_idx > 0:
            self.stdscr.addstr(3, w-2, "↑", curses.A_BOLD)
        if len(self.tasks) > self.top_idx + (h - 4):
            self.stdscr.addstr(h-2, w-2, "↓", curses.A_BOLD)
        
        # Сообщение, если задач нет
        if not self.tasks:
            no_tasks = "Нет задач. Нажмите Ctrl+N, чтобы добавить новую."
            self.stdscr.addstr(3, (w - len(no_tasks)) // 2, no_tasks)
        
        self.stdscr.refresh()

    def draw_task_detail(self):
        """Отрисовать детали задачи"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        task = self.tasks[self.selected_idx]
        objects = self.load_objects(task.jira_id)
        logs = self.load_logs(task.jira_id)
        
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Заголовок
        title = f" Детали задачи: {task.jira_id} "
        self.stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
        
        # Подсказки
        help_text = "↑/↓: Навигация | Enter: Выбрать | Ctrl+N: Добавить/Редактировать | Ctrl+D: Удалить | Esc: Назад"
        self.stdscr.addstr(h-1, 0, help_text, curses.A_DIM)
        
        # Разделы
        sections = [
            "Описание задачи",
            f"Измененные/новые объекты ({len(objects)})",
            f"Лог разработки ({len(logs)})"
        ]
        
        # Отображение разделов
        for idx, section in enumerate(sections):
            # Подсветка выбранного раздела
            if idx == self.task_detail_section:
                self.stdscr.addstr(2 + idx, 2, ">" + section, curses.A_BOLD)
            else:
                self.stdscr.addstr(2 + idx, 2, " " + section)
        
        # Отображение содержимого раздела
        if self.task_detail_section == 0:  # Описание
            # Индикатор редактирования
            edit_hint = "Ctrl+N: Редактировать описание" if task.description else "Ctrl+N: Добавить описание"
            self.stdscr.addstr(2, w - len(edit_hint) - 2, edit_hint, curses.A_DIM)
            
            if task.description:
                # Разбиваем описание на строки с переносом
                desc_lines = []
                for line in task.description.split('\n'):
                    desc_lines.extend(textwrap.wrap(line, width=w-4))
                
                # Прокрутка описания
                max_scroll = max(0, len(desc_lines) - (h - 6))
                self.description_scroll = min(self.description_scroll, max_scroll)
                
                # Отображаем видимую часть описания
                start_line = self.description_scroll
                end_line = min(start_line + (h - 6), len(desc_lines))
                
                for i, line in enumerate(desc_lines[start_line:end_line]):
                    self.stdscr.addstr(6 + i, 2, line, curses.color_pair(1))
            else:
                no_desc = "Описание отсутствует. Нажмите Ctrl+N, чтобы добавить."
                self.stdscr.addstr(6, (w - len(no_desc)) // 2, no_desc, curses.color_pair(2))
        
        elif self.task_detail_section == 1:  # Объекты
            for idx, obj in enumerate(objects):
                if 6 + idx >= h - 1:
                    break
                prefix = ">" if idx == self.object_idx else " "
                self.stdscr.addstr(6 + idx, 2, f"{prefix}{idx+1}. {obj}", curses.color_pair(5))
        
        elif self.task_detail_section == 2:  # Логи
            today = datetime.now().strftime("%Y-%m-%d")
            for idx, log in enumerate(logs):
                if 6 + idx >= h - 1:
                    break
                
                # Подсветка сегодняшней даты
                color = curses.color_pair(6) | curses.A_BOLD if log["date"] == today else curses.color_pair(6)
                prefix = ">" if idx == self.log_idx else " "
                
                # Отобразить дату и количество записей
                log_line = f"{prefix}{log['date']} ({len(log['entries'])})"
                self.stdscr.addstr(6 + idx, 2, log_line, color)
                
                # Отобразить последнюю запись
                if log["entries"] and 6 + idx < h - 2:
                    last_entry = log["entries"][-1][:w-20]
                    self.stdscr.addstr(6 + idx, 25, f"- {last_entry}", color)
        
        self.stdscr.refresh()

    def run(self):
        """Главный цикл приложения"""
        while True:
            if not self.check_window_size():
                # Обработка слишком маленького окна
                self.stdscr.clear()
                msg = f"Минимальный размер: {MIN_WIDTH}x{MIN_HEIGHT}"
                self.stdscr.addstr(0, 0, msg, curses.A_BOLD)
                self.stdscr.refresh()
                key = self.stdscr.getch()
                if key == ord('q'):
                    break
                continue
            
            if self.mode == "task_list":
                self.draw_task_list()
            elif self.mode == "task_detail":
                self.draw_task_detail()
            
            key = self.stdscr.getch()
            
            # Обработка изменения размера окна
            if key == curses.KEY_RESIZE:
                continue
            
            # Режим списка задач
            if self.mode == "task_list":
                # Навигация
                if key == curses.KEY_UP and self.selected_idx > 0:
                    self.selected_idx -= 1
                    if self.selected_idx < self.top_idx:
                        self.top_idx = self.selected_idx
                elif key == curses.KEY_DOWN and self.selected_idx < len(self.tasks) - 1:
                    self.selected_idx += 1
                    if self.selected_idx >= self.top_idx + (curses.LINES - 4):
                        self.top_idx += 1
                
                # Прокрутка страницы
                elif key == curses.KEY_PPAGE and self.top_idx > 0:
                    self.top_idx = max(0, self.top_idx - (curses.LINES - 4))
                    self.selected_idx = self.top_idx
                elif key == curses.KEY_NPAGE:
                    self.top_idx = min(len(self.tasks) - 1, self.top_idx + (curses.LINES - 4))
                    self.selected_idx = min(len(self.tasks) - 1, self.selected_idx + (curses.LINES - 4))
                
                # Горячие клавиши
                elif key == ord('q'):  # Выход
                    break
                elif key == 10 or key == curses.KEY_ENTER:  # Enter - детали задачи
                    if self.tasks:
                        self.mode = "task_detail"
                        self.task_detail_section = 0
                        self.object_idx = 0
                        self.log_idx = 0
                        self.description_scroll = 0
                elif key == 14:  # Ctrl+N - добавить
                    self.add_task()
                elif key == 21:  # Ctrl+U - обновить
                    self.update_task()
                elif key == 4:  # Ctrl+D - удалить
                    self.delete_task()
            
            # Режим деталей задачи
            elif self.mode == "task_detail":
                # Навигация по разделам
                if key == curses.KEY_UP:
                    if self.task_detail_section == 0 and self.description_scroll > 0:
                        self.description_scroll -= 1
                    elif self.task_detail_section > 0:
                        self.task_detail_section -= 1
                        self.object_idx = 0
                        self.log_idx = 0
                elif key == curses.KEY_DOWN:
                    if self.task_detail_section == 0:
                        # Проверяем, есть ли куда прокручивать
                        task = self.tasks[self.selected_idx]
                        if task.description:
                            h, w = self.stdscr.getmaxyx()
                            desc_lines = []
                            for line in task.description.split('\n'):
                                desc_lines.extend(textwrap.wrap(line, width=w-4))
                            if self.description_scroll < len(desc_lines) - (h - 6):
                                self.description_scroll += 1
                    elif self.task_detail_section < 2:
                        self.task_detail_section += 1
                        self.object_idx = 0
                        self.log_idx = 0
                
                # Навигация внутри раздела
                task = self.tasks[self.selected_idx]
                objects = self.load_objects(task.jira_id)
                logs = self.load_logs(task.jira_id)
                
                if key == curses.KEY_UP:
                    if self.task_detail_section == 1 and self.object_idx > 0:
                        self.object_idx -= 1
                    elif self.task_detail_section == 2 and self.log_idx > 0:
                        self.log_idx -= 1
                elif key == curses.KEY_DOWN:
                    if self.task_detail_section == 1 and self.object_idx < len(objects) - 1:
                        self.object_idx += 1
                    elif self.task_detail_section == 2 and self.log_idx < len(logs) - 1:
                        self.log_idx += 1
                
                # Выбор раздела/действия
                elif key == 10 or key == curses.KEY_ENTER:
                    if self.task_detail_section == 1 and objects:
                        # Просмотр объектов
                        pass
                    elif self.task_detail_section == 2 and logs:
                        # Просмотр логов
                        pass
                
                # Добавление/редактирование
                elif key == 14:  # Ctrl+N
                    if self.task_detail_section == 0:  # Редактировать описание
                        self.edit_description()
                    elif self.task_detail_section == 1:  # Добавить объект
                        self.add_object(task.jira_id)
                    elif self.task_detail_section == 2:  # Добавить запись в лог
                        self.add_log_entry(task.jira_id)
                
                # Удаление
                elif key == 4:  # Ctrl+D
                    if self.task_detail_section == 1:  # Удалить объект
                        self.delete_object(task.jira_id)
                    elif self.task_detail_section == 2:  # Удалить лог
                        # Реализация удаления лога
                        pass
                
                # Возврат в список задач
                elif key == 27:  # ESC
                    self.mode = "task_list"
            
            # Выход по Ctrl+C
            elif key == 3:
                break

def main(stdscr):
    curses.use_default_colors()
    app = TaskManagerTUI(stdscr)

if __name__ == "__main__":
    wrapper(main)
