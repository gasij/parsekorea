import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7771319116:AAFTuVK9k_AHXDoX0gX6qIgDqreSY6-84eM')
# TELEGRAM_CHAT_ID больше не требуется - бот отправляет всем подписчикам

# Parser Configuration
BUNJANG_URL = 'https://globalbunjang.com/'
PARSING_INTERVAL = 600  # Интервал парсинга в секундах (1 час)
MAX_PRODUCTS_PER_MESSAGE = 5  # Максимальное количество товаров в одном сообщении
USE_SELENIUM = os.getenv('USE_SELENIUM', 'False').lower() == 'true'  # Использовать Selenium для динамического контента
NEW_PRODUCTS_MAX_AGE_HOURS = 1  # Максимальный возраст товара в часах, чтобы считаться "новым" (только товары за последний час)

# Бренды для парсинга (только товары этих брендов будут парситься с ОБОИХ сайтов)
BRANDS_TO_PARSE = [
    {'name': 'maison margiela', 'category': None},  # только обувь
    {'name': 'grailz', 'category': None},
    {'name': 'project gr', 'category': None},
    {'name': 'stone island', 'category': None},
    {'name': 'cp company', 'category': None},
]

# Database (для хранения уже отправленных товаров)
DB_FILE = 'products.db'

