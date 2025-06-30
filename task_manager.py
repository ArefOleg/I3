#!/usr/bin/env python3
import json
import os
import curses
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

def safe_addstr(win, y, x, text, attr=0):
    """Безопасный вывод текста с проверкой границ экрана"""
    height, width = win.getmaxyx()
    if y < 0 or y >= height or x >= width:
        return
    
    # Обрезаем текст, чтобы он помещался в строку
    text = text[:max(0, width - x - 1)]
    try:
        win.addstr(y, max(0, x), text, attr)
    except curses.error:
        pass

class TaskManagerTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.tasks = []
        self.selected_idx = 0
        self.load_tasks()
        self.init_curses()
        self.run()

    def init_curses(self):
        # Настройка цветов
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)    # low
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # medium
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)      # high
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)    # выделение
        
        # Оптимизация ввода
        self.stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        curses.curs_set(0)  # Скрыть курсор
        self.stdscr.timeout(100)  # Неблокирующее чтение с таймаутом

    def check_window_size(self):
        """Проверить размер окна и вывести сообщение, если слишком мало"""
        h, w = self.stdscr.getmaxyx()
        if h < MIN_HEIGHT or w < MIN_WIDTH:
            self.stdscr.clear()
            msg = f"Слишком маленькое окно! Минимум: {MIN_WIDTH}x{MIN_HEIGHT}"
            safe_addstr(self.stdscr, h//2, max(0, (w - len(msg))//2), msg, curses.A_BOLD)
            self.stdscr.refresh()
            return False
        return True

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
            # Преобразуем namedtuple в словари
            tasks_data = [{"name": t.name, "type": t.type, "priority": t.priority} for t in self.tasks]
            json.dump(tasks_data, f, indent=2)

    def draw_ui(self):
        """Отрисовать интерфейс"""
        # Проверить размер окна
        if not self.check_window_size():
            return
            
        h, w = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # Заголовок
        title = " Arch Linux Task Manager "
        safe_addstr(self.stdscr, 0, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
        
        # Подсказки
        help_text = "↑/↓: Навигация | Ctrl+N: Добавить | Enter: Изменить | Ctrl+D: Удалить | q: Выход"
        if h > 1:
            safe_addstr(self.stdscr, h-1, 0, help_text[:w-1], curses.A_DIM)
        
        # Заголовки таблицы
        if self.tasks and h > 4:
            header = f"{'#':<4} {'Название':<30} {'Тип':<20} {'Приоритет':<10}"
            safe_addstr(self.stdscr, 2, 2, header[:w-3], curses.A_BOLD)
        
        # Список задач
        max_visible = max(0, h - 4)
        visible_tasks = self.tasks[:max_visible]
        
        for idx, task in enumerate(visible_tasks):
            line_y = 3 + idx
            # Проверка, что строка в пределах экрана
            if line_y >= h:
                break
                
            # Определение цвета приоритета
            color = curses.color_pair(COLORS.get(task.priority, 2))
            
            # Подсветка выбранной строки
            if idx == self.selected_idx:
                try:
                    self.stdscr.addstr(line_y, 0, " " * w, curses.color_pair(4))
                except curses.error:
                    pass
            
            # Отображение задачи
            task_line = f"{idx+1:<4} {task.name[:25]:<30} {task.type[:15]:<20} {task.priority:<10}"
            safe_addstr(self.stdscr, line_y, 2, task_line[:w-3], color)
        
        # Сообщение, если задач нет
        if not self.tasks and h > 3:
            no_tasks = "Нет задач. Нажмите Ctrl+N, чтобы добавить новую."
            safe_addstr(self.stdscr, 3, max(0, (w - len(no_tasks)) // 2), no_tasks[:w-1])
        
        self.stdscr.refresh()

    def input_dialog(self, title, default=""):
        """Диалог ввода текста"""
        # Проверить размер окна
        if not self.check_window_size():
            return None
            
        h, w = self.stdscr.getmaxyx()
        # Убедиться, что диалог помещается
        if h < 5 or w < 50:
            return None
            
        # Создать окно диалога
        dialog_h = 3
        dialog_w = min(50, w-4)
        y = max(0, (h - dialog_h) // 2)
        x = max(0, (w - dialog_w) // 2)
        
        try:
            win = curses.newwin(dialog_h, dialog_w, y, x)
            win.border()
            safe_addstr(win, 0, 2, f" {title} ", curses.A_BOLD)
            win.refresh()
        except curses.error:
            return None
        
        curses.echo()
        curses.curs_set(1)
        
        input_str = default
        win.move(1, 1)
        win.clrtobot()
        safe_addstr(win, 1, 1, input_str)
        win.refresh()
        
        while True:
            try:
                ch = win.getch()
            except curses.error:
                continue
                
            if ch == 10:  # Enter
                break
            elif ch == 27:  # ESC
                input_str = None
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                input_str = input_str[:-1]
            elif ch >= 32 and ch <= 126:  # Только печатаемые символы
                if len(input_str) < dialog_w - 2:
                    input_str += chr(ch)
            
            win.move(1, 1)
            win.clrtoeol()
            safe_addstr(win, 1, 1, input_str)
            win.refresh()
        
        curses.noecho()
        curses.curs_set(0)
        return input_str

    def select_priority(self):
        """Диалог выбора приоритета"""
        # Проверить размер окна
        if not self.check_window_size():
            return None
            
        h, w = self.stdscr.getmaxyx()
        # Убедиться, что диалог помещается
        if h < 7 or w < 30:
            return None
            
        # Создать окно диалога
        dialog_h = 5
        dialog_w = min(30, w-4)
        y = max(0, (h - dialog_h) // 2)
        x = max(0, (w - dialog_w) // 2)
        
        try:
            win = curses.newwin(dialog_h, dialog_w, y, x)
            win.border()
            safe_addstr(win, 0, 2, " Выберите приоритет ", curses.A_BOLD)
            safe_addstr(win, 1, 2, "1. Низкий", curses.color_pair(1))
            safe_addstr(win, 2, 2, "2. Средний", curses.color_pair(2))
            safe_addstr(win, 3, 2, "3. Высокий", curses.color_pair(3))
            win.refresh()
        except curses.error:
            return None
        
        while True:
            try:
                ch = win.getch()
            except curses.error:
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
            try:
                self.draw_ui()
                key = self.stdscr.getch()
                
                # Обработка изменения размера окна
                if key == curses.KEY_RESIZE:
                    curses.resizeterm(*self.stdscr.getmaxyx())
                    continue
                
                # Навигация
                if key == curses.KEY_UP and self.selected_idx > 0:
                    self.selected_idx -= 1
                elif key == curses.KEY_DOWN and self.selected_idx < len(self.tasks) - 1:
                    self.selected_idx += 1
                
                # Горячие клавиши
                elif key == ord('q') or key == ord('Q'):  # Выход
                    break
                elif key == 10 or key == curses.KEY_ENTER:  # Enter - редактировать
                    self.update_task()
                elif key == 4:  # Ctrl+D - удалить
                    self.delete_task()
                elif key == 14:  # Ctrl+N - добавить
                    self.add_task()
                    
            except Exception as e:
                # В случае любой ошибки продолжить работу
                with open("task_manager_error.log", "a") as f:
                    f.write(f"Error: {str(e)}\n")
                continue

def main(stdscr):
    # Включить обработку изменения размера окна
    curses.use_default_colors()
    if curses.has_colors():
        curses.start_color()
    
    # Инициализировать экран
    stdscr.clear()
    stdscr.refresh()
    
    # Запустить приложение
    app = TaskManagerTUI(stdscr)

if __name__ == "__main__":
    try:
        wrapper(main)
    except Exception as e:
        with open("task_manager_crash.log", "w") as f:
            f.write(f"Critical error: {str(e)}\n")
        # Попытка восстановить терминал
        os.system('reset')
