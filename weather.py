#1f7ea3317da0c0d2a527b98ae52ba738
import requests
import time
from datetime import datetime, timedelta, timezone

# Конфигурация
API_KEY = "1f7ea3317da0c0d2a527b98ae52ba738"
CITY = "Moscow,RU"
URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric&lang=ru"
REFRESH_INTERVAL = 60  # Обновление каждые 60 секунд

# ANSI цветовые коды
COLORS = {
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BOLD": "\033[1m",
    "RESET": "\033[0m",
}

# Компактный ASCII арт
WEATHER_ART = {
    "clear": {
        "color": COLORS["YELLOW"],
        "art": [
            "    \\   /    ",
            "  ― (   ) ―   ",
            "    /   \\    "
        ]
    },
    "clouds": {
        "color": COLORS["WHITE"],
        "art": [
            "     .--.     ",
            "  .-(    ).   ",
            "  (____).)    "
        ]
    },
    "rain": {
        "color": COLORS["BLUE"],
        "art": [
            "     .--.     ",
            "  .-(    ).   ",
            "  (____).) ~  "
        ]
    },
    "snow": {
        "color": COLORS["CYAN"],
        "art": [
            "     .--.     ",
            "  .-(    ).   ",
            "  (____).) *  "
        ]
    },
    "thunderstorm": {
        "color": COLORS["MAGENTA"],
        "art": [
            "     .--.     ",
            "  .-(    ).   ",
            "  (____).)/\\  "
        ]
    },
    "default": {
        "color": COLORS["GREEN"],
        "art": [
            "   .~~~~.    ",
            "   ;    ;    ",
            "    \\__/     "
        ]
    }
}

def get_weather_art(condition):
    """Возвращает ASCII арт и цвет для погодного условия"""
    condition = condition.lower()
    
    if "clear" in condition:
        return WEATHER_ART["clear"]
    elif "cloud" in condition:
        return WEATHER_ART["clouds"]
    elif "rain" in condition:
        return WEATHER_ART["rain"]
    elif "snow" in condition:
        return WEATHER_ART["snow"]
    elif "thunder" in condition or "storm" in condition:
        return WEATHER_ART["thunderstorm"]
    else:
        return WEATHER_ART["default"]

def get_temp_color(temp):
    """Возвращает цветовой код в зависимости от температуры"""
    if temp < -10:
        return COLORS["CYAN"] + COLORS["BOLD"]
    elif temp < 0:
        return COLORS["BLUE"]
    elif temp < 10:
        return COLORS["CYAN"]
    elif temp < 20:
        return COLORS["GREEN"]
    elif temp < 30:
        return COLORS["YELLOW"]
    else:
        return COLORS["RED"] + COLORS["BOLD"]

def clear_screen():
    """Очищает экран терминала"""
    print("\033[H\033[J", end="")

def get_moscow_time():
    """Возвращает текущее время в Москве с учетом часового пояса"""
    # Часовой пояс Москвы (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    return datetime.now(moscow_tz).strftime("%H:%M:%S")

def get_weather():
    """Получает и отображает текущую погоду"""
    try:
        # Отправка запроса
        response = requests.get(URL)
        data = response.json()
        
        # Проверка статуса
        if response.status_code == 200:
            # Извлечение данных
            weather_desc = data['weather'][0]['description']
            weather_main = data['weather'][0]['main']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            pressure = data['main']['pressure']
            wind_speed = data['wind']['speed']
            
            # Получаем арт и цвет для погоды
            weather_art = get_weather_art(weather_main)
            weather_color = weather_art["color"]
            art_lines = weather_art["art"]
            
            # Цвета для температуры
            temp_color = get_temp_color(temp)
            feels_color = get_temp_color(feels_like)
            reset = COLORS["RESET"]
            
            # Текущее время в Москве
            now = get_moscow_time()
            
            # Очистка экрана и вывод заголовка
            clear_screen()
            print(f"{COLORS['BOLD']}{COLORS['YELLOW']}Погода в Москве [{now}]{reset}\n")
            
            # Выводим ASCII арт и основную информацию
            print(f"{weather_color}{art_lines[0]}  {COLORS['BOLD']}Состояние:{reset} {weather_desc.capitalize()}")
            print(f"{weather_color}{art_lines[1]}  {COLORS['BOLD']}Температура:{reset} {temp_color}{temp:.1f}°C{reset}")
            print(f"{weather_color}{art_lines[2]}  {COLORS['BOLD']}Ощущается:{reset} {feels_color}{feels_like:.1f}°C{reset}")
            
            # Вывод параметров друг под другом
            print(f"\n{COLORS['BOLD']}Дополнительные параметры:{reset}")
            print(f"  Влажность:   {COLORS['BLUE']}{humidity}%{reset}")
            print(f"  Давление:    {COLORS['CYAN']}{pressure} hPa{reset}")
            print(f"  Ветер:       {COLORS['WHITE']}{wind_speed} м/с{reset}")
            
            # Компактный футер
            print(f"\n{COLORS['GREEN']}Обновление через {REFRESH_INTERVAL} сек {COLORS['YELLOW']}[Ctrl+C для выхода]{reset}")
            
        else:
            print(f"{COLORS['RED']}Ошибка: {data.get('message', 'Неизвестная ошибка')}{COLORS['RESET']}")

    except requests.exceptions.RequestException as e:
        print(f"{COLORS['RED']}Ошибка соединения: {e}{COLORS['RESET']}")
    except KeyError:
        print(f"{COLORS['RED']}Ошибка обработки данных. Проверьте API-ключ.{COLORS['RESET']}")

def main():
    """Основной цикл программы"""
    try:
        while True:
            get_weather()
            # Ожидание до следующего обновления
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n{COLORS['GREEN']}Программа завершена. До свидания!{COLORS['RESET']}")

if __name__ == "__main__":
    main()
