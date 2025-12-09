import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from parser import BunjangParser, FruitsFamilyParser
from bot import TelegramBot
from database import ProductDatabase
import config

class BunjangBot:
    def __init__(self):
        # Парсер для Bunjang
        self.bunjang_parser = BunjangParser(
            config.BUNJANG_URL, 
            use_selenium=config.USE_SELENIUM,
            brands_filter=config.BRANDS_TO_PARSE
        )
        # Парсер для FruitsFamily (используем те же бренды, что и для Bunjang)
        # Для FruitsFamily всегда используем Selenium, так как сайт требует JavaScript
        self.fruits_parser = FruitsFamilyParser(
            base_url='https://fruitsfamily.com/',
            use_selenium=True,  # Всегда используем Selenium для FruitsFamily
            brands_filter=config.BRANDS_TO_PARSE  # Используем те же бренды
        )
        # Для обратной совместимости
        self.parser = self.bunjang_parser
        self.bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)
        self.db = ProductDatabase(config.DB_FILE)
        self.application = None
        self.is_parsing_active = True  # Флаг для управления парсингом
        self.scheduler_task = None  # Задача планировщика
    
    def get_control_keyboard(self):
        """Создает клавиатуру с кнопками управления (inline)"""
        keyboard = [
            [
                InlineKeyboardButton("▶️ Начать парс", callback_data="start_parse"),
                InlineKeyboardButton("⏹️ Остановить парс", callback_data="stop_parse")
            ],
            [
                InlineKeyboardButton("📊 Статус парсинга", callback_data="parse_status")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_reply_keyboard(self):
        """Создает постоянную клавиатуру меню"""
        keyboard = [
            [
                KeyboardButton("▶️ Начать парс"),
                KeyboardButton("⏹️ Остановить парс")
            ],
            [
                KeyboardButton("📊 Статус")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        self.db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        self.db.subscribe_user(user.id)
        
        status_text = "активен" if self.is_parsing_active else "остановлен"
        
        await update.message.reply_text(
            "Привет! Я бот для парсинга товаров с:\n"
            "- globalbunjang.com\n"
            "- fruitsfamily.com\n\n"
            "Вы подписаны на рассылку новых товаров.\n"
            f"Статус парсинга: {status_text}\n\n"
            "Используйте кнопки меню для управления парсингом.\n"
            "Используйте /stop чтобы отписаться от рассылки.",
            reply_markup=self.get_reply_keyboard()
        )
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stop"""
        user = update.effective_user
        self.db.unsubscribe_user(user.id)
        await update.message.reply_text(
            "Вы отписаны от рассылки. Используйте /start чтобы подписаться снова.",
            reply_markup=self.get_reply_keyboard()
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status"""
        user = update.effective_user
        is_subscribed = self.db.is_subscribed(user.id)
        status_text = "подписаны" if is_subscribed else "не подписаны"
        parse_status = "активен" if self.is_parsing_active else "остановлен"
        subscribed_users = len(self.db.get_subscribed_users())
        await update.message.reply_text(
            f"📊 Статус:\n\n"
            f"Подписка: вы {status_text} на рассылку\n"
            f"Парсинг: {parse_status}\n"
            f"Всего подписчиков: {subscribed_users}\n\n"
            f"Сайты:\n"
            f"- globalbunjang.com\n"
            f"- fruitsfamily.com",
            reply_markup=self.get_reply_keyboard()
        )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений (кнопки меню)"""
        text = update.message.text
        
        if text == "▶️ Начать парс":
            if self.is_parsing_active:
                await update.message.reply_text(
                    "✅ Парсинг уже активен!\n\n"
                    "Парсинг выполняется автоматически по расписанию.",
                    reply_markup=self.get_reply_keyboard()
                )
            else:
                self.is_parsing_active = True
                await update.message.reply_text(
                    "✅ Парсинг запущен!\n\n"
                    "Начинаю парсинг товаров...",
                    reply_markup=self.get_reply_keyboard()
                )
                # Запускаем парсинг в фоне
                asyncio.create_task(self.parse_and_send_with_notification(update.effective_user.id))
        
        elif text == "⏹️ Остановить парс":
            if not self.is_parsing_active:
                await update.message.reply_text(
                    "⏹️ Парсинг уже остановлен!",
                    reply_markup=self.get_reply_keyboard()
                )
            else:
                self.is_parsing_active = False
                await update.message.reply_text(
                    "⏹️ Парсинг остановлен!\n\n"
                    "Автоматический парсинг приостановлен. Используйте кнопку '▶️ Начать парс' для возобновления.",
                    reply_markup=self.get_reply_keyboard()
                )
        
        elif text == "📊 Статус":
            await self.status_command(update, context)
    
    async def start_parse_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start_parse"""
        if self.is_parsing_active:
            await update.message.reply_text(
                "✅ Парсинг уже активен!\n\n"
                "Парсинг выполняется автоматически по расписанию.",
                reply_markup=self.get_reply_keyboard()
            )
        else:
            self.is_parsing_active = True
            await update.message.reply_text(
                "✅ Парсинг запущен!\n\n"
                "Начинаю парсинг товаров...",
                reply_markup=self.get_reply_keyboard()
            )
            # Запускаем парсинг в фоне
            asyncio.create_task(self.parse_and_send_with_notification(update.effective_user.id))
    
    async def stop_parse_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stop_parse"""
        if not self.is_parsing_active:
            await update.message.reply_text(
                "⏹️ Парсинг уже остановлен!",
                reply_markup=self.get_reply_keyboard()
            )
        else:
            self.is_parsing_active = False
            await update.message.reply_text(
                "⏹️ Парсинг остановлен!\n\n"
                "Автоматический парсинг приостановлен. Используйте кнопку '▶️ Начать парс' для возобновления.",
                reply_markup=self.get_reply_keyboard()
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_parse":
            if self.is_parsing_active:
                await query.edit_message_text(
                    "✅ Парсинг уже активен!\n\n"
                    "Парсинг выполняется автоматически по расписанию.",
                    reply_markup=self.get_control_keyboard()
                )
            else:
                self.is_parsing_active = True
                # Запускаем парсинг немедленно
                await query.edit_message_text(
                    "✅ Парсинг запущен!\n\n"
                    "Начинаю парсинг товаров...",
                    reply_markup=self.get_control_keyboard()
                )
                # Запускаем парсинг в фоне
                asyncio.create_task(self.parse_and_send_with_notification(query.message.chat_id))
        
        elif query.data == "stop_parse":
            if not self.is_parsing_active:
                await query.edit_message_text(
                    "⏹️ Парсинг уже остановлен!",
                    reply_markup=self.get_control_keyboard()
                )
            else:
                self.is_parsing_active = False
                await query.edit_message_text(
                    "⏹️ Парсинг остановлен!\n\n"
                    "Автоматический парсинг приостановлен. Используйте кнопку 'Начать парс' для возобновления.",
                    reply_markup=self.get_control_keyboard()
                )
        
        elif query.data == "parse_status":
            status_text = "активен" if self.is_parsing_active else "остановлен"
            subscribed_users = len(self.db.get_subscribed_users())
            await query.edit_message_text(
                f"📊 Статус парсинга:\n\n"
                f"Парсинг: {status_text}\n"
                f"Подписчиков: {subscribed_users}\n\n"
                f"Сайты:\n"
                f"- globalbunjang.com\n"
                f"- fruitsfamily.com",
                reply_markup=self.get_control_keyboard()
            )
    
    async def parse_and_send_with_notification(self, user_id: int):
        """Парсинг с уведомлением пользователя о результате"""
        try:
            await self.bot.send_message_to_user(
                user_id,
                "🔄 Начинаю парсинг товаров..."
            )
            
            # Вызываем обычный парсинг
            await self.parse_and_send()
            
            await self.bot.send_message_to_user(
                user_id,
                "✅ Парсинг завершен!"
            )
        except Exception as e:
            await self.bot.send_message_to_user(
                user_id,
                f"❌ Ошибка при парсинге: {e}"
            )
    
    async def parse_and_send(self):
        """Парсинг и отправка новых товаров с обоих сайтов"""
        print("Начало парсинга...")
        
        try:
            # Получаем список подписанных пользователей
            user_ids = self.db.get_subscribed_users()
            
            if not user_ids:
                print("Нет подписанных пользователей")
                return
            
            print(f"Найдено {len(user_ids)} подписанных пользователей")
            
            all_products = []
            
            # 1. Парсим товары с Bunjang для всех брендов из config
            print("Парсинг Bunjang Global...")
            try:
                bunjang_products = []
                # Парсим товары для каждого бренда из списка
                for brand_info in config.BRANDS_TO_PARSE:
                    brand_name = brand_info['name']
                    category = brand_info.get('category')
                    
                    # Формируем поисковый запрос
                    if category == 'shoes':
                        # Для обуви используем специальную категорию
                        search_url = f"https://globalbunjang.com/search?categoryId=405&q={brand_name.replace(' ', '%20')}&soldout=exclude"
                    else:
                        search_url = f"https://globalbunjang.com/search?q={brand_name.replace(' ', '%20')}&soldout=exclude"
                    
                    print(f"  Парсинг бренда: {brand_name}...")
                    brand_products = self.bunjang_parser.parse_products_from_search(search_url, limit=10)
                    if brand_products:
                        bunjang_products.extend(brand_products)
                        print(f"  Найдено {len(brand_products)} товаров бренда {brand_name}")
                
                if bunjang_products:
                    all_products.extend(bunjang_products)
                    print(f"Всего найдено {len(bunjang_products)} товаров на Bunjang")
            except Exception as e:
                print(f"Ошибка при парсинге Bunjang: {e}")
                import traceback
                traceback.print_exc()
            
            # 2. Парсим товары с FruitsFamily по конкретным ссылкам для каждого бренда
            print("Парсинг FruitsFamily...")
            try:
                fruits_products = []
                # Парсим товары для каждого бренда из списка по конкретным ссылкам
                for brand_info in config.BRANDS_TO_PARSE:
                    brand_name = brand_info['name']
                    print(f"  Парсинг бренда: {brand_name}...")
                    
                    # Используем конкретную ссылку для бренда из config
                    brand_url = config.FRUITS_BRAND_URLS.get(brand_name.lower())
                    if brand_url:
                        print(f"    URL: {brand_url}")
                        brand_products = self.fruits_parser.parse_products(url=brand_url, limit=20)
                    else:
                        # Если ссылки нет, используем поиск (резервный вариант)
                        print(f"    Ссылка для бренда {brand_name} не найдена в config, используем поиск")
                        search_query = brand_name
                        brand_products = self.fruits_parser.parse_products_from_search(search_query=search_query, limit=10)
                    
                    if brand_products:
                        fruits_products.extend(brand_products)
                        # Проверяем, что товары имеют необходимые поля
                        valid_products = [p for p in brand_products if p.get('link') and p.get('title')]
                        if len(valid_products) < len(brand_products):
                            print(f"  ВНИМАНИЕ: {len(brand_products) - len(valid_products)} товаров без ссылки или названия")
                        print(f"  Найдено {len(brand_products)} товаров бренда {brand_name} (валидных: {len(valid_products)})")
                    else:
                        print(f"  Товары не найдены для бренда {brand_name}")
                
                if fruits_products:
                    # Дедупликация товаров FruitsFamily по ссылке (один товар может быть на разных страницах брендов)
                    seen_links = set()
                    unique_fruits_products = []
                    duplicates_count = 0
                    
                    for product in fruits_products:
                        link = product.get('link', '')
                        if link:
                            # Используем ссылку как уникальный идентификатор
                            if link not in seen_links:
                                seen_links.add(link)
                                unique_fruits_products.append(product)
                            else:
                                duplicates_count += 1
                        else:
                            # Если нет ссылки, используем название для дедупликации
                            title = product.get('title', '').lower().strip()
                            if title and title not in seen_links:
                                seen_links.add(title)
                                unique_fruits_products.append(product)
                            else:
                                duplicates_count += 1
                    
                    if duplicates_count > 0:
                        print(f"  Удалено {duplicates_count} дубликатов товаров FruitsFamily")
                    
                    all_products.extend(unique_fruits_products)
                    valid_fruits = [p for p in unique_fruits_products if p.get('link') and p.get('title')]
                    print(f"Всего найдено {len(unique_fruits_products)} уникальных товаров на FruitsFamily (валидных: {len(valid_fruits)})")
                    if len(valid_fruits) < len(unique_fruits_products):
                        print(f"  ВНИМАНИЕ: {len(unique_fruits_products) - len(valid_fruits)} товаров FruitsFamily без ссылки или названия!")
                    
                    # Временная отладка: сохраняем первые несколько товаров для проверки
                    if valid_fruits:
                        print(f"  Примеры товаров FruitsFamily:")
                        for i, p in enumerate(valid_fruits[:3], 1):
                            print(f"    {i}. {p.get('title', 'Без названия')[:50]}")
                            print(f"       Ссылка: {p.get('link', 'Нет ссылки')[:80]}")
                            print(f"       Цена: {p.get('price', 'Нет цены')}")
                else:
                    print("  ВНИМАНИЕ: Не найдено ни одного товара на FruitsFamily!")
            except Exception as e:
                print(f"Ошибка при парсинге FruitsFamily: {e}")
                import traceback
                traceback.print_exc()
            
            if not all_products:
                print("Товары не найдены")
                return
            
            # Финальная дедупликация всех товаров по ссылке (на случай, если один товар есть на обоих сайтах)
            seen_all_links = set()
            unique_all_products = []
            for product in all_products:
                link = product.get('link', '')
                if link and link not in seen_all_links:
                    seen_all_links.add(link)
                    unique_all_products.append(product)
                elif not link:
                    # Если нет ссылки, используем название
                    title = product.get('title', '').lower().strip()
                    if title and title not in seen_all_links:
                        seen_all_links.add(title)
                        unique_all_products.append(product)
            
            if len(unique_all_products) < len(all_products):
                print(f"Удалено {len(all_products) - len(unique_all_products)} дубликатов между сайтами")
            
            all_products = unique_all_products
            
            print(f"Всего найдено {len(all_products)} уникальных товаров")
            
            # Подсчитываем товары по источникам для отладки
            bunjang_count = sum(1 for p in all_products if 'globalbunjang.com' in p.get('link', ''))
            fruits_count = sum(1 for p in all_products if 'fruitsfamily.com' in p.get('link', ''))
            print(f"  - С Bunjang: {bunjang_count} товаров")
            print(f"  - С FruitsFamily: {fruits_count} товаров")
            
            # Фильтруем только новые товары (которых нет в базе или они еще не отправлены)
            new_products = self.db.get_new_products(all_products, max_age_hours=config.NEW_PRODUCTS_MAX_AGE_HOURS)
            
            if not new_products:
                print("Новых товаров не найдено")
                # Отладочная информация
                print(f"  Все {len(all_products)} товаров были отфильтрованы как старые или уже отправленные")
                return
            
            # Подсчитываем новые товары по источникам
            new_bunjang = sum(1 for p in new_products if 'globalbunjang.com' in p.get('link', ''))
            new_fruits = sum(1 for p in new_products if 'fruitsfamily.com' in p.get('link', ''))
            print(f"Найдено {len(new_products)} новых товаров (только что обнаружено)")
            print(f"  - С Bunjang: {new_bunjang} новых")
            print(f"  - С FruitsFamily: {new_fruits} новых")
            
            # Если есть новые товары FruitsFamily, показываем примеры
            if new_fruits > 0:
                fruits_new = [p for p in new_products if 'fruitsfamily.com' in p.get('link', '')]
                print(f"  Примеры новых товаров FruitsFamily для отправки:")
                for i, p in enumerate(fruits_new[:3], 1):
                    print(f"    {i}. {p.get('title', 'Без названия')[:50]}")
            
            # Ограничиваем количество для отправки
            products_to_send = new_products[:config.MAX_PRODUCTS_PER_MESSAGE]
            
            # Проверяем, сколько товаров FruitsFamily будет отправлено
            fruits_to_send = sum(1 for p in products_to_send if 'fruitsfamily.com' in p.get('link', ''))
            if fruits_to_send > 0:
                print(f"Будет отправлено {fruits_to_send} товаров с FruitsFamily из {len(products_to_send)} товаров")
            
            # Отправляем новые товары всем подписчикам
            # Используем первый доступный парсер для форматирования (оба имеют одинаковый метод)
            parser_for_format = self.bunjang_parser if hasattr(self.bunjang_parser, 'format_product_message') else self.fruits_parser
            sent_count = await self.bot.send_products_to_all_users(
                user_ids,
                products_to_send,
                parser_for_format,
                max_per_batch=config.MAX_PRODUCTS_PER_MESSAGE
            )
            
            # Сохраняем отправленные товары в БД и отмечаем как отправленные
            fruits_sent = 0
            bunjang_sent = 0
            
            for i, product in enumerate(products_to_send):
                if i >= sent_count:
                    break
                
                # Подсчитываем по источникам
                if 'fruitsfamily.com' in product.get('link', ''):
                    fruits_sent += 1
                elif 'globalbunjang.com' in product.get('link', ''):
                    bunjang_sent += 1
                    
                # Сначала добавляем/обновляем товар в базе
                self.db.add_product(product, mark_as_sent=False)
                
                # Затем отмечаем как отправленный
                import hashlib
                product_id = product.get('link', product.get('title', ''))
                if product_id:
                    product_id_hash = hashlib.md5(product_id.encode()).hexdigest()
                    self.db.mark_as_sent(product_id_hash)
            
            print(f"Отправлено {sent_count} новых товаров пользователям:")
            print(f"  - С Bunjang: {bunjang_sent}")
            print(f"  - С FruitsFamily: {fruits_sent}")
            
            if fruits_sent == 0 and new_fruits > 0:
                print(f"  ВНИМАНИЕ: Найдено {new_fruits} новых товаров FruitsFamily, но ни один не был отправлен!")
                print(f"  Возможно, они были отфильтрованы при отправке или превышен лимит MAX_PRODUCTS_PER_MESSAGE")
            
        except Exception as e:
            print(f"Ошибка при парсинге и отправке: {e}")
            import traceback
            traceback.print_exc()
            # НЕ отправляем ошибки пользователям - только логируем
    
    
    async def setup_handlers(self):
        """Настройка обработчиков команд"""
        from telegram.ext import MessageHandler, filters
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("start_parse", self.start_parse_command))
        self.application.add_handler(CommandHandler("stop_parse", self.stop_parse_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        # Обработчик текстовых сообщений (кнопки меню)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
    
    async def run_bot(self):
        """Запуск бота с обработкой команд"""
        self.application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        await self.setup_handlers()
        
        # Запускаем бота в фоне
        await self.application.initialize()
        await self.application.start()
        
        # Очищаем предыдущие обновления, чтобы избежать конфликтов
        try:
            await self.application.bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            print(f"Предупреждение при очистке webhook: {e}")
        
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        print("Telegram бот запущен и готов к работе!")
        
        # Запускаем планировщик парсинга
        asyncio.create_task(self.run_scheduler_async())
        
        print(f"Парсинг будет выполняться каждые {config.PARSING_INTERVAL} секунд")
        
        # Ждем остановки
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nОстановка бота...")
            await self.application.stop()
            await self.application.shutdown()
            self.bunjang_parser.close()
            self.fruits_parser.close()
    
    async def run_scheduler_async(self):
        """Асинхронный планировщик"""
        await asyncio.sleep(5)  # Задержка при запуске для инициализации бота
        
        # Первый парсинг (если активен)
        if self.is_parsing_active:
            await self.parse_and_send()
        
        # Периодический парсинг
        while True:
            await asyncio.sleep(config.PARSING_INTERVAL)
            # Проверяем флаг перед парсингом
            if self.is_parsing_active:
                await self.parse_and_send()
            else:
                print("Парсинг остановлен пользователем, пропускаю...")

def main():
    # Проверка конфигурации
    if not config.TELEGRAM_BOT_TOKEN:
        print("ОШИБКА: Не указан TELEGRAM_BOT_TOKEN")
        print("Создайте файл .env и добавьте:")
        print("TELEGRAM_BOT_TOKEN=your_token_here")
        return
    
    bot = BunjangBot()
    
    # Запуск бота
    try:
        asyncio.run(bot.run_bot())
    except KeyboardInterrupt:
        print("\nОстановка бота...")
        bot.bunjang_parser.close()
        bot.fruits_parser.close()

if __name__ == '__main__':
    main()
