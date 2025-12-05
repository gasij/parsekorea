import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from parser import BunjangParser
from bot import TelegramBot
from database import ProductDatabase
import config

class BunjangBot:
    def __init__(self):
        self.parser = BunjangParser(
            config.BUNJANG_URL, 
            use_selenium=config.USE_SELENIUM,
            brands_filter=config.BRANDS_TO_PARSE
        )
        self.bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)
        self.db = ProductDatabase(config.DB_FILE)
        self.application = None
    
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
        
        await update.message.reply_text(
            "Привет! Я бот для парсинга товаров с globalbunjang.com\n\n"
            "Вы подписаны на рассылку новых товаров.\n"
            "Используйте /stop чтобы отписаться от рассылки.\n"
            "Используйте /status чтобы проверить статус подписки."
        )
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stop"""
        user = update.effective_user
        self.db.unsubscribe_user(user.id)
        await update.message.reply_text("Вы отписаны от рассылки. Используйте /start чтобы подписаться снова.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status"""
        user = update.effective_user
        is_subscribed = self.db.is_subscribed(user.id)
        status_text = "подписаны" if is_subscribed else "не подписаны"
        await update.message.reply_text(f"Ваш статус: вы {status_text} на рассылку.")
    
    async def parse_and_send(self):
        """Парсинг и отправка новых товаров"""
        print("Начало парсинга...")
        
        try:
            # Получаем список подписанных пользователей
            user_ids = self.db.get_subscribed_users()
            
            if not user_ids:
                print("Нет подписанных пользователей")
                return
            
            print(f"Найдено {len(user_ids)} подписанных пользователей")
            
            # Парсим товары
            products = self.parser.parse_trending_products(limit=20)
            
            if not products:
                print("Товары не найдены")
                return
            
            # Фильтруем только новые товары (которых нет в базе или они еще не отправлены)
            new_products = self.db.get_new_products(products, max_age_hours=config.NEW_PRODUCTS_MAX_AGE_HOURS)
            
            if not new_products:
                print("Новых товаров не найдено")
                return
            
            print(f"Найдено {len(new_products)} новых товаров (только что обнаружено)")
            
            # Ограничиваем количество для отправки
            products_to_send = new_products[:config.MAX_PRODUCTS_PER_MESSAGE]
            
            # Отправляем новые товары всем подписчикам
            sent_count = await self.bot.send_products_to_all_users(
                user_ids,
                products_to_send,
                self.parser,
                max_per_batch=config.MAX_PRODUCTS_PER_MESSAGE
            )
            
            # Сохраняем отправленные товары в БД и отмечаем как отправленные
            for i, product in enumerate(products_to_send):
                if i >= sent_count:
                    break
                    
                # Сначала добавляем/обновляем товар в базе
                self.db.add_product(product, mark_as_sent=False)
                
                # Затем отмечаем как отправленный
                import hashlib
                product_id = product.get('link', product.get('title', ''))
                if product_id:
                    product_id_hash = hashlib.md5(product_id.encode()).hexdigest()
                    self.db.mark_as_sent(product_id_hash)
            
            print(f"Отправлено {sent_count} новых товаров пользователям")
            
        except Exception as e:
            print(f"Ошибка при парсинге и отправке: {e}")
            import traceback
            traceback.print_exc()
            # НЕ отправляем ошибки пользователям - только логируем
    
    
    async def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
    
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
            self.parser.close()
    
    async def run_scheduler_async(self):
        """Асинхронный планировщик"""
        await asyncio.sleep(5)  # Задержка при запуске для инициализации бота
        
        # Первый парсинг
        await self.parse_and_send()
        
        # Периодический парсинг
        while True:
            await asyncio.sleep(config.PARSING_INTERVAL)
            await self.parse_and_send()

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
        bot.parser.close()

if __name__ == '__main__':
    main()
