import json
import curses
import os
import feedparser
from datetime import datetime, timezone, timedelta
import textwrap
import time
import threading

# Итерация 8: новый путь файлов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Итерация 5: Путь к файлу с прочитанными новостями
READ_NEWS_FILE = os.path.join(BASE_DIR, "read_news.json")

# Итерация 5: Функция для загрузки прочитанных новостей
def load_read_news():
    if not os.path.exists(READ_NEWS_FILE):
        return {}
    
    try:
        with open(READ_NEWS_FILE, 'r') as f:
            data = json.load(f)
            # Итерация 5: Удаляем вчерашние записи
            today_str = datetime.now().strftime("%Y-%m-%d")
            return {k: v for k, v in data.items() if v["date"] == today_str}
    except:
        return {}

# Итерация 5: Функция для сохранения прочитанных новостей
def save_read_news(read_news):
    # Фильтруем только сегодняшние записи
    today_str = datetime.now().strftime("%Y-%m-%d")
    filtered = {k: v for k, v in read_news.items() if v["date"] == today_str}
    
    with open(READ_NEWS_FILE, 'w') as f:
        json.dump(filtered, f)

# Итерация 5: Пометить новость как прочитанную
def mark_as_read(read_news, feed_url, news_id):
    today_str = datetime.now().strftime("%Y-%m-%d")
    key = f"{feed_url}|{news_id}"
    read_news[key] = {
        "date": today_str,
        "feed": feed_url,
        "news_id": news_id
    }

# Итерация 5: Проверить, прочитана ли новость
def is_news_read(read_news, feed_url, news_id):
    key = f"{feed_url}|{news_id}"
    return key in read_news

# Итерация 5: Подсчет непрочитанных новостей для ленты
def count_unread_news(feed, read_news):
    try:
        d = feedparser.parse(feed['link'])
    except:
        return 0
    
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    unread_count = 0
    
    for entry in d.entries:
        if not hasattr(entry, 'published_parsed'):
            continue
            
        pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        
        if pub_time >= today_start:
            news_id = entry.get("id", entry.get("link", entry.title))
            if not is_news_read(read_news, feed['link'], news_id):
                unread_count += 1
                
    return unread_count

# Итерация 6: Функция для периодической проверки обновлений
def background_updater(feeds, read_news, feed_unread_counts, update_event, refresh_callback):
    """Фоновый поток для проверки обновлений"""
    while True:
        # Ждем 10 минут (600 секунд)
        time.sleep(600)
        
        # Итерация 6: Проверяем, нужно ли обновлять
        if update_event.is_set():
            # Итерация 6: Обновляем счетчики для всех лент
            for feed in feeds:
                try:
                    new_count = count_unread_news(feed, read_news)
                    if new_count != feed_unread_counts.get(feed['name'], 0):
                        feed_unread_counts[feed['name']] = new_count
                        # Итерация 6: Уведомляем главный поток о необходимости обновления
                        refresh_callback()
                except Exception as e:
                    # Итерация 6: Ошибки логируем, но не прерываем поток
                    pass

