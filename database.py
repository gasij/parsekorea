import sqlite3
import json
from typing import List, Dict

class ProductDatabase:
    def __init__(self, db_file: str = 'products.db'):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Создаем таблицу products
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE,
                title TEXT,
                link TEXT,
                price TEXT,
                image TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        ''')
        conn.commit()
        
        # Проверяем и добавляем колонку first_seen_at если её нет
        try:
            cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'first_seen_at' not in columns:
                try:
                    # SQLite не поддерживает DEFAULT CURRENT_TIMESTAMP в ALTER TABLE
                    cursor.execute('ALTER TABLE products ADD COLUMN first_seen_at TIMESTAMP')
                    conn.commit()
                except sqlite3.OperationalError as e:
                    print(f"Предупреждение: не удалось добавить колонку first_seen_at: {e}")
        except Exception as e:
            print(f"Предупреждение при проверке колонок: {e}")
        
        # Создаем таблицу users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscribed INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def product_exists(self, product_id: str) -> bool:
        """Проверка существования товара"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM products WHERE product_id = ?', (product_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def add_product(self, product: Dict, mark_as_sent: bool = False) -> bool:
        """Добавление товара в базу данных"""
        # Генерируем ID товара на основе ссылки или названия
        product_id = product.get('link', product.get('title', ''))
        if not product_id:
            return False
        
        # Простой хэш для ID
        import hashlib
        product_id_hash = hashlib.md5(product_id.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            if self.product_exists(product_id_hash):
                # Товар уже существует, обновляем first_seen_at только если он старый
                cursor.execute('''
                    UPDATE products 
                    SET first_seen_at = CURRENT_TIMESTAMP 
                    WHERE product_id = ? AND first_seen_at < datetime('now', '-1 hour')
                ''', (product_id_hash,))
            else:
                # Новый товар
                sent_at = 'CURRENT_TIMESTAMP' if mark_as_sent else 'NULL'
                cursor.execute(f'''
                    INSERT INTO products (product_id, title, link, price, image, description, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, {sent_at})
                ''', (
                    product_id_hash,
                    product.get('title', ''),
                    product.get('link', ''),
                    product.get('price', ''),
                    product.get('image', ''),
                    product.get('description', '')
                ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def mark_as_sent(self, product_id: str):
        """Отметить товар как отправленный"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products SET sent_at = CURRENT_TIMESTAMP WHERE product_id = ?
        ''', (product_id,))
        conn.commit()
        conn.close()
    
    def get_new_products(self, products: List[Dict], max_age_hours: int = 1) -> List[Dict]:
        """Получить только новые товары за последний час (которых нет в базе или они были найдены только что)"""
        new_products = []
        from datetime import datetime, timedelta
        
        # Время, до которого считаем товары "новыми" (за последний час)
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        stats = {
            'no_id': 0,
            'new': 0,
            'already_sent': 0,
            'too_old': 0,
            'fruits_new': 0,
            'fruits_filtered': 0
        }
        
        for product in products:
            product_id = product.get('link', product.get('title', ''))
            if not product_id:
                stats['no_id'] += 1
                continue
            
            is_fruits = 'fruitsfamily.com' in product_id
                
            import hashlib
            product_id_hash = hashlib.md5(product_id.encode()).hexdigest()
            
            # Проверяем, существует ли товар в базе
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            try:
                # Пробуем запрос с first_seen_at
                cursor.execute('''
                    SELECT sent_at, first_seen_at, created_at FROM products WHERE product_id = ?
                ''', (product_id_hash,))
            except sqlite3.OperationalError:
                # Если колонки нет, используем упрощенный запрос
                try:
                    cursor.execute('''
                        SELECT sent_at, created_at FROM products WHERE product_id = ?
                    ''', (product_id_hash,))
                except sqlite3.OperationalError:
                    cursor.execute('''
                        SELECT sent_at FROM products WHERE product_id = ?
                    ''', (product_id_hash,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                # Товар полностью новый - добавляем
                new_products.append(product)
                stats['new'] += 1
                if is_fruits:
                    stats['fruits_new'] += 1
            else:
                # Товар существует в базе
                sent_at_str = result[0] if result else None
                
                # Проверяем возраст товара
                is_recent = False
                if len(result) >= 2:
                    # Пробуем определить время создания
                    time_str = result[1] if len(result) > 1 else None
                    if time_str:
                        try:
                            # Парсим время создания
                            if 'T' in str(time_str):
                                created_time = datetime.fromisoformat(str(time_str).replace('Z', '+00:00'))
                            else:
                                created_time = datetime.strptime(str(time_str), '%Y-%m-%d %H:%M:%S')
                            
                            # Проверяем, что товар был создан в течение последнего часа
                            if created_time >= cutoff_time:
                                is_recent = True
                        except:
                            # Если не удалось распарсить, считаем товар новым если не отправлен
                            is_recent = True
                    else:
                        is_recent = True
                else:
                    is_recent = True
                
                # Отправляем только если товар еще не был отправлен
                # Для FruitsFamily: если товар не отправлен, считаем его новым независимо от возраста
                # (так как товары на страницах брендов могут быть старыми, но мы их еще не отправляли)
                if not sent_at_str:
                    # Товар еще не отправлен - добавляем (даже если он старый)
                    # Это особенно важно для FruitsFamily, где мы парсим страницы брендов
                    new_products.append(product)
                    stats['new'] += 1
                    if is_fruits:
                        stats['fruits_new'] += 1
                else:
                    # Товар уже был отправлен
                    stats['already_sent'] += 1
                    if is_fruits:
                        stats['fruits_filtered'] += 1
        
        # Выводим статистику
        print(f"Статистика фильтрации товаров:")
        print(f"  - Новых товаров: {stats['new']} (FruitsFamily: {stats['fruits_new']})")
        print(f"  - Уже отправлено: {stats['already_sent']} (FruitsFamily: {stats['fruits_filtered']})")
        print(f"  - Слишком старых: {stats['too_old']}")
        print(f"  - Без ID: {stats['no_id']}")
        
        return new_products
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление или обновление пользователя"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    
    def subscribe_user(self, user_id: int) -> bool:
        """Подписать пользователя на рассылку"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET subscribed = 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?
        ''', (user_id,))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def unsubscribe_user(self, user_id: int) -> bool:
        """Отписать пользователя от рассылки"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET subscribed = 0 WHERE user_id = ?
        ''', (user_id,))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def get_subscribed_users(self) -> List[int]:
        """Получить список ID подписанных пользователей"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE subscribed = 1')
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return user_ids
    
    def is_subscribed(self, user_id: int) -> bool:
        """Проверить, подписан ли пользователь"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 1 if result else False

