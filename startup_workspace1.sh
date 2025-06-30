#!/bin/bash

# Создаем временный файл макета
LAYOUT_FILE="/tmp/i3_layout_$(date +%s).json"

cat > "$LAYOUT_FILE" << 'EOF'
{
    "type": "con",
    "layout": "splith",
    "nodes":[
        {
            "type": "con",
            "percent": 0.4,
            "layout": "splitv",
            "nodes":[
                {"type": "con",
                "percent": 0.5,
                "swallows":[{"class":"DUF"}]},
                
                {"type": "con",
                "percent": 0.25,
                "swallows":[{"class":"TASK"}]},

                {"type": "con",
                "percent": 0.25,
                "swallows":[{"class":"CONSOLE"}]}

                
            ]
        },
        {
            "type": "con",
            "percent": 0.6,
            "layout": "splitv",
            "nodes":[
                {"type": "con",
                "percent": 0.6,
                "swallows":[{"class":"BTOP"}]},

                {"type": "con",
                "percent": 0.4,
                "layout": "splith",
                "nodes":[
                    {"type": "con",
                    "percent": 0.5,
                    "swallows":[{"class":"WEATHER"}]},

                    {"type": "con",
                    "percent": 0.5,
                    "swallows":[{"class":"RSS"}]}
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
nohup alacritty --class 'TASK' -e python ~/user_programs/task_manager/task_manager.py >/dev/null 2>&1 &
nohup alacritty --class 'RSS' -e python ~/user_programs/rss/get_rss.py >/dev/null 2>&1 &


# Удаляем временный файл
#sleep 1
#rm "$LAYOUT_FILE"

# Сообщение для проверки
#echo "Layout applied. Check your i3 workspace."
