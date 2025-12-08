import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8511531317:AAGBdl_GnJ-UQZVr4Ha54NB69xM7R6EWjsk')
# TELEGRAM_CHAT_ID больше не требуется - бот отправляет всем подписчикам

# Parser Configuration
BUNJANG_URL = 'https://globalbunjang.com/'
PARSING_INTERVAL = 30  # Интервал парсинга в секундах (1 час)
MAX_PRODUCTS_PER_MESSAGE = 100232131  # Максимальное количество товаров в одном сообщении
USE_SELENIUM = os.getenv('USE_SELENIUM', 'False').lower() == 'true'  # Использовать Selenium для динамического контента
NEW_PRODUCTS_MAX_AGE_HOURS = 1  # Максимальный возраст товара в часах, чтобы считаться "новым" (только товары за последний час)

# Бренды для парсинга (только товары этих брендов будут парситься с ОБОИХ сайтов)
BRANDS_TO_PARSE = [
    {'name': 'maison margiela', 'category': None},
    {'name': 'grailz', 'category': None},
    {'name': 'project gr', 'category': None},
    {'name': 'stone island', 'category': None},
    {'name': 'cp company', 'category': None},
]

# Ссылки для парсинга брендов на fruitsfamily.com
FRUITS_BRAND_URLS = {
    'maison margiela': 'https://fruitsfamily.com/brand/Maison%20Margiela?sort=POPULAR',
    'grailz': 'https://fruitsfamily.com/search/grailz?sort=POPULAR',
    'project gr': 'https://fruitsfamily.com/brand/PROJECT%20GR?sort=POPULAR',
    'stone island': 'https://fruitsfamily.com/brand/Stone%20Island?sort=POPULAR',
    'cp company': 'https://fruitsfamily.com/brand/C.P.%20Company?sort=POPULAR',
}

# Database (для хранения уже отправленных товаров)
DB_FILE = 'products.db'

