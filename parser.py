import requests
from bs4 import BeautifulSoup
import time
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin
import re

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class BunjangParser:
    def __init__(self, base_url: str = 'https://globalbunjang.com/', use_selenium: bool = False, brands_filter: List[Dict] = None):
        self.base_url = base_url
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.brands_filter = brands_filter or []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.driver = None
    
    def get_page_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Получить HTML страницы с помощью Selenium"""
        if not SELENIUM_AVAILABLE:
            return None
        
        try:
            if not self.driver:
                print("  Инициализация Selenium драйвера...")
                try:
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')
                    self.driver = webdriver.Chrome(options=chrome_options)
                    print("  Selenium драйвер успешно инициализирован")
                except Exception as e:
                    print(f"  ОШИБКА при инициализации Selenium драйвера: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            else:
                # Проверяем, что драйвер еще работает
                try:
                    self.driver.current_url
                except:
                    print("  Драйвер не работает, пересоздаем...")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    # Пробуем создать заново
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')
                    self.driver = webdriver.Chrome(options=chrome_options)
                    print("  Selenium драйвер пересоздан")
            
            self.driver.get(url)
            # Ждем загрузки контента
            time.sleep(3)
            
            # Прокручиваем страницу для загрузки динамического контента
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            try:
                html = self.driver.page_source
                if not html or len(html) < 100:
                    print(f"  ВНИМАНИЕ: Получен пустой или очень короткий HTML ({len(html) if html else 0} символов)")
                    return None
                print(f"  HTML получен, размер: {len(html)} символов")
                return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                print(f"  ОШИБКА при получении HTML: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"Ошибка при получении страницы через Selenium {url}: {e}")
            return None
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получить HTML страницы"""
        if self.use_selenium:
            return self.get_page_selenium(url)
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Ошибка при получении страницы {url}: {e}")
            # Пробуем через Selenium если обычный запрос не сработал
            if SELENIUM_AVAILABLE:
                print("Пробуем через Selenium...")
                return self.get_page_selenium(url)
            return None
    
    def close(self):
        """Закрыть Selenium драйвер"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def parse_product_card(self, card_element) -> Optional[Dict]:
        """Парсинг карточки товара"""
        product = {}
        
        try:
            # Получаем весь текст из элемента для анализа
            all_text = card_element.get_text(separator=' ', strip=True)
            
            # Название товара - ищем в разных местах
            title = None
            title_selectors = [
                # По классам
                lambda x: x.find(['h1', 'h2', 'h3', 'h4', 'h5'], class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower())),
                lambda x: x.find(['div', 'span', 'p'], class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower())),
                # По атрибутам
                lambda x: x.find(['div', 'span', 'p'], attrs={'data-title': True}),
                # Просто любой заголовок
                lambda x: x.find(['h1', 'h2', 'h3', 'h4', 'h5']),
                # Текст из ссылки
                lambda x: x.find('a', href=True),
                # Alt текст изображения
                lambda x: x.find('img', alt=True),
            ]
            
            for selector in title_selectors:
                elem = selector(card_element)
                if elem:
                    if elem.name == 'img':
                        title = elem.get('alt', '').strip()
                    else:
                        title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        break
            
            # Если не нашли через селекторы, берем первый значимый текст
            if not title or len(title) < 3:
                # Пробуем взять текст из ссылки
                link_elem = card_element.find('a', href=True)
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    # Если в ссылке нет текста, берем из родителя
                    if not title or len(title) < 3:
                        parent = link_elem.parent
                        if parent:
                            title = parent.get_text(strip=True)
            
            # Если все еще нет названия, берем первый значимый текст из всего элемента
            if not title or len(title) < 3:
                # Убираем служебные слова и берем первые слова
                words = all_text.split()
                if len(words) > 2:
                    title = ' '.join(words[:10])  # Берем первые 10 слов
            
            # Проверяем, что это не категория (исключаем общие слова)
            if title:
                title_lower = title.lower()
                # Исключаем категории и навигационные элементы
                exclude_words = ['arrow', 'more', 'category', 'search', 'home', 'menu', 'cart', 
                               'boy group', 'girl group', "men's style", "women's", 'pokémon',
                               'rare figures', 'authentic', 'certified', 'luxury', 'icon_exit',
                               'korean site', 'let\'s talk', 'trending', 'popular', 'top']
                if any(word in title_lower for word in exclude_words):
                    # Это скорее всего категория, пропускаем
                    return None
                
                # Проверяем ссылку - если это категория или бренд, но не товар
                link = product.get('link', '') or (card_element.find('a', href=True) and card_element.find('a', href=True).get('href', ''))
                if link:
                    if '/category/' in link or '/brand/' in link:
                        # Это категория или бренд, но можем оставить если есть цена
                        if not product.get('price'):
                            return None
            
            if title and len(title) > 3:
                product['title'] = title[:200]  # Ограничиваем длину
            
            # Получаем ссылку
            link_elem = card_element.find('a', href=True)
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                product['link'] = urljoin(self.base_url, href)
            elif card_element.name == 'a' and card_element.get('href'):
                product['link'] = urljoin(self.base_url, card_element.get('href'))
            
            # Цена - ищем в разных форматах
            price = None
            price_patterns = [
                # По классам
                lambda x: x.find(['span', 'div', 'p', 'strong', 'b'], class_=lambda c: c and 'price' in c.lower()),
                # По тексту с символами валют
                lambda x: x.find(string=re.compile(r'[₩$€£¥]\s*\d+[\d,.]*')),
                lambda x: x.find(string=re.compile(r'\d+[\d,.]*\s*[₩$€£¥]')),
                lambda x: x.find(string=re.compile(r'\d+[\d,.]*\s*(won|원|KRW|USD|EUR|USD)')),
                # Любой текст с числами и валютными символами
                lambda x: re.search(r'[₩$€£¥]\s*\d+[\d,.]*|\d+[\d,.]*\s*[₩$€£¥원]', all_text),
            ]
            
            for pattern in price_patterns:
                result = pattern(card_element)
                if result:
                    if hasattr(result, 'group'):
                        price = result.group(0).strip()
                    elif hasattr(result, 'get_text'):
                        price = result.get_text(strip=True)
                    else:
                        price = str(result).strip()
                    if price:
                        break
            
            if price:
                product['price'] = price[:50]  # Ограничиваем длину
            
            # Изображение
            img_elem = card_element.find('img')
            if img_elem:
                img_src = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or
                          img_elem.get('data-original'))
                if img_src:
                    product['image'] = urljoin(self.base_url, img_src)
            
            # Дополнительная информация
            desc_elem = card_element.find(['p', 'div', 'span'], class_=lambda x: x and ('desc' in x.lower() or 'description' in x.lower() or 'info' in x.lower()))
            if desc_elem:
                product['description'] = desc_elem.get_text(strip=True)[:300]
            elif all_text and len(all_text) > len(title or ''):
                # Если есть дополнительный текст, используем его как описание
                desc = all_text.replace(title or '', '', 1).strip()
                if desc and len(desc) > 10:
                    product['description'] = desc[:300]
            
        except Exception as e:
            print(f"Ошибка при парсинге карточки товара: {e}")
            import traceback
            traceback.print_exc()
        
        # Проверяем фильтр по брендам
        if self.brands_filter and product.get('title'):
            if not self._matches_brand_filter(product):
                return None
        
        # Возвращаем товар если есть хотя бы название или ссылка
        if product.get('title') and len(product.get('title', '')) > 3:
            return product
        elif product.get('link'):
            # Если есть ссылка, но нет названия, используем ссылку как название
            product['title'] = product['link'].split('/')[-1] or 'Товар'
            # Проверяем фильтр еще раз после установки названия
            if self.brands_filter:
                if not self._matches_brand_filter(product):
                    return None
            return product
        
        return None
    
    def _matches_brand_filter(self, product: Dict) -> bool:
        """Проверяет, соответствует ли товар фильтру брендов"""
        if not self.brands_filter:
            return True
        
        title = product.get('title', '').lower()
        description = product.get('description', '').lower()
        text_to_check = f"{title} {description}"
        
        for brand_info in self.brands_filter:
            brand_name = brand_info['name'].lower()
            category = brand_info.get('category')
            
            # Проверяем, содержит ли товар название бренда
            if brand_name in text_to_check:
                # Если указана категория (например, только обувь для maison margiela)
                if category:
                    category_keywords = {
                        'shoes': ['shoe', 'sneaker', 'boot', 'sandal', 'slipper', 'loafer', 'oxford', 'heel', 'footwear', 'обувь', 'кроссовки', 'ботинки', 'sneakers', 'boots']
                    }
                    if category in category_keywords:
                        # Проверяем, что это обувь
                        keywords = category_keywords[category]
                        if any(keyword in text_to_check for keyword in keywords):
                            return True
                        else:
                            continue  # Бренд совпадает, но категория не подходит
                else:
                    # Категория не указана, бренд подходит
                    return True
        
        return False
    
    def parse_products(self, category: str = None, limit: int = 20) -> List[Dict]:
        """Парсинг товаров с главной страницы или категории"""
        products = []
        
        # Формируем URL
        url = self.base_url
        if category:
            url = urljoin(self.base_url, category)
        
        print(f"Парсинг страницы: {url}")
        soup = self.get_page(url)
        
        if not soup:
            # Если обычный парсинг не сработал и Selenium доступен, пробуем его
            if not self.use_selenium and SELENIUM_AVAILABLE:
                print("Пробуем использовать Selenium для динамического контента...")
                soup = self.get_page_selenium(url)
            
            if not soup:
                return products
        
        # Ищем карточки товаров - пробуем разные селекторы
        product_cards = []
        
        # Селекторы для поиска товаров
        selectors_to_try = [
            # По классам с product/item
            lambda s: s.find_all('div', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower() or 'card' in x.lower())),
            lambda s: s.find_all('article', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            lambda s: s.find_all('a', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            # По структуре - ссылки с изображениями и текстом (исключаем категории)
            lambda s: [elem for elem in s.find_all('a', href=True) 
                      if elem.find('img') and elem.get_text(strip=True) and len(elem.get_text(strip=True)) > 10
                      and '/category/' not in (elem.get('href', '') or '')
                      and '/search' not in (elem.get('href', '') or '')],
            # По data-атрибутам
            lambda s: s.find_all(['div', 'article'], attrs={'data-product-id': True}),
            lambda s: s.find_all(['div', 'article'], attrs={'data-item-id': True}),
        ]
        
        for selector_func in selectors_to_try:
            try:
                product_cards = selector_func(soup)
                if product_cards and len(product_cards) > 0:
                    print(f"Найдено {len(product_cards)} потенциальных товаров")
                    break
            except:
                continue
        
        # Если не нашли, ищем в контейнерах (исключаем категории)
        if not product_cards:
            containers = soup.find_all(['div', 'section', 'article'], class_=lambda x: x and (
                'list' in x.lower() or 'grid' in x.lower() or 'container' in x.lower() or 
                'products' in x.lower() or 'items' in x.lower()
            ))
            for container in containers:
                links = container.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    # Пропускаем категории и поиск
                    if '/category/' in href or '/search' in href:
                        continue
                    if link.find('img') and link.get_text(strip=True) and len(link.get_text(strip=True)) > 10:
                        product_cards.append(link.parent if link.parent.name in ['div', 'article'] else link)
        
        # Парсим найденные карточки
        seen_titles = set()
        parsed_count = 0
        for card in product_cards[:limit * 3]:  # Берем больше, так как многие могут не распарситься
            parsed_count += 1
            product = self.parse_product_card(card)
            if product and product.get('title'):
                # Убираем дубликаты по названию
                title_key = product['title'].lower().strip()
                if title_key not in seen_titles and len(title_key) > 3:
                    seen_titles.add(title_key)
                    products.append(product)
                    if len(products) >= limit:
                        break
        
        print(f"Обработано {parsed_count} элементов, успешно распарсено {len(products)} товаров")
        
        # Если товаров мало и Selenium доступен, пробуем его
        if len(products) < 3 and not self.use_selenium and SELENIUM_AVAILABLE:
            print("Найдено мало товаров, пробуем использовать Selenium...")
            selenium_soup = self.get_page_selenium(url)
            if selenium_soup:
                # Повторяем парсинг с Selenium
                selenium_products = []
                selenium_cards = []
                for selector_func in selectors_to_try:
                    try:
                        selenium_cards = selector_func(selenium_soup)
                        if selenium_cards and len(selenium_cards) > 0:
                            print(f"Найдено {len(selenium_cards)} элементов через Selenium")
                            break
                    except:
                        continue
                
                for card in selenium_cards[:limit * 2]:
                    product = self.parse_product_card(card)
                    if product and product.get('title'):
                        title_key = product['title'].lower().strip()
                        if title_key not in seen_titles and len(title_key) > 3:
                            seen_titles.add(title_key)
                            selenium_products.append(product)
                            if len(selenium_products) >= limit - len(products):
                                break
                
                products.extend(selenium_products)
                print(f"Через Selenium найдено еще {len(selenium_products)} товаров")
        
        return products[:limit]
    
    def parse_trending_products(self, limit: int = 10) -> List[Dict]:
        """Парсинг трендовых товаров с фильтрацией по брендам"""
        products = []
        
        # Если есть фильтр по брендам, ищем товары по каждому бренду
        if self.brands_filter:
            print(f"Поиск товаров брендов: {[b['name'] for b in self.brands_filter]}")
            
            # Формируем поисковые запросы для каждого бренда
            for brand_info in self.brands_filter:
                brand_name = brand_info['name']
                category = brand_info.get('category')
                
                # Формируем поисковый запрос
                search_query = brand_name
                if category == 'shoes':
                    search_query = f"{brand_name} shoes"
                
                print(f"Поиск товаров: {search_query}")
                
                # Парсим результаты поиска
                search_url = f"{self.base_url}search?q={search_query.replace(' ', '%20')}"
                search_products = self.parse_products_from_search(search_url, limit=limit // len(self.brands_filter) + 1)
                products.extend(search_products)
                
                if len(products) >= limit:
                    break
        else:
            # Если фильтра нет, используем обычный парсинг
            main_products = self.parse_products(limit=limit)
            products.extend(main_products)
            
            # Если товаров мало, пробуем парсить из категорий/брендов
            if len(products) < limit:
                print(f"Найдено только {len(products)} товаров, ищем в категориях...")
                
                # Парсим главную страницу для поиска категорий
                soup = self.get_page(self.base_url)
                if soup:
                    # Ищем ссылки на категории и бренды
                    category_links = []
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        # Ищем ссылки на категории, бренды или товары
                        if ('/category/' in href or '/brand/' in href or '/product/' in href or '/item/' in href) and href not in category_links:
                            category_links.append(href)
                    
                    # Парсим первые несколько категорий/брендов
                    for cat_link in category_links[:3]:  # Берем первые 3
                        full_url = urljoin(self.base_url, cat_link)
                        print(f"Парсинг категории: {full_url}")
                        cat_products = self.parse_products(category=cat_link, limit=5)
                        products.extend(cat_products)
                        
                        if len(products) >= limit:
                            break
        
        return products[:limit]
    
    def parse_products_from_search(self, search_url: str, limit: int = 20) -> List[Dict]:
        """Парсинг товаров из результатов поиска"""
        products = []
        
        print(f"Парсинг результатов поиска: {search_url}")
        soup = self.get_page(search_url)
        
        if not soup:
            if not self.use_selenium and SELENIUM_AVAILABLE:
                print("Пробуем использовать Selenium для поиска...")
                soup = self.get_page_selenium(search_url)
            
            if not soup:
                return products
        
        # Ищем карточки товаров в результатах поиска
        product_cards = []
        selectors_to_try = [
            lambda s: s.find_all('div', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower() or 'card' in x.lower())),
            lambda s: s.find_all('article', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            lambda s: s.find_all('a', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            lambda s: [elem for elem in s.find_all('a', href=True) 
                      if elem.find('img') and elem.get_text(strip=True) and len(elem.get_text(strip=True)) > 10
                      and '/category/' not in (elem.get('href', '') or '')
                      and '/search' not in (elem.get('href', '') or '')],
        ]
        
        for selector_func in selectors_to_try:
            try:
                product_cards = selector_func(soup)
                if product_cards and len(product_cards) > 0:
                    print(f"Найдено {len(product_cards)} потенциальных товаров в результатах поиска")
                    break
            except:
                continue
        
        # Парсим найденные карточки
        seen_titles = set()
        for card in product_cards[:limit * 2]:
            product = self.parse_product_card(card)
            if product and product.get('title'):
                title_key = product['title'].lower().strip()
                if title_key not in seen_titles and len(title_key) > 3:
                    seen_titles.add(title_key)
                    products.append(product)
                    if len(products) >= limit:
                        break
        
        print(f"Успешно распарсено {len(products)} товаров из результатов поиска")
        return products
    
    def format_product_message(self, product: Dict) -> str:
        """Форматирование товара для отправки в Telegram"""
        from currency import converter
        
        message = f"<b>{product.get('title', 'Без названия')}</b>\n\n"
        
        if product.get('price'):
            original_price = product['price']
            # Конвертируем цену в рубли (для Bunjang обычно KRW)
            rubles = converter.convert_to_rubles(original_price, default_currency='KRW')
            if rubles:
                message += f"Цена: {original_price} (~{rubles})\n"
            else:
                message += f"Цена: {original_price}\n"
        
        if product.get('description'):
            message += f"{product['description'][:200]}...\n"
        
        if product.get('link'):
            message += f"\n<a href='{product['link']}'>Ссылка на товар</a>"
        
        return message


class FruitsFamilyParser:
    """Парсер для сайта fruitsfamily.com"""
    
    def __init__(self, base_url: str = 'https://fruitsfamily.com/', use_selenium: bool = False, brands_filter: List[Dict] = None):
        self.base_url = base_url
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.brands_filter = brands_filter or []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.driver = None
    
    def get_page_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Получить HTML страницы с помощью Selenium"""
        if not SELENIUM_AVAILABLE:
            print("  Selenium не доступен")
            return None
        
        try:
            if not self.driver:
                print("  Инициализация Selenium драйвера...")
                try:
                    chrome_options = Options()
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    chrome_options.add_experimental_option('useAutomationExtension', False)
                    chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')
                    self.driver = webdriver.Chrome(options=chrome_options)
                    print("  Selenium драйвер успешно инициализирован")
                except Exception as e:
                    print(f"  ОШИБКА при инициализации Selenium драйвера: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            print(f"  Загрузка страницы через Selenium: {url}")
            try:
                self.driver.get(url)
                print(f"  Страница загружена, ожидание загрузки контента...")
            except Exception as e:
                print(f"  ОШИБКА при загрузке URL через Selenium: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            # Ждем загрузки контента
            time.sleep(4)
            
            # Прокручиваем страницу для загрузки динамического контента
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except Exception as e:
                print(f"  Предупреждение при прокрутке страницы: {e}")
            
            try:
                html = self.driver.page_source
                if not html or len(html) < 100:
                    print(f"  ВНИМАНИЕ: Получен пустой или очень короткий HTML ({len(html) if html else 0} символов)")
                    return None
                print(f"  HTML получен, размер: {len(html)} символов")
                return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                print(f"  ОШИБКА при получении HTML: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"  КРИТИЧЕСКАЯ ОШИБКА при получении страницы через Selenium {url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получить HTML страницы"""
        if self.use_selenium:
            print(f"  Используем Selenium для загрузки страницы")
            result = self.get_page_selenium(url)
            if not result:
                print(f"  Selenium не смог загрузить страницу, пробуем обычный HTTP запрос...")
                # Пробуем обычный запрос как fallback
                try:
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    print(f"  HTTP запрос успешен, размер ответа: {len(response.content)} байт")
                    return BeautifulSoup(response.content, 'html.parser')
                except Exception as e:
                    print(f"  HTTP запрос также не удался: {e}")
            return result
        
        try:
            print(f"  Пробуем обычный HTTP запрос...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            print(f"  HTTP запрос успешен, размер ответа: {len(response.content)} байт")
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"  Ошибка при обычном HTTP запросе {url}: {e}")
            # Пробуем через Selenium если обычный запрос не сработал
            if SELENIUM_AVAILABLE:
                print("  Пробуем через Selenium...")
                return self.get_page_selenium(url)
            return None
    
    def close(self):
        """Закрыть Selenium драйвер"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def parse_product_card(self, card_element) -> Optional[Dict]:
        """Парсинг карточки товара с fruitsfamily.com"""
        product = {}
        
        try:
            all_text = card_element.get_text(separator=' ', strip=True)
            
            # Название товара
            title = None
            title_selectors = [
                # По классам, специфичным для fruitsfamily
                lambda x: x.find(['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span', 'p'], 
                               class_=lambda c: c and ('title' in c.lower() or 'name' in c.lower() or 'product' in c.lower())),
                lambda x: x.find('a', href=True),
                lambda x: x.find('img', alt=True),
            ]
            
            for selector in title_selectors:
                elem = selector(card_element)
                if elem:
                    if elem.name == 'img':
                        title = elem.get('alt', '').strip()
                    else:
                        title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        break
            
            # Если не нашли, берем первый значимый текст
            if not title or len(title) < 3:
                link_elem = card_element.find('a', href=True)
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    if not title or len(title) < 3:
                        parent = link_elem.parent
                        if parent:
                            title = parent.get_text(strip=True)
            
            if not title or len(title) < 3:
                words = all_text.split()
                if len(words) > 2:
                    title = ' '.join(words[:15])
            
            # Исключаем служебные элементы
            if title:
                title_lower = title.lower()
                exclude_words = ['arrow', 'more', 'category', 'search', 'home', 'menu', 'cart',
                               '인기', '브랜드', '랭킹', '상품', '검색', '홈', '마켓', '판매',
                               'popular', 'brand', 'ranking', 'product', 'search']
                if any(word in title_lower for word in exclude_words) and len(title) < 20:
                    return None
            
            if title and len(title) > 3:
                product['title'] = title[:200]
            
            # Ссылка
            link_elem = card_element.find('a', href=True)
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                product['link'] = urljoin(self.base_url, href)
            elif card_element.name == 'a' and card_element.get('href'):
                product['link'] = urljoin(self.base_url, card_element.get('href'))
            
            # Цена - ищем корейские валюты (원, KRW)
            price = None
            price_patterns = [
                lambda x: x.find(['span', 'div', 'p', 'strong', 'b'], 
                               class_=lambda c: c and 'price' in c.lower()),
                lambda x: re.search(r'\d+[\d,.]*\s*원|\d+[\d,.]*\s*KRW|원\s*\d+[\d,.]*|KRW\s*\d+[\d,.]*', all_text),
                lambda x: re.search(r'\d+[\d,.]*\s*[₩$€£¥]|[₩$€£¥]\s*\d+[\d,.]*', all_text),
            ]
            
            for pattern in price_patterns:
                try:
                    result = pattern(card_element)
                    if result:
                        if hasattr(result, 'group') and callable(getattr(result, 'group', None)):
                            price = result.group(0).strip()
                        elif hasattr(result, 'get_text'):
                            price = result.get_text(strip=True)
                        else:
                            price = str(result).strip()
                        if price:
                            break
                except:
                    continue
            
            if price:
                product['price'] = price[:50]
            
            # Изображение
            img_elem = card_element.find('img')
            if img_elem:
                img_src = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or
                          img_elem.get('data-original') or
                          img_elem.get('data-srcset'))
                if img_src:
                    # Обрабатываем srcset если есть
                    if ' ' in img_src:
                        img_src = img_src.split()[0]
                    product['image'] = urljoin(self.base_url, img_src)
            
            # Описание
            desc_elem = card_element.find(['p', 'div', 'span'], 
                                        class_=lambda x: x and ('desc' in x.lower() or 'description' in x.lower() or 'info' in x.lower()))
            if desc_elem:
                product['description'] = desc_elem.get_text(strip=True)[:300]
            elif all_text and len(all_text) > len(title or ''):
                desc = all_text.replace(title or '', '', 1).strip()
                if desc and len(desc) > 10:
                    product['description'] = desc[:300]
            
        except Exception as e:
            print(f"Ошибка при парсинге карточки товара: {e}")
            import traceback
            traceback.print_exc()
        
        # Проверяем фильтр по брендам
        if self.brands_filter and product.get('title'):
            if not self._matches_brand_filter(product):
                return None
        
        # Возвращаем товар если есть хотя бы название или ссылка
        if product.get('title') and len(product.get('title', '')) > 3:
            return product
        elif product.get('link'):
            product['title'] = product['link'].split('/')[-1] or 'Товар'
            if self.brands_filter:
                if not self._matches_brand_filter(product):
                    return None
            return product
        
        return None
    
    def _matches_brand_filter(self, product: Dict) -> bool:
        """Проверяет, соответствует ли товар фильтру брендов"""
        if not self.brands_filter:
            return True
        
        title = product.get('title', '').lower()
        description = product.get('description', '').lower()
        text_to_check = f"{title} {description}"
        
        for brand_info in self.brands_filter:
            brand_name = brand_info['name'].lower()
            category = brand_info.get('category')
            
            # Создаем варианты написания бренда для более гибкого поиска
            brand_variants = [brand_name]
            
            # Специальные случаи для брендов
            if brand_name == 'cp company':
                brand_variants.extend(['c.p. company', 'cpcompany', 'c p company', 'cp комп니', 'cp컴퍼니', 'cp company', 'c.p.company'])
            elif brand_name == 'maison margiela':
                brand_variants.extend(['margiela', 'maisonmargiela', '메종 마르지엘라', '마르지엘라', '메종마르지엘라', '메종 마르지엘라'])
            elif brand_name == 'stone island':
                brand_variants.extend(['stoneisland', '스톤아일랜드', 'stone island'])
            elif brand_name == 'project gr':
                brand_variants.extend(['projectgr', 'project gr', '프로젝트 gr', 'projectgr', '프로젝트gr'])
            elif brand_name == 'grailz':
                brand_variants.extend(['grailz', '그레일즈'])
            
            # Проверяем все варианты
            brand_found = any(variant in text_to_check for variant in brand_variants)
            
            if brand_found:
                if category:
                    category_keywords = {
                        'shoes': ['shoe', 'sneaker', 'boot', 'sandal', 'slipper', 'loafer', 'oxford', 'heel', 'footwear', 
                                 'обувь', 'кроссовки', 'ботинки', 'sneakers', 'boots', '신발', '운동화', '부츠']
                    }
                    if category in category_keywords:
                        keywords = category_keywords[category]
                        if any(keyword in text_to_check for keyword in keywords):
                            return True
                        else:
                            continue
                else:
                    return True
        
        return False
    
    def parse_products(self, url: str = None, limit: int = 50) -> List[Dict]:
        """Парсинг товаров с указанной страницы"""
        products = []
        
        if not url:
            url = self.base_url
        
        # Проверяем, является ли URL страницей конкретного бренда
        # Если да, то фильтр брендов не нужен (все товары уже отфильтрованы)
        is_brand_page = '/brand/' in url or ('/search/' in url and '?sort=' in url)
        
        print(f"Парсинг страницы: {url}")
        if is_brand_page:
            print("  (Страница бренда - фильтр брендов будет отключен)")
        
        # Сначала пробуем обычный запрос
        soup = self.get_page(url)
        
        if not soup:
            print("  Обычный запрос не удался, пробуем Selenium...")
            if self.use_selenium and SELENIUM_AVAILABLE:
                print("  Используем Selenium для динамического контента...")
                soup = self.get_page_selenium(url)
            elif not self.use_selenium and SELENIUM_AVAILABLE:
                print("  Selenium доступен, но не включен. Пробуем использовать его...")
                soup = self.get_page_selenium(url)
            
            if not soup:
                print(f"  ОШИБКА: Не удалось загрузить страницу {url}")
                print(f"  use_selenium={self.use_selenium}, SELENIUM_AVAILABLE={SELENIUM_AVAILABLE}")
                return products
        else:
            print(f"  Страница успешно загружена (обычный запрос)")
        
        # Ищем карточки товаров
        product_cards = []
        
        selectors_to_try = [
            # По классам с product/item/card
            lambda s: s.find_all('div', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower() or 'card' in x.lower())),
            lambda s: s.find_all('article', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            lambda s: s.find_all('a', class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower())),
            # Ссылки с изображениями и текстом
            lambda s: [elem for elem in s.find_all('a', href=True) 
                      if elem.find('img') and elem.get_text(strip=True) and len(elem.get_text(strip=True)) > 10
                      and '/product/' in (elem.get('href', '') or '')],
            # По data-атрибутам
            lambda s: s.find_all(['div', 'article'], attrs={'data-product-id': True}),
            lambda s: s.find_all(['div', 'article'], attrs={'data-item-id': True}),
        ]
        
        for selector_func in selectors_to_try:
            try:
                product_cards = selector_func(soup)
                if product_cards and len(product_cards) > 0:
                    print(f"Найдено {len(product_cards)} потенциальных товаров")
                    break
            except:
                continue
        
        # Если не нашли, ищем в контейнерах
        if not product_cards:
            print("  Стандартные селекторы не нашли товары, ищем в контейнерах...")
            containers = soup.find_all(['div', 'section', 'article', 'ul', 'li'], 
                                     class_=lambda x: x and (
                                         'list' in x.lower() or 'grid' in x.lower() or 'container' in x.lower() or 
                                         'products' in x.lower() or 'items' in x.lower() or 'card' in x.lower()
                                     ))
            print(f"  Найдено {len(containers)} контейнеров")
            for container in containers:
                links = container.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if '/product/' in href or '/item/' in href or '/goods/' in href or '/brand/' in href:
                        if link.find('img') and link.get_text(strip=True) and len(link.get_text(strip=True)) > 10:
                            product_cards.append(link.parent if link.parent.name in ['div', 'article', 'li'] else link)
            
            if not product_cards:
                print("  ВНИМАНИЕ: Не найдено ни одной карточки товара!")
                # Пробуем найти любые ссылки с изображениями
                all_links = soup.find_all('a', href=True)
                links_with_img = [link for link in all_links if link.find('img')]
                print(f"  Найдено {len(all_links)} ссылок, из них {len(links_with_img)} с изображениями")
                if links_with_img:
                    print(f"  Примеры ссылок с изображениями:")
                    for i, link in enumerate(links_with_img[:5], 1):
                        href = link.get('href', '')[:80]
                        text = link.get_text(strip=True)[:50]
                        print(f"    {i}. {href} - {text}")
        
        # Парсим найденные карточки
        # Если это страница конкретного бренда, временно отключаем фильтр
        original_brands_filter = self.brands_filter
        skip_brand_filter = is_brand_page
        if skip_brand_filter:
            self.brands_filter = None  # Временно отключаем фильтр для страниц брендов
            print("  Фильтр брендов ОТКЛЮЧЕН для страницы бренда")
        
        seen_titles = set()
        parsed_count = 0
        filtered_count = 0
        no_title_count = 0
        no_link_count = 0
        
        print(f"  Начинаем парсинг {len(product_cards)} карточек товаров...")
        for card in product_cards[:limit * 3]:
            parsed_count += 1
            product = self.parse_product_card(card)
            
            if product:
                if product.get('title') and len(product.get('title', '')) > 3:
                    title_key = product['title'].lower().strip()
                    if title_key not in seen_titles:
                        seen_titles.add(title_key)
                        # Проверяем наличие ссылки
                        if product.get('link'):
                            products.append(product)
                            if len(products) >= limit:
                                break
                        else:
                            no_link_count += 1
                            if no_link_count <= 3:  # Показываем первые 3 примера
                                print(f"    Товар без ссылки: {product.get('title', 'Без названия')[:50]}")
                else:
                    no_title_count += 1
                    if no_title_count <= 3:  # Показываем первые 3 примера
                        print(f"    Товар без названия, ссылка: {product.get('link', 'Нет')[:60]}")
            else:
                # Товар был отфильтрован
                filtered_count += 1
                if filtered_count <= 3:  # Показываем первые 3 примера отфильтрованных
                    try:
                        card_text = card.get_text(strip=True)[:50] if hasattr(card, 'get_text') else str(card)[:50]
                        print(f"    Товар отфильтрован: {card_text}")
                    except:
                        print(f"    Товар отфильтрован (не удалось получить текст)")
        
        # Восстанавливаем фильтр
        self.brands_filter = original_brands_filter
        
        print(f"Обработано {parsed_count} элементов:")
        print(f"  - Успешно распарсено: {len(products)}")
        print(f"  - Отфильтровано: {filtered_count}")
        print(f"  - Без названия: {no_title_count}")
        print(f"  - Без ссылки: {no_link_count}")
        
        if filtered_count > 0 and len(products) == 0 and not is_brand_page:
            print(f"ВНИМАНИЕ: Все товары отфильтрованы! Возможно, фильтр брендов слишком строгий.")
        
        if len(products) > 0:
            # Показываем примеры распарсенных товаров
            print(f"  Примеры распарсенных товаров:")
            for i, p in enumerate(products[:3], 1):
                print(f"    {i}. {p.get('title', 'Без названия')[:50]}")
                print(f"       Ссылка: {p.get('link', 'Нет')[:60]}")
        
        return products[:limit]
    
    def parse_products_from_search(self, search_url: str = None, search_query: str = None, limit: int = 50) -> List[Dict]:
        """Парсинг товаров из результатов поиска"""
        if search_url:
            return self.parse_products(url=search_url, limit=limit)
        elif search_query:
            search_url = f"{self.base_url}search?q={search_query.replace(' ', '%20')}"
            return self.parse_products(url=search_url, limit=limit)
        else:
            return self.parse_products(limit=limit)
    
    def format_product_message(self, product: Dict) -> str:
        """Форматирование товара для отправки в Telegram"""
        from currency import converter
        
        message = f"<b>{product.get('title', 'Без названия')}</b>\n\n"
        
        if product.get('price'):
            original_price = product['price']
            # Конвертируем цену в рубли (для FruitsFamily обычно KRW)
            rubles = converter.convert_to_rubles(original_price, default_currency='KRW')
            if rubles:
                message += f"Цена: {original_price} (~{rubles})\n"
            else:
                message += f"Цена: {original_price}\n"
        
        if product.get('description'):
            message += f"{product['description'][:200]}...\n"
        
        if product.get('link'):
            message += f"\n<a href='{product['link']}'>Ссылка на товар</a>"
        
        return message