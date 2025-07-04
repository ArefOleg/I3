#!/usr/bin/env python3
import json
import os
import curses
import textwrap
from curses import wrapper
from collections import namedtuple

# Конфигурация
TASKS_FILE = os.path.expanduser("~/.tasks.json")
COLORS = {
    "low": 1,    # Зеленый
    "medium": 2, # Желтый
    "high": 3,   # Красный
}

# Минимальные размеры окна
MIN_HEIGHT = 10
MIN_WIDTH = 60

# Структура задачи
Task = namedtuple("Task", ["name", "type", "priority"])

def wrap_text(text, width):
    """Разбивает текст на строки с переносом"""
    if not text:
        return [""]
    return textwrap.wrap(text, width=width) or [""]

class TaskManagerTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.tasks = []
        self.selected_idx = 0
        self.top_idx = 0  # Индекс первой отображаемой задачи
        self.task_lines = []  # Количество строк для каждой задачи
        self.load_tasks()
        self.init_curses()
        self.run()

    def init_curses(self):
        # Настройка цветов
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
        
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
                self.tasks = [Task(**task) for task in data]
        except (json.JSONDecodeError, TypeError):
            pass

    def save_tasks(self):
        """Сохранить задачи в файл"""
        with open(TASKS_FILE, "w") as f:
            tasks_data = [{"name": t.name, "type": t.type, "priority": t.priority} for t in self.tasks]
            json.dump(tasks_data, f, indent=2)

    def calculate_layout(self, w):
        """Вычислить параметры отображения"""
        # Ширины колонок
        return {
            "number": 4,
            "name": max(10, w - 40),  # Ширина названия (остальное - под другие колонки)
            "type": 15,
            "priority": 10,
            "spacing": 3  # Пробелы между колонками
        }

    def draw_ui(self):
        """Отрисовать интерфейс"""
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
        self.stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
        
        # Подсказки
        help_text = "↑/↓: Навигация | Ctrl+N: Добавить | Enter: Изменить | Ctrl+D: Удалить | q: Выход"
        self.stdscr.addstr(h-1, 0, help_text, curses.A_DIM)
        
        # Рассчитать параметры отображения
        layout = self.calculate_layout(w)
        name_width = layout["name"]
        
        # Сгенерировать строки для задач
        self.task_lines = []
        visible_tasks = []
        for idx, task in enumerate(self.tasks):
            # Разбить название на строки
            name_lines = wrap_text(task.name, name_width)
            # Обрезать тип задачи
            task_type = task.type[:layout["type"]] + (task.type[layout["type"]:] and "..")
            # Для каждой строки названия создаем отдельную запись
            for i, name_line in enumerate(name_lines):
                visible_tasks.append({
                    "idx": idx,
                    "name": name_line,
                    "type": task_type if i == 0 else "",  # Тип только в первой строке
                    "priority": task.priority if i == 0 else "",  # Приоритет только в первой строке
                    "is_first": i == 0
                })
            self.task_lines.append(len(name_lines))
        
        # Отобразить заголовки таблицы
        if self.tasks:
            header = (f"{'#':<{layout['number']}} "
                      f"{'Название':<{name_width}} "
                      f"{'Тип':<{layout['type']}} "
                      f"{'Приоритет':<{layout['priority']}}")
            self.stdscr.addstr(2, 2, header, curses.A_BOLD)
        
        # Отобразить задачи (только видимую часть)
        current_line = 3
        visible_count = 0
        
        # Определить диапазон отображаемых задач
        start_idx = 0
        for i in range(self.top_idx):
            start_idx += self.task_lines[i]
        end_idx = min(start_idx + h - 4, len(visible_tasks))

        for idx in range(start_idx, end_idx):
            task = visible_tasks[idx]
            actual_idx = task["idx"]
            
            # Определение цвета приоритета
            color = curses.color_pair(COLORS.get(task["priority"], 2))
            if not task["is_first"]:
                color = curses.color_pair(5)  # Дополнительные строки - другим цветом
            
            # Подсветка выбранной задачи
            if actual_idx == self.selected_idx:
                self.stdscr.addstr(current_line, 0, " " * w, curses.color_pair(4))
            
            # Форматирование номера задачи
            number = f"{actual_idx+1}." if task["is_first"] else ""
            
            # Отображение задачи
            task_line = (f"{number:<{layout['number']}} "
                         f"{task['name']:<{name_width}} "
                         f"{task['type']:<{layout['type']}} "
                         f"{task['priority']:<{layout['priority']}}")
            self.stdscr.addstr(current_line, 2, task_line, color)
            
            current_line += 1
            visible_count += 1
            if current_line >= h - 1:
                break
        
        # Показать индикатор прокрутки
        if start_idx > 0:
            self.stdscr.addstr(3, w-2, "↑", curses.A_BOLD)
        if end_idx < len(visible_tasks):
            self.stdscr.addstr(h-2, w-2, "↓", curses.A_BOLD)
        
        # Сообщение, если задач нет
        if not self.tasks:
            no_tasks = "Нет задач. Нажмите Ctrl+N, чтобы добавить новую."
            self.stdscr.addstr(3, (w - len(no_tasks)) // 2, no_tasks)
        
        self.stdscr.refresh()

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

    def select_priority(self):
        """Диалог выбора приоритета"""
        h, w = self.stdscr.getmaxyx()
        
        # Создать окно диалога
        win = curses.newwin(5, 30, h//2, (w-30)//2)
        win.border()
        win.addstr(0, 2, " Выберите приоритет ")
        win.addstr(1, 2, "1. Низкий", curses.color_pair(1))
        win.addstr(2, 2, "2. Средний", curses.color_pair(2))
        win.addstr(3, 2, "3. Высокий", curses.color_pair(3))
        win.refresh()
        
        while True:
            try:
                ch = win.getch()
            except:
                continue
                
            if ch == ord('1'):
                return "low"
            elif ch == ord('2'):
                return "medium"
            elif ch == ord('3'):
                return "high"
            elif ch == 27:  # ESC
                return None

    def add_task(self):
        """Добавить новую задачу"""
        name = self.input_dialog("Название задачи")
        if name is None or not name.strip():
            return
        
        task_type = self.input_dialog("Тип задачи")
        if task_type is None:
            return
        
        priority = self.select_priority()
        if priority is None:
            return
        
        self.tasks.append(Task(name, task_type, priority))
        self.save_tasks()

    def update_task(self):
        """Обновить выбранную задачу"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        task = self.tasks[self.selected_idx]
        
        name = self.input_dialog("Название задачи", task.name)
        if name is None:
            return
        
        task_type = self.input_dialog("Тип задачи", task.type)
        if task_type is None:
            return
        
        priority = self.select_priority()
        if priority is None:
            return
        
        self.tasks[self.selected_idx] = Task(name, task_type, priority)
        self.save_tasks()

    def delete_task(self):
        """Удалить выбранную задачу"""
        if not self.tasks or self.selected_idx >= len(self.tasks):
            return
        
        del self.tasks[self.selected_idx]
        
        # Обновить индекс выбранной задачи
        if self.selected_idx >= len(self.tasks) and self.tasks:
            self.selected_idx = len(self.tasks) - 1
        elif not self.tasks:
            self.selected_idx = 0
            
        self.save_tasks()

    def run(self):
        """Главный цикл приложения"""
        while True:
            self.draw_ui()
            key = self.stdscr.getch()
            
            # Обработка изменения размера окна
            if key == curses.KEY_RESIZE:
                continue
            
            # Навигация
            if key == curses.KEY_UP and self.selected_idx > 0:
                self.selected_idx -= 1
                # Прокрутка вверх, если выбранная задача не видна
                if self.selected_idx < self.top_idx:
                    self.top_idx = self.selected_idx
            elif key == curses.KEY_DOWN and self.selected_idx < len(self.tasks) - 1:
                self.selected_idx += 1
                # Прокрутка вниз, если выбранная задача не видна
                total_lines = sum(self.task_lines[:self.selected_idx+1])
                visible_lines = sum(self.task_lines[self.top_idx:self.selected_idx+1])
                h, w = self.stdscr.getmaxyx()
                if visible_lines > h - 4:
                    self.top_idx += 1
            
            # Прокрутка страницы
            elif key == curses.KEY_PPAGE and self.top_idx > 0:
                self.top_idx = max(0, self.top_idx - 1)
            elif key == curses.KEY_NPAGE:
                h, w = self.stdscr.getmaxyx()
                visible_lines = sum(self.task_lines[self.top_idx:self.top_idx + h - 4])
                if visible_lines < sum(self.task_lines) - 1:
                    self.top_idx += 1
            
            # Горячие клавиши
            elif key == ord('q') or key == ord('Q'):  # Выход
                break
            elif key == 10 or key == curses.KEY_ENTER:  # Enter - редактировать
                self.update_task()
            elif key == 4:  # Ctrl+D - удалить
                self.delete_task()
            elif key == 14:  # Ctrl+N - добавить
                self.add_task()

def main(stdscr):
    curses.use_default_colors()
    app = TaskManagerTUI(stdscr)

if __name__ == "__main__":
    wrapper(main)
