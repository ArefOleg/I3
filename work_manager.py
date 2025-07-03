#!/usr/bin/env python3
import sqlite3
import datetime
import curses
import curses.textpad
import locale

# Устанавливаем локаль для поддержки Unicode
locale.setlocale(locale.LC_ALL, '')
locale.setlocale(locale.LC_CTYPE, ('ru_RU', 'UTF-8'))

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
    
    # Таблица логов разработки
    c.execute('''CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                log_date TEXT NOT NULL,   -- Дата лога в формате 'YYYY-MM-DD'
                content TEXT NOT NULL,    -- Содержимое лога
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
        
        # Включаем режим редактирования с поддержкой UTF-8
        textbox = curses.textpad.Textbox(text_win, insert_mode=True)
        curses.curs_set(1)
        textbox.edit(self.validate_input)
        curses.curs_set(0)
        
        # Получаем отредактированный текст
        edited_text = textbox.gather().strip()
        
        # Сохраняем изменения
        c.execute("UPDATE tasks SET description = ? WHERE id = ?", (edited_text, task_id))
        self.conn.commit()
        
        # Обновляем данные в текущем представлении
        return edited_text

    def validate_input(self, key):
        """Валидатор для поддержки русского ввода"""
        # Разрешаем все печатные символы (включая русские)
        if key >= 32 and key != 0x7f:
            return key
        return key

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
        
        # Шаг 1: Выбор типа объекта
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
        
        # Шаг 2: Ввод имени объекта
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, f"Creating new {obj_type} for task: {task_id}")
        self.stdscr.addstr(1, 0, "-" * width)
        self.stdscr.addstr(2, 0, "Enter object name: ")
        self.stdscr.refresh()
        
        curses.curs_set(1)
        curses.echo()
        self.stdscr.move(2, len("Enter object name: "))
        obj_name = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        
        if not obj_name:
            self.show_message("Object name cannot be empty! Press any key.")
            self.stdscr.getch()
            return
            
        # Шаг 3: Редактирование описания объекта
        created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Создаем окно для редактирования
        edit_win = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
        edit_win.clear()
        edit_win.addstr(0, 0, f"Edit description for {obj_type} '{obj_name}' (Ctrl+G to save, Ctrl+C to cancel):")
        edit_win.refresh()
        
        # Создаем текстовое поле
        text_win = curses.newwin(curses.LINES - 2, curses.COLS - 1, 1, 0)
        text_win.refresh()
        
        # Включаем режим редактирования с поддержкой UTF-8
        textbox = curses.textpad.Textbox(text_win, insert_mode=True)
        curses.curs_set(1)
        textbox.edit(self.validate_input)
        curses.curs_set(0)
        
        # Получаем отредактированный текст
        description = textbox.gather().strip()
        
        # Сохраняем объект
        if description:
            c = self.conn.cursor()
            try:
                c.execute("""INSERT INTO task_objects 
                          (task_id, object_type, name, description, created_date) 
                          VALUES (?, ?, ?, ?, ?)""", 
                          (task_id, obj_type, obj_name, description, created_date))
                self.conn.commit()
                self.show_message(f"Added {obj_type} '{obj_name}' to task! Press any key.")
                self.stdscr.getch()
            except sqlite3.Error as e:
                self.show_message(f"Error: {str(e)}. Press any key.")
                self.stdscr.getch()
        else:
            self.show_message("Description cannot be empty! Object not created. Press any key.")
            self.stdscr.getch()

    def update_object(self, task_id, obj_id):
        c = self.conn.cursor()
        # Получаем текущие данные объекта
        c.execute("""SELECT object_type, name, description 
                  FROM task_objects 
                  WHERE id = ?""", (obj_id,))
        obj = c.fetchone()
        
        if not obj:
            return
            
        obj_type, name, description = obj
        
        # Шаг 1: Редактирование имени объекта
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, f"Update object name (current: {name}): ")
        self.stdscr.refresh()
        
        curses.curs_set(1)
        curses.echo()
        self.stdscr.move(0, len(f"Update object name (current: {name}): "))
        new_name = self.stdscr.getstr().decode('utf-8').strip()
        curses.noecho()
        curses.curs_set(0)
        
        if not new_name:
            new_name = name

        # Шаг 2: Редактирование описания объекта
        # Создаем окно для редактирования
        edit_win = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
        edit_win.clear()
        edit_win.addstr(0, 0, f"Edit description for {obj_type} '{new_name}' (Ctrl+G to save, Ctrl+C to cancel):")
        edit_win.refresh()
        
        # Создаем текстовое поле
        text_win = curses.newwin(curses.LINES - 2, curses.COLS - 1, 1, 0)
        if description:
            text_win.addstr(description)
        text_win.refresh()
        
        # Включаем режим редактирования с поддержкой UTF-8
        textbox = curses.textpad.Textbox(text_win, insert_mode=True)
        curses.curs_set(1)
        textbox.edit(self.validate_input)
        curses.curs_set(0)
        
        # Получаем отредактированный текст
        new_description = textbox.gather().strip()
        
        # Сохраняем изменения
        if new_description:
            c.execute("""UPDATE task_objects 
                      SET name = ?, description = ? 
                      WHERE id = ?""",
                      (new_name, new_description, obj_id))
            self.conn.commit()
            self.show_message(f"Object updated! Press any key.")
            self.stdscr.getch()
        else:
            self.show_message("Description cannot be empty! Update canceled. Press any key.")
            self.stdscr.getch()
            
        return new_description

    def show_list_objects(self, task_id):
        # Получаем объекты для задачи с сортировкой по типу объекта (алфавитный порядок) и по дате создания (новые сверху)
        c = self.conn.cursor()
        c.execute("""SELECT id, object_type, name, created_date, description 
                  FROM task_objects 
                  WHERE task_id = ? 
                  ORDER BY object_type ASC, created_date DESC""", 
                  (task_id,))
        objects = c.fetchall()
        
        if not objects:
            self.show_message("No objects found for this task. Press any key.")
            self.stdscr.getch()
            return
        
        # Отображаем список объектов
        current_idx = 0
        start_idx = 0
        page_size = curses.LINES - 3
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            # Обновленный заголовок с указанием сортировки
            self.stdscr.addstr(0, 0, f"Objects for Task: {task_id} (sorted by type)")
            self.stdscr.addstr(1, 0, "-" * width)
            
            # Отображаем объекты
            for i, obj in enumerate(objects[start_idx:start_idx+page_size]):
                obj_id, obj_type, obj_name, created_date, description = obj
                
                # Форматируем дату
                try:
                    dt = datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S")
                    display_date = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    display_date = created_date
                
                # Выделение текущего объекта
                if i + start_idx == current_idx:
                    self.stdscr.attron(curses.A_REVERSE)
                
                # Отображаем информацию
                display_obj_name = obj_name if len(obj_name) < 25 else obj_name[:22] + "..."
                self.stdscr.addstr(2 + i, 0, f"{display_obj_name} ({obj_type})")
                
                # Отображаем начало описания
                short_desc = description.split('\n')[0][:width-40] + "..." if description else "No description"
                self.stdscr.addstr(2 + i, 30, short_desc)
                
                if i + start_idx == current_idx:
                    self.stdscr.attroff(curses.A_REVERSE)
            
            # Подсказки
            footer = "q:Back  ↑/↓:Navigate  Enter:View Details  Ctrl+U:Update Object"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                if current_idx > 0:
                    current_idx -= 1
                    if current_idx < start_idx:
                        start_idx = current_idx
            elif key == curses.KEY_DOWN:
                if current_idx < len(objects) - 1:
                    current_idx += 1
                    if current_idx >= start_idx + page_size:
                        start_idx += 1
            elif key == 10:  # Enter
                # Показываем детали объекта
                obj = objects[current_idx]
                self.show_object_details(task_id, obj)
            elif key == 21:  # Ctrl+U - Обновить объект
                if objects:
                    obj_id = objects[current_idx][0]
                    self.update_object(task_id, obj_id)
                    # Перезагружаем объекты после обновления
                    c.execute("""SELECT id, object_type, name, created_date, description 
                              FROM task_objects 
                              WHERE task_id = ? 
                              ORDER BY object_type ASC, created_date DESC""", 
                              (task_id,))
                    objects = c.fetchall()

    def show_object_details(self, task_id, obj):
        obj_id, obj_type, obj_name, created_date, description = obj
        
        # Форматируем дату
        try:
            dt = datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S")
            display_date = dt.strftime("%d.%m.%Y %H:%M")
        except:
            display_date = created_date
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            # Заголовок
            self.stdscr.addstr(0, 0, f"Object: {obj_name} ({obj_type})")
            self.stdscr.addstr(1, 0, f"Task: {task_id} | Created: {display_date}")
            self.stdscr.addstr(2, 0, "-" * width)
            
            # Описание объекта
            self.stdscr.addstr(3, 0, "Description:")
            if description:
                # Отображаем описание с переносами
                y = 4
                for line in description.split('\n'):
                    if y < height - 2 and line.strip():
                        # Обрезаем строку, если она слишком длинная
                        while len(line) > width:
                            self.stdscr.addstr(y, 0, line[:width])
                            line = line[width:]
                            y += 1
                            if y >= height - 2:
                                break
                        if y < height - 1:
                            self.stdscr.addstr(y, 0, line)
                            y += 1
                        if y >= height - 2:
                            break
            else:
                self.stdscr.addstr(4, 0, "No description available")
            
            # Подсказки
            footer = "q:Back"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break

    def edit_today_log(self, task_id):
        """Создает или редактирует лог за сегодняшний день"""
        today = datetime.date.today().strftime("%Y-%m-%d")
        created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        c = self.conn.cursor()
        
        # Проверяем, есть ли уже лог за сегодня
        c.execute("""SELECT id, content 
                  FROM task_logs 
                  WHERE task_id = ? AND log_date = ?""", 
                  (task_id, today))
        log = c.fetchone()
        
        log_id = None
        content = ""
        
        if log:
            log_id, content = log
        else:
            # Создаем новую запись лога
            c.execute("""INSERT INTO task_logs 
                      (task_id, log_date, content, created_date) 
                      VALUES (?, ?, ?, ?)""", 
                      (task_id, today, "", created_date))
            self.conn.commit()
            log_id = c.lastrowid
        
        # Создаем окно для редактирования
        edit_win = curses.newwin(curses.LINES - 1, curses.COLS, 0, 0)
        edit_win.clear()
        edit_win.addstr(0, 0, f"Edit today's log ({today}) for task: {task_id} (Ctrl+G to save, Ctrl+C to cancel):")
        edit_win.refresh()
        
        # Создаем текстовое поле
        text_win = curses.newwin(curses.LINES - 2, curses.COLS - 1, 1, 0)
        if content:
            text_win.addstr(content)
        text_win.refresh()
        
        # Включаем режим редактирования с поддержкой UTF-8
        textbox = curses.textpad.Textbox(text_win, insert_mode=True)
        curses.curs_set(1)
        textbox.edit(self.validate_input)
        curses.curs_set(0)
        
        # Получаем отредактированный текст
        edited_text = textbox.gather().strip()
        
        # Сохраняем изменения
        c.execute("""UPDATE task_logs 
                  SET content = ?, created_date = ?
                  WHERE id = ?""", 
                  (edited_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), log_id))
        self.conn.commit()
        
        return edited_text

    def show_log_list(self, task_id):
        """Показывает список логов для задачи"""
        c = self.conn.cursor()
        c.execute("""SELECT id, log_date, content, created_date 
                  FROM task_logs 
                  WHERE task_id = ? 
                  ORDER BY log_date DESC""", 
                  (task_id,))
        logs = c.fetchall()
        
        if not logs:
            self.show_message("No logs found for this task. Press any key.")
            self.stdscr.getch()
            return
        
        # Отображаем список логов
        current_idx = 0
        start_idx = 0
        page_size = curses.LINES - 3
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(0, 0, f"Logs for Task: {task_id}")
            self.stdscr.addstr(1, 0, "-" * width)
            
            # Отображаем логи
            for i, log in enumerate(logs[start_idx:start_idx+page_size]):
                log_id, log_date, content, created_date = log
                
                # Форматируем дату
                try:
                    dt = datetime.datetime.strptime(log_date, "%Y-%m-%d")
                    display_date = dt.strftime("%d.%m.%Y")
                except:
                    display_date = log_date
                
                # Выделение текущего лога
                if i + start_idx == current_idx:
                    self.stdscr.attron(curses.A_REVERSE)
                
                # Отображаем информацию
                self.stdscr.addstr(2 + i, 0, f"Log: {display_date}")
                
                # Отображаем начало содержимого
                short_content = content.split('\n')[0][:width-20] + "..." if content else "No content"
                self.stdscr.addstr(2 + i, 15, short_content)
                
                if i + start_idx == current_idx:
                    self.stdscr.attroff(curses.A_REVERSE)
            
            # Подсказки
            footer = "q:Back  ↑/↓:Navigate  Enter:View Log"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                if current_idx > 0:
                    current_idx -= 1
                    if current_idx < start_idx:
                        start_idx = current_idx
            elif key == curses.KEY_DOWN:
                if current_idx < len(logs) - 1:
                    current_idx += 1
                    if current_idx >= start_idx + page_size:
                        start_idx += 1
            elif key == 10:  # Enter
                # Показываем детали лога
                log = logs[current_idx]
                self.show_log_details(task_id, log)

    def show_log_details(self, task_id, log):
        log_id, log_date, content, created_date = log
        
        # Форматируем даты
        try:
            dt_log = datetime.datetime.strptime(log_date, "%Y-%m-%d")
            display_log_date = dt_log.strftime("%d.%m.%Y")
        except:
            display_log_date = log_date
            
        try:
            dt_created = datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S")
            display_created_date = dt_created.strftime("%d.%m.%Y %H:%M")
        except:
            display_created_date = created_date
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            # Заголовок
            self.stdscr.addstr(0, 0, f"Log for {display_log_date} | Created: {display_created_date}")
            self.stdscr.addstr(1, 0, f"Task: {task_id}")
            self.stdscr.addstr(2, 0, "-" * width)
            
            # Содержимое лога
            self.stdscr.addstr(3, 0, "Content:")
            if content:
                # Отображаем содержимое с переносами
                y = 4
                for line in content.split('\n'):
                    if y < height - 2 and line.strip():
                        # Обрезаем строку, если она слишком длинная
                        while len(line) > width:
                            self.stdscr.addstr(y, 0, line[:width])
                            line = line[width:]
                            y += 1
                            if y >= height - 2:
                                break
                        if y < height - 1:
                            self.stdscr.addstr(y, 0, line)
                            y += 1
                        if y >= height - 2:
                            break
            else:
                self.stdscr.addstr(4, 0, "No content available")
            
            # Подсказки
            footer = "q:Back"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break

    def view_task_details(self, task_idx):
        # Загружаем текущие данные задачи
        c = self.conn.cursor()
        c.execute("SELECT id, name, created_date, description FROM tasks WHERE id = ?", 
                  (self.tasks[task_idx][0],))
        task = c.fetchone()
        
        if not task:
            return
            
        task_id, name, created_date, description = task
        
        # Обновленные опции меню
        menu_options = [
            "Add Objects",
            "Show List Objects",
            "Log",  # Переименовано
            "Show List Log"  # Новый пункт
        ]
        selected_option = 0
        
        # Режим детального просмотра
        while True:
            # Форматируем дату
            try:
                dt = datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S")
                display_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                display_date = created_date
            
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            # Заголовок
            self.stdscr.addstr(0, 0, f"Task Details: {task_id} - {name}")
            self.stdscr.addstr(1, 0, f"Created: {display_date}")
            self.stdscr.addstr(2, 0, "-" * width)
            
            # Меню опций с навигацией стрелками
            for i, option in enumerate(menu_options):
                if i == selected_option:
                    self.stdscr.attron(curses.A_REVERSE)
                self.stdscr.addstr(3 + i, 0, f"{i+1}. {option}")
                if i == selected_option:
                    self.stdscr.attroff(curses.A_REVERSE)
            
            self.stdscr.addstr(3 + len(menu_options), 0, "-" * width)
            
            # Описание задачи
            self.stdscr.addstr(4 + len(menu_options), 0, "Description:")
            if description:
                # Отображаем описание с переносами
                y = 5 + len(menu_options)
                for line in description.split('\n'):
                    if y < height - 2 and line.strip():
                        # Обрезаем строку, если она слишком длинная
                        while len(line) > width:
                            self.stdscr.addstr(y, 0, line[:width])
                            line = line[width:]
                            y += 1
                            if y >= height - 2:
                                break
                        if y < height - 1:
                            self.stdscr.addstr(y, 0, line)
                            y += 1
                        if y >= height - 2:
                            break
            else:
                self.stdscr.addstr(5 + len(menu_options), 0, "No description available")
            
            # Подсказки
            footer = "q:Back  ↑/↓:Navigate  Enter:Select  Ctrl+O:Edit Description"
            self.stdscr.addstr(height - 1, 0, footer[:width-1])
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                if selected_option > 0:
                    selected_option -= 1
            elif key == curses.KEY_DOWN:
                if selected_option < len(menu_options) - 1:
                    selected_option += 1
            elif key == 10:  # Enter
                # Обработка выбранной опции
                if selected_option == 0:  # Add Objects
                    self.add_object(task_id)
                elif selected_option == 1:  # Show List Objects
                    self.show_list_objects(task_id)
                elif selected_option == 2:  # Log (бывший Development Log)
                    self.edit_today_log(task_id)
                elif selected_option == 3:  # Show List Log (новый)
                    self.show_log_list(task_id)
            elif key == 15:  # Ctrl+O
                # Редактируем описание и сразу обновляем переменную
                new_description = self.edit_description(task_id)
                description = new_description
                # Обновляем список задач для главного экрана
                self.load_tasks()

    def show_message(self, msg):
        self.stdscr.move(curses.LINES - 1, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(curses.LINES - 1, 0, msg)
        self.stdscr.refresh()

    def draw_ui(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Заголовки
        self.stdscr.addstr(0, 0, "ID")
        self.stdscr.addstr(0, 20, "Task Name")
        self.stdscr.addstr(0, 60, "Created Date")
        self.stdscr.addstr(1, 0, "-" * (width - 1))
        
        # Задачи (новые сверху)
        for i, task in enumerate(self.tasks):
            task_id, name, created_date, _ = task
            line = i + 2
            
            # Форматируем дату
            try:
                dt = datetime.datetime.strptime(created_date, "%Y-%m-%d %H:%M:%S")
                display_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                display_date = created_date
            
            # Обрезаем длинные значения
            display_id = task_id if len(task_id) < 18 else task_id[:15] + "..."
            display_name = name if len(name) < 38 else name[:35] + "..."
            
            # Выделение текущей строки
            if i == self.selected_idx:
                self.stdscr.attron(curses.A_REVERSE)
            
            self.stdscr.addstr(line, 0, display_id)
            self.stdscr.addstr(line, 20, display_name)
            self.stdscr.addstr(line, 60, display_date)
            
            if i == self.selected_idx:
                self.stdscr.attroff(curses.A_REVERSE)
        
        # Подсказки
        footer = "Ctrl+N:New  Ctrl+U:Update  Ctrl+D:Delete  Enter:Details  Ctrl+Q:Quit"
        self.stdscr.addstr(height - 1, 0, footer[:width-1])
        self.stdscr.refresh()

    def run(self):
        curses.curs_set(0)
        self.stdscr.keypad(True)
        
        while True:
            self.draw_ui()
            key = self.stdscr.getch()
            
            if key == curses.KEY_UP and self.selected_idx > 0:
                self.selected_idx -= 1
            elif key == curses.KEY_DOWN and self.selected_idx < len(self.tasks) - 1:
                self.selected_idx += 1
            elif key == 14:  # Ctrl+N
                self.create_task()
            elif key == 21:  # Ctrl+U
                self.update_task()
            elif key == 4:   # Ctrl+D
                self.delete_task()
            elif key == 10:  # Enter
                self.view_task_details(self.selected_idx)
            elif key == 17:  # Ctrl+Q
                break

def main(stdscr):
    # Включаем поддержку специальных клавиш и цветов
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()
    
    # Инициализируем менеджер задач
    app = TaskManager(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)
