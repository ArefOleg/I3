#!/usr/bin/env python3
import sqlite3
import datetime
import curses
import curses.textpad

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Таблица задач
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_date TEXT NOT NULL,
                description TEXT)''')
    
    # Таблица объектов
    c.execute('''CREATE TABLE IF NOT EXISTS task_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                created_date TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id))''')
    
    # Проверяем существование колонок для tasks
    c.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in c.fetchall()]
    if 'description' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
    
    # Проверяем существование колонки name для task_objects
    c.execute("PRAGMA table_info(task_objects)")
    columns = [col[1] for col in c.fetchall()]
    if 'name' not in columns:
        c.execute("ALTER TABLE task_objects ADD COLUMN name TEXT NOT NULL DEFAULT 'Unnamed'")
    
    conn.commit()
    return conn

class TaskManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.conn = init_db()
        self.tasks = []
        self.selected_idx = 0
        self.load_tasks()
        
    def load_tasks(self):
        c = self.conn.cursor()
        c.execute("SELECT id, name, created_date, description FROM tasks ORDER BY datetime(created_date) DESC")
        self.tasks = c.fetchall()
        
    def create_task(self):
        # Запрос ID
        self.show_message("Enter task ID (any characters): ")
        curses.curs_set(1)
        self.stdscr.move(curses.LINES - 1, len("Enter task ID (any characters): "))
        curses.echo()
        task_id = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        
        if not task_id:
            curses.curs_set(0)
            return
            
        # Проверка уникальности ID
        if any(task[0] == task_id for task in self.tasks):
            self.show_message(f"ID '{task_id}' already exists! Press any key.")
            self.stdscr.getch()
            curses.curs_set(0)
            return

        # Запрос названия задачи
        self.show_message("Enter task name: ")
        self.stdscr.move(curses.LINES - 1, len("Enter task name: "))
        curses.echo()
        name = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        
        if name:
            created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c = self.conn.cursor()
            try:
                c.execute("INSERT INTO tasks (id, name, created_date, description) VALUES (?, ?, ?, ?)", 
                         (task_id, name, created_date, ""))
                self.conn.commit()
                self.load_tasks()
                self.selected_idx = 0
            except sqlite3.Error as e:
                self.show_message(f"Error: {str(e)}. Press any key.")
                self.stdscr.getch()

    def update_task(self):
        if not self.tasks:
            return
            
        task_id = self.tasks[self.selected_idx][0]
        self.show_message(f"Update task (current: {self.tasks[self.selected_idx][1]}): ")
        curses.curs_set(1)
        self.stdscr.move(curses.LINES - 1, len(f"Update task (current: {self.tasks[self.selected_idx][1]}): "))
        curses.echo()
        new_name = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        
        if new_name:
            c = self.conn.cursor()
            c.execute("UPDATE tasks SET name = ? WHERE id = ?", (new_name, task_id))
            self.conn.commit()
            self.load_tasks()

    def delete_task(self):
        if not self.tasks:
            return
            
        task_id = self.tasks[self.selected_idx][0]
        c = self.conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        prev_len = len(self.tasks)
        self.load_tasks()
        
        if prev_len > 0:
            if self.selected_idx >= len(self.tasks):
                self.selected_idx = max(0, len(self.tasks) - 1)

    def edit_description(self, task_id):
        # Получаем текущее описание
        c = self.conn.cursor()
        c.execute("SELECT description FROM tasks WHERE id = ?", (task_id,))
        result = c.fetchone()
        description = result[0] if result else ""

        # Создаем окно для редактирования
        edit_win = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
        edit_win.clear()
        edit_win.addstr(0, 0, "Edit description (Ctrl+G to save, Ctrl+C to cancel):")
        edit_win.refresh()
        
        # Создаем текстовое поле
        text_win = curses.newwin(curses.LINES - 2, curses.COLS - 1, 1, 0)
        if description:
            text_win.addstr(description)
        text_win.refresh()
        
        # Включаем режим редактирования
        textbox = curses.textpad.Textbox(text_win)
        textbox.edit()
        
        # Получаем отредактированный текст
        edited_text = textbox.gather().strip()
        
        # Сохраняем изменения
        c.execute("UPDATE tasks SET description = ? WHERE id = ?", (edited_text, task_id))
        self.conn.commit()
        
        # Обновляем данные в текущем представлении
        return edited_text

    def add_object(self, task_id):
        # Типы объектов
        object_types = [
            "SQL",
            "Applet",
            "Application",
            "Business Component",
            "Business Object",
            "Business Service",
            "Integration Object",
            "Link",
            "Job",
            "Outbound Web Service",
            "Inbound Web Service",
            "Pick List",
            "Task",
            "Table",
            "Screen",
            "View",
            "Workflow Process",
            "Workflow Policy",
            "Product"
        ]
        
        selected_type = 0
        
        # Выбор типа объекта
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(0, 0, f"Select Object Type for Task: {task_id}")
            self.stdscr.addstr(1, 0, "-" * width)
            
            # Отображаем типы объектов
            for i, obj_type in enumerate(object_types):
                if i == selected_type:
                    self.stdscr.attron(curses.A_REVERSE)
                self.stdscr.addstr(2 + i, 2, obj_type)
                if i == selected_type:
                    self.stdscr.attroff(curses.A_REVERSE)
            
            # Подсказки
            footer = "Enter:Select  ↑/↓:Navigate  q:Cancel"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                return
            elif key == curses.KEY_UP:
                if selected_type > 0:
                    selected_type -= 1
            elif key == curses.KEY_DOWN:
                if selected_type < len(object_types) - 1:
                    selected_type += 1
            elif key == 10:  # Enter
                break
        
        # Получили выбранный тип
        obj_type = object_types[selected_type]
        
        # Запрос имени объекта
        self.show_message(f"Enter name for {obj_type}: ")
        curses.curs_set(1)
        self.stdscr.move(curses.LINES - 1, len(f"Enter name for {obj_type}: "))
        curses.echo()
        obj_name = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        
        if not obj_name:
            return
            
        # Редактирование описания объекта
        created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Создаем окно для редактирования
        edit_win = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
        edit_win.clear()
        edit_win.addstr(0, 0, f"Edit description for {obj_type} (Ctrl+G to save, Ctrl+C to cancel):")
        edit_win.refresh()
        
        # Создаем текстовое поле
        text_win = curses.newwin(curses.LINES - 2, curses.COLS - 1, 1, 0)
        text_win.refresh()
        
        # Включаем режим редактирования
        textbox = curses.textpad.Textbox(text_win)
        textbox.edit()
        
        # Получаем отредактированный текст
        description = textbox.gather().strip()
        
        if description:
            # Сохраняем объект
            c = self.conn.cursor()
            try:
                c.execute("""INSERT INTO task_objects 
                          (task_id, object_type, name, description, created_date) 
                          VALUES (?, ?, ?, ?, ?)""", 
                          (task_id, obj_type, obj_name, description, created_date))
                self.conn.commit()
                self.show_message(f"Added {obj_type} to task! Press any key.")
                self.stdscr.getch()
            except sqlite3.Error as e:
                self.show_message(f"Error: {str(e)}. Press any key.")
                self.stdscr.getch()

    def show_list_objects(self, task_id):
        # Получаем объекты для задачи
        c = self.conn.cursor()
        c.execute("""SELECT object_type, name, created_date, description 
                  FROM task_objects 
                  WHERE task_id = ? 
                  ORDER BY created_date DESC""", 
                  (task_id,))
        objects = c.fetchall()
        
        if not objects:
            self.show_message("No objects found for this task. Press any key.")
            self.stdscr.getch()
            return
        
        # Отображаем список объектов
        current_idx = 0
       
