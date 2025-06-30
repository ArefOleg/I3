#!/usr/bin/env python3
import json
import os
import sys
from collections import namedtuple

# Конфигурация
TASKS_FILE = os.path.expanduser("~/.tasks.json")
COLOR_RESET = "\033[0m"
COLORS = {
    "low": "\033[92m",    # Зеленый
    "medium": "\033[93m", # Желтый
    "high": "\033[91m",   # Красный
}

# Структура задачи
Task = namedtuple("Task", ["name", "type", "priority"])

def load_tasks():
    """Загрузить задачи из файла"""
    if not os.path.exists(TASKS_FILE):
        return []
    
    with open(TASKS_FILE, "r") as f:
        try:
            data = json.load(f)
            return [Task(**task) for task in data]
        except json.JSONDecodeError:
            return []

def save_tasks(tasks):
    """Сохранить задачи в файл"""
    with open(TASKS_FILE, "w") as f:
        json.dump([task._asdict() for task in tasks], f, indent=2)

def print_tasks(tasks):
    """Вывести задачи в виде таблицы с цветами"""
    if not tasks:
        print("Нет задач")
        return
    
    # Заголовок таблицы
    print(f"{'№':<5}{'Имя':<20}{'Тип':<15}{'Приоритет':<10}")
    print("-" * 50)
    
    # Вывод задач
    for i, task in enumerate(tasks, 1):
        color = COLORS.get(task.priority, COLOR_RESET)
        print(f"{i:<5}{task.name:<20}{task.type:<15}{color}{task.priority:<10}{COLOR_RESET}")

def add_task(tasks, name, task_type, priority):
    """Добавить новую задачу"""
    if priority not in COLORS:
        print(f"Ошибка: Недопустимый приоритет. Допустимые значения: {', '.join(COLORS.keys())}")
        return False
    
    tasks.append(Task(name, task_type, priority))
    save_tasks(tasks)
    print(f"Задача добавлена: {name}")
    return True

def done_task(tasks, task_num):
    """Удалить задачу по номеру"""
    try:
        task_idx = int(task_num) - 1
        if 0 <= task_idx < len(tasks):
            removed = tasks.pop(task_idx)
            save_tasks(tasks)
            print(f"Задача удалена: {removed.name}")
            return True
        else:
            print("Ошибка: Неверный номер задачи")
    except ValueError:
        print("Ошибка: Номер задачи должен быть числом")
    return False

def update_task(tasks, task_num, name, task_type, priority):
    """Обновить существующую задачу"""
    if priority not in COLORS:
        print(f"Ошибка: Недопустимый приоритет. Допустимые значения: {', '.join(COLORS.keys())}")
        return False
    
    try:
        task_idx = int(task_num) - 1
        if 0 <= task_idx < len(tasks):
            tasks[task_idx] = Task(name, task_type, priority)
            save_tasks(tasks)
            print(f"Задача обновлена: {name}")
            return True
        else:
            print("Ошибка: Неверный номер задачи")
    except ValueError:
        print("Ошибка: Номер задачи должен быть числом")
    return False

def main():
    tasks = load_tasks()
    
    if len(sys.argv) < 2:
        print_tasks(tasks)
        return
    
    command = sys.argv[1].lower()
    
    if command == "add" and len(sys.argv) == 5:
        add_task(tasks, sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "done" and len(sys.argv) == 3:
        done_task(tasks, sys.argv[2])
    elif command == "update" and len(sys.argv) == 6:
        update_task(tasks, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif command == "list":
        print_tasks(tasks)
    else:
        print("Использование:")
        print("  Добавить задачу:   add <имя> <тип> <приоритет>")
        print("  Удалить задачу:    done <номер>")
        print("  Обновить задачу:   update <номер> <имя> <тип> <приоритет>")
        print("  Показать задачи:   list")
        print("\nПримеры:")
        print("  ./task_manager.py add 'Написать код' 'Работа' 'high'")
        print("  ./task_manager.py done 2")
        print("  ./task_manager.py update 3 'Новое имя' 'Личное' 'medium'")

if __name__ == "__main__":
    main()
