import asyncio
from telegram import Bot
from telegram.error import TelegramError
from typing import List, Dict
import config

class TelegramBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
    
    async def send_product_to_user(self, user_id: int, product: Dict, parser) -> bool:
        """Отправка одного товара конкретному пользователю"""
        try:
            message = parser.format_product_message(product)
            
            # Если есть изображение, отправляем с фото
            if product.get('image'):
                try:
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=product['image'],
                        caption=message,
                        parse_mode='HTML'
                    )
                    return True
                except Exception as e:
                    print(f"Ошибка при отправке фото пользователю {user_id}, пробуем без фото: {e}")
            
            # Отправка без фото
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            return True
            
        except TelegramError as e:
            print(f"Ошибка Telegram при отправке товара пользователю {user_id}: {e}")
            return False
        except Exception as e:
            print(f"Общая ошибка при отправке товара пользователю {user_id}: {e}")
            return False
    
    async def send_product_to_all_users(self, user_ids: List[int], product: Dict, parser) -> int:
        """Отправка товара всем пользователям"""
        sent_count = 0
        for user_id in user_ids:
            success = await self.send_product_to_user(user_id, product, parser)
            if success:
                sent_count += 1
                # Небольшая задержка между сообщениями, чтобы не превысить лимиты API
                await asyncio.sleep(0.05)  # 50ms задержка
        
        return sent_count
    
    async def send_products_to_all_users(self, user_ids: List[int], products: List[Dict], parser, max_per_batch: int = 5) -> int:
        """Отправка нескольких товаров всем пользователям"""
        total_sent = 0
        for product in products[:max_per_batch]:
            sent_count = await self.send_product_to_all_users(user_ids, product, parser)
            total_sent += sent_count
            # Задержка между товарами
            await asyncio.sleep(1)
        
        return total_sent
    
    async def send_message_to_user(self, user_id: int, text: str) -> bool:
        """Отправка обычного сообщения пользователю"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode='HTML'
            )
            return True
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
            return False
    
    async def send_message_to_all_users(self, user_ids: List[int], text: str) -> int:
        """Отправка сообщения всем подписанным пользователям"""
        sent_count = 0
        for user_id in user_ids:
            success = await self.send_message_to_user(user_id, text)
            if success:
                sent_count += 1
            await asyncio.sleep(0.05)
        return sent_count
