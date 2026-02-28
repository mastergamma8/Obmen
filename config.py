# config.py
BOT_TOKEN = "ТВОЙ_ТОКЕН_БОТА"
WEBAPP_URL = "https://твой-домен.com/" # Ссылка на твой FastAPI (для локального теста можно использовать ngrok)
ADMIN_ID = 123456789 # Твой Telegram ID (для команд админа)

# Настройки подарков
# Ключ - ID подарка
GIFTS = {
    1: {
        "name": "Звезда",
        "photo": "gifts/1.png",
        "required_amount": 10
    },
    2: {
        "name": "Сердце",
        "photo": "gifts/2.png",
        "required_amount": 5
    },
    3: {
        "name": "Корона",
        "photo": "gifts/3.png",
        "required_amount": 3
    },
    4: {
        "name": "Бриллиант",
        "photo": "gifts/4.png",
        "required_amount": 1
    }
}
