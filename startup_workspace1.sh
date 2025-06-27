#!/bin/bash

# Создаем временный файл макета
LAYOUT_FILE="/tmp/i3_layout_$(date +%s).json"

cat > "$LAYOUT_FILE" << 'EOF'
{
    "layout": "splith",
    "type": "con",
    "percent": 100,
    "nodes": [
        {
            "type": "con",
            "percent": 50,
            "layout": "splitv",
            "nodes": [
                {
                    "type": "con",
                    "percent": 50,
                    "swallows": [{"class": "DUF"}]
                },
                {
                    "type": "con",
                    "percent": 50,
                    "swallows": [{"class": "CONSOLE"}]
                }
            ]
        },
        {
            "type": "con",
            "percent": 50,
            "layout": "splitv",
            "nodes": [
                {
                    "type": "con",
                    "percent": 60,
                    "swallows": [{"class": "BTOP"}]
                },
                {
                    "type": "con",
                    "layout": "splith",
                    "percent": 40,
                    "nodes": [
                        {
                            "type": "con",
                            "percent": 50,
                            "swallows": [{"class": "WEATHER"}]
                        },
                        {
                            "type": "con",
                            "percent": 50,
                            "swallows": [{"class": "RSS"}]
                        }
                    ]
                }
            ]
        }
    ]
}
EOF

# Применяем макет
i3-msg "workspace 1; append_layout $LAYOUT_FILE"

# Запускаем приложения с разными классами
nohup alacritty --class 'DUF' -e bash -c "while true; do clear; duf; sleep 5; done" >/dev/null 2>&1 &
nohup alacritty --class 'CONSOLE' >/dev/null 2>&1 &
nohup alacritty --class 'BTOP' -e btop >/dev/null 2>&1 &
nohup alacritty --class 'WEATHER' -e python ~/user_programs/weather/weather.py >/dev/null 2>&1 &
nohup alacritty --class 'RSS' -e python ~/user_programs/rss/get_rss.py >/dev/null 2>&1 &

# Удаляем временный файл
sleep 1
rm "$LAYOUT_FILE"

# Сообщение для проверки
echo "Layout applied. Check your i3 workspace."
