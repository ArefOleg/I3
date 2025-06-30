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

# Структура задачи
Task = namedtuple("Task", ["name", "type", "priority"])

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
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)   # выделение
        
        # Оптимизация ввода
        self.stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        curses.curs_set(0)  # Скрыть курсор

    def load_tasks(self):
        """Загрузить задачи из файла"""
        self.tasks = []
        if not os.path.exists(TASKS_FILE):
            return
        
        try:
            with open(TASKS_FILE, "r") as f:
                data = json.load(f)
                self.tasks = [Task(**task) for task in data]
        except json.JSONDecodeError:
            pass

    def save_tasks(self):
        """Сохранить задачи в файл"""
        with open(TASKS_FILE, "w") as f:
            json.dump([task._asdict() for task in self.tasks], f, indent=2)

    def draw_ui(self):
        """Отрисовать интерфейс"""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Заголовок
        title = " Arch Linux Task Manager "
        self.stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD)
        
        # Подсказки
        help_text = "↑/↓: Навигация | Ctrl+N: Добавить | Enter: Изменить | Ctrl+D: Удалить | q: Выход"
        self.stdscr.addstr(h-1, 0, help_text, curses.A_DIM)
        
        # Заголовки таблицы
        if self.tasks:
            header = f"{'#':<4} {'Название':<30} {'Тип':<20} {'Приоритет':<10}"
            self.stdscr.addstr(2, 2, header, curses.A_BOLD)
        
        # Список задач
        for idx, task in enumerate(self.tasks):
            # Определение цвета приоритета
            color = curses.color_pair(COLORS[task.priority])
            
            # Подсветка выбранной строки
            if idx == self.selected_idx:
                self.stdscr.addstr(3 + idx, 0, " " * w, curses.color_pair(4))
            
            # Отображение задачи
            task_line = f"{idx+1:<4} {task.name:<30} {task.type:<20} {task.priority:<10}"
            self.stdscr.addstr(3 + idx, 2, task_line, color | (curses.A_BOLD if idx == self.selected_idx else 0))
        
        # Сообщение, если задач нет
        if not self.tasks:
            no_tasks = "Нет задач. Нажмите Ctrl+N, чтобы добавить новую."
            self.stdscr.addstr(3, (w - len(no_tasks)) // 2, no_tasks)
        
        self.stdscr.refresh()

    def input_dialog(self, title, default=""):
        """Диалог ввода текста"""
        h, w = self.stdscr.getmaxyx()
        win = curses.newwin(3, 50, h//2, (w-50)//2)
        win.border()
        win.addstr(0, 2, f" {title} ")
        win.refresh()
        
        curses.echo()
        curses.curs_set(1)
        win.move(1, 1)
        win.clrtoeol()
        
        input_str = ""
        while True:
            ch = win.getch()
            if ch == 10:  # Enter
                break
            elif ch == 27:  # ESC
                input_str = None
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                input_str = input_str[:-1]
            else:
                input_str += chr(ch)
            
            win.move(1, 1)
            win.clrtoeol()
            win.addstr(1, 1, input_str)
        
        curses.noecho()
        curses.curs_set(0)
        return input_str

    def select_priority(self):
        """Диалог выбора приоритета"""
        h, w = self.stdscr.getmaxyx()
        win = curses.newwin(5, 30, h//2, (w-30)//2)
        win.border()
        win.addstr(0, 2, " Выберите приоритет ")
        win.addstr(1, 2, "1. Низкий", curses.color_pair(1))
        win.addstr(2, 2, "2. Средний", curses.color_pair(2))
        win.addstr(3, 2, "3. Высокий", curses.color_pair(3))
        win.refresh()
        
        while True:
            ch = win.getch()
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
        if name is None or name.strip() == "":
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
        if not self.tasks:
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
        if not self.tasks:
            return
        
        del self.tasks[self.selected_idx]
        if self.selected_idx >= len(self.tasks) and self.selected_idx > 0:
            self.selected_idx = len(self.tasks) - 1
        self.save_tasks()

    def run(self):
        """Главный цикл приложения"""
        while True:
            self.draw_ui()
            key = self.stdscr.getch()
            
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

def main(stdscr):
    app = TaskManagerTUI(stdscr)

if __name__ == "__main__":
    wrapper(main)