# Итерация 5: Функция для отображения полного текста новости с пометкой прочитанной
def show_article(stdscr, article, feed_url, read_news):
    # Итерация 5: Помечаем новость как прочитанную
    news_id = article.get("id", article.get("link", article.get("title", "")))
    mark_as_read(read_news, feed_url, news_id)
    save_read_news(read_news)
    
    stdscr.clear()
    rows, cols = stdscr.getmaxyx()
    
    # Отображение заголовка с переносом
    title = article.get('title', 'Без заголовка')
    title_lines = textwrap.wrap(title, width=cols-1)
    for i, line in enumerate(title_lines):
        stdscr.addstr(i, 0, line, curses.A_BOLD)
    
    # Рассчитываем положение линии под заголовком
    title_height = len(title_lines)
    stdscr.hline(title_height, 0, curses.ACS_HLINE, cols)
    
    # Итерация 5: Добавляем пометку "ПРОЧИТАНО"
    read_status = "ПРОЧИТАНО"
    if title_lines:
        # Размещаем статус в последней строке заголовка справа
        last_line = title_lines[-1]
        status_x = min(cols - len(read_status) - 1, len(last_line) + 2)
        stdscr.addstr(title_height - 1, status_x, read_status, curses.A_REVERSE | curses.A_BOLD)
    
    # Получение и подготовка описания
    description = article.get('description', 'Нет описания')
    
    clean_description = ""
    inside_tag = False
    for char in description:
        if char == '<':
            inside_tag = True
        elif char == '>':
            inside_tag = False
        elif not inside_tag:
            clean_description += char
    
    wrapped_lines = []
    for paragraph in clean_description.split('\n'):
        if paragraph.strip():
            wrapped = textwrap.wrap(paragraph, width=cols-1)
            wrapped_lines.extend(wrapped)
            wrapped_lines.append("")
    
    current_line = title_height + 1  # Начинаем после заголовка и линии
    start_idx = 0
    
    while True:
        stdscr.clear()
        
        # Снова отображаем заголовок (он статичен)
        for i, line in enumerate(title_lines):
            stdscr.addstr(i, 0, line, curses.A_BOLD)
        stdscr.hline(title_height, 0, curses.ACS_HLINE, cols)
        
        # Снова отображаем статус
        if title_lines:
            stdscr.addstr(title_height - 1, status_x, read_status, curses.A_REVERSE | curses.A_BOLD)
        
        # Отображение текста статьи
        max_lines = rows - (title_height + 2)  # Учитываем заголовок, линию и статусную строку
        for i in range(max_lines):
            idx = start_idx + i
            if idx >= len(wrapped_lines):
                break
            stdscr.addstr(title_height + 1 + i, 0, wrapped_lines[idx])
        
        # Строка состояния
        status_line = f"↑↓ Прокрутка | Q: назад | {start_idx+1}-{min(start_idx+max_lines, len(wrapped_lines))}/{len(wrapped_lines)}"
        # Обрезаем статусную строку если слишком длинная
        if len(status_line) > cols:
            status_line = status_line[:cols-4] + "..."
        stdscr.addstr(rows-1, 0, status_line, curses.A_REVERSE)
        
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            start_idx = max(0, start_idx - 1)
        elif key == curses.KEY_DOWN:
            if start_idx + max_lines < len(wrapped_lines):
                start_idx += 1
        elif key == curses.KEY_PPAGE:
            start_idx = max(0, start_idx - max_lines)
        elif key == curses.KEY_NPAGE:
            start_idx = min(len(wrapped_lines) - max_lines, start_idx + max_lines)
        elif key == ord('q') or key == ord('Q'):
            break

