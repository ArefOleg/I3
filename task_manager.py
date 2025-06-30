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
            tasks_data = [{"name": t.name, "type": t.type, "priority": t.priority}
