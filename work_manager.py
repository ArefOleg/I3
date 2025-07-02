#!/usr/bin/env python3
import sqlite3
import datetime
import curses
import curses.textpad

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_date TEXT NOT NULL,
                description TEXT)''')
    
    # Проверяем существование колонки description
    c.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in c.fetchall()]
    if 'description' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN description TEXT")
    
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

    def view_task_details(self, task_idx):
        # Загружаем текущие данные задачи
        c = self.conn.cursor()
        c.execute("SELECT id, name, created_date, description FROM tasks WHERE id = ?", 
                  (self.tasks[task_idx][0],))
        task = c.fetchone()
        
        if not task:
            return
            
        task_id, name, created_date, description = task
        
        # Опции меню
        menu_options = [
            "Add Objects",
            "Show List Objects",
            "Development Log"
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
                        # (чтобы не вылезать за пределы экрана)
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
                    self.show_message("Add Objects functionality will be here")
                    self.stdscr.getch()
                elif selected_option == 1:  # Show List Objects
                    self.show_message("Show List Objects functionality will be here")
                    self.stdscr.getch()
                elif selected_option == 2:  # Development Log
                    self.show_message("Development Log functionality will be here")
                    self.stdscr.getch()
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
    app = TaskManager(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)