# Итерация 5: Функция для отображения новостей с цветами прочитанных
def show_news(stdscr, feed, read_news):
    # Загрузка и парсинг RSS-ленты
    try:
        d = feedparser.parse(feed['link'])
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Ошибка загрузки: {e}")
        stdscr.addstr(2, 0, "Нажмите любую клавишу для возврата...")
        stdscr.refresh()
        stdscr.getch()
        return []

    # Фильтрация новостей: только сегодняшние
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    news_items = []
    
    for entry in d.entries:
        if not hasattr(entry, 'published_parsed'):
            continue
            
        pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        
        if pub_time >= today_start:
            time_str = pub_time.astimezone().strftime("%H:%M")
            news_id = entry.get("id", entry.get("link", entry.title))
            is_read = is_news_read(read_news, feed['link'], news_id)
            
            news_items.append({
                'title': entry.title,
                'time': time_str,
                'published': pub_time,
                'entry': entry,
                'is_read': is_read,  # Итерация 5: Флаг прочитанной новости
                'id': news_id
            })

    news_items.sort(key=lambda x: x['published'], reverse=True)
    
    current_selection = 0
    start_idx = 0
    
    while True:
        stdscr.clear()
        rows, cols = stdscr.getmaxyx()
        
        title = f"Новости {feed['name']} ({len(news_items)} сегодня)"
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        stdscr.addstr(1, 0, "Стрелки: навигация | Enter: читать | Q: назад", curses.A_DIM)
        
        # Отображение списка новостей с переносом текста
        visible_items = min(rows - 4, len(news_items))
        display_pos = 3  # Начинаем с этой строки
        visible_count = 0
        display_map = []  # Для сопоставления позиции экрана с индексом новости
        
        # Отображаем столько новостей, сколько помещается на экране
        idx = start_idx
        while visible_count < visible_items and idx < len(news_items):
            item = news_items[idx]
            prefix = f"[{item['time']}] "
            text = item['title']
            
            # Разбиваем текст на строки с переносом
            available_width = cols - len(prefix) - 1
            if available_width < 5:  # Минимальная ширина для текста
                available_width = 5
                
            wrapped_lines = textwrap.wrap(text, width=available_width)
            if not wrapped_lines:
                wrapped_lines = [""]
            
            # Проверяем, поместится ли новость на экран
            required_lines = len(wrapped_lines)
            if display_pos + required_lines > rows - 1:  # Оставляем место для статусной строки
                break
            
            # Отображаем первую строку с временем
            is_selected = (idx == current_selection)
            attr = curses.A_REVERSE if is_selected else curses.A_NORMAL
            if item['is_read']:
                attr |= curses.A_DIM
                
            line = prefix + wrapped_lines[0]
            if len(line) > cols - 1:
                line = line[:cols-1]
            stdscr.addstr(display_pos, 0, line, attr)
            display_map.append(idx)  # Запоминаем индекс новости для этой позиции
            display_pos += 1
            
            # Отображаем остальные строки с отступом
            indent = ' ' * len(prefix)
            for line_text in wrapped_lines[1:]:
                line = indent + line_text
                if len(line) > cols - 1:
                    line = line[:cols-1]
                    
                stdscr.addstr(display_pos, 0, line, attr)
                display_pos += 1
            
            visible_count += 1
            idx += 1
        
        # Отображение информации о прокрутке
        if start_idx + visible_count < len(news_items) or start_idx > 0:
            scroll_info = f"↑↓ {start_idx+1}-{start_idx+visible_count} из {len(news_items)}"
            if len(scroll_info) > cols:
                scroll_info = scroll_info[:cols-4] + "..."
            stdscr.addstr(rows-1, 0, scroll_info, curses.A_REVERSE)
        
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            if current_selection > 0:
                current_selection -= 1
                # Прокручиваем список, если текущий элемент не виден
                if current_selection < start_idx:
                    start_idx = current_selection
        elif key == curses.KEY_DOWN:
            if current_selection < len(news_items) - 1:
                current_selection += 1
                # Прокручиваем список, если текущий элемент не виден
                if current_selection >= start_idx + visible_count:
                    start_idx += 1
        elif key == curses.KEY_PPAGE:
            current_selection = max(0, current_selection - visible_count)
            start_idx = max(0, start_idx - visible_count)
        elif key == curses.KEY_NPAGE:
            current_selection = min(len(news_items)-1, current_selection + visible_count)
            start_idx = min(len(news_items)-visible_count, start_idx + visible_count)
        elif key == ord('q') or key == ord('Q'):
            break
        elif key == curses.KEY_ENTER or key in [10, 13]:
            selected = news_items[current_selection]
            # Итерация 5: Передаем данные о прочитанных новостях
            show_article(stdscr, selected['entry'], feed['link'], read_news)
            # Итерация 5: Обновляем статус прочтения после просмотра
            selected['is_read'] = True
    
    return news_items

def main(stdscr):
    # Инициализация цветов и настроек
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.keypad(True)
    
    # Итерация 5: Загрузка данных о прочитанных новостях
    read_news = load_read_news()
    
    # Загрузка RSS-подписок из JSON
    try:
        # Итерация 8: Обновленный путь
        subscription_path = os.path.join(BASE_DIR, 'subscriptions.json')
        with open(subscription_path, 'r') as f:
            feeds = json.load(f)
    except FileNotFoundError:
        stdscr.addstr(0, 0, "Error: subscriptions.json not found!")
        stdscr.refresh()
        stdscr.getch()
        return

    current_selection = 0
    
    # Итерация 5: Подсчет непрочитанных новостей для каждой ленты
    feed_unread_counts = {}
    for feed in feeds:
        feed_unread_counts[feed['name']] = count_unread_news(feed, read_news)
    
    # Итерация 6: Флаг для обновления интерфейса
    refresh_needed = False
    
    # Итерация 6: Событие для управления фоновым потоком
    update_event = threading.Event()
    update_event.set()  # Разрешаем обновление
    
    # Итерация 6: Функция для запроса обновления интерфейса
    def request_refresh():
        nonlocal refresh_needed
        refresh_needed = True
    
    # Итерация 6: Запуск фонового потока для проверки обновлений
    updater_thread = threading.Thread(
        target=background_updater,
        args=(feeds, read_news, feed_unread_counts, update_event, request_refresh),
        daemon=True
    )
    updater_thread.start()
    

    # Главный цикл приложения
    while True:
        # Итерация 7: Всегда очищаем экран перед отрисовкой
        stdscr.clear()

        # Итерация 6: Проверка необходимости обновления интерфейса
        if refresh_needed:
            refresh_needed = False
            # Перерисовываем экран
            stdscr.clear()
        
        # Отображение заголовка
        rows, cols = stdscr.getmaxyx()
        header = "RSS Reader - Выберите ленту (ENTER: открыть, Q: выход)"
        stdscr.addstr(0, 0, header, curses.A_BOLD)
        
        # Итерация 5: Отображение списка подписок с количеством непрочитанных
        for idx, feed in enumerate(feeds):
            unread_count = feed_unread_counts.get(feed['name'], 0)
            unread_info = f" - {unread_count} непрочитано" if unread_count > 0 else ""
            feed_line = f"{feed['name']}{unread_info}"
            
            # Обрезаем строку если она слишком длинная
            if len(feed_line) > cols - 4:
                feed_line = feed_line[:cols-7] + "..."
            
            if idx == current_selection:
                stdscr.addstr(idx + 2, 0, f"> {feed_line}", curses.A_REVERSE)
            else:
                stdscr.addstr(idx + 2, 0, f"  {feed_line}")
        
        # Обновляем экран
        stdscr.refresh()
        
        # Итерация 6: Устанавливаем таймаут для неблокирующего чтения
        stdscr.timeout(1000)  # Ждем ввод 1 секунду
        
        # Обработка пользовательского ввода
        key = stdscr.getch()
        
        # Итерация 6: Сбрасываем таймаут после получения ввода
        stdscr.timeout(-1)
        
        # Выход по 'Q'
        if key == ord('q') or key == ord('Q'):
            # Итерация 6: Останавливаем фоновый поток
            update_event.clear()
            break
        
        # Навигация по списку
        elif key == curses.KEY_UP:
            current_selection = max(0, current_selection - 1)
        elif key == curses.KEY_DOWN:
            current_selection = min(len(feeds) - 1, current_selection + 1)
        
        # Обработка выбора ленты
        elif key == curses.KEY_ENTER or key in [10, 13]:
            # Итерация 6: Временно отключаем обновления
            update_event.clear()
            
            selected = feeds[current_selection]
            show_news(stdscr, selected, read_news)
            
            # Итерация 5: Обновляем счетчик непрочитанных после просмотра ленты
            feed_unread_counts[selected['name']] = count_unread_news(selected, read_news)
            
            # Итерация 6: Включаем обновления обратно
            update_event.set()
        
        # Итерация 6: Обработка таймаута (ничего не нажато)
        elif key == -1:
            # Ничего не делаем, просто переходим к следующей итерации
            pass

if __name__ == "__main__":
    # Итерация 8: Обновление путей
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Проверка существования файла перед запуском
    subscription_path = os.path.join(BASE_DIR, 'subscriptions.json')
    if not os.path.exists(subscription_path):
        print("Error: Create subscriptions.json file first!")
        print("Example content:")
        print(json.dumps([
            {"name": "DTF", "link": "https://dtf.ru/rss"},
            {"name": "Linux", "link": "https://www.opennet.ru/opennews/opennews_all.rss"}
        ], indent=2))
        exit(1)
    
    # Проверка наличия feedparser
    try:
        import feedparser
    except ImportError:
        print("Error: feedparser module is required.")
        print("Install it with: pip install feedparser")
        exit(1)
    
    curses.wrapper(main)
