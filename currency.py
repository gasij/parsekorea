"""
Модуль для конвертации валют в рубли
"""
import requests
import re
from typing import Optional, Dict
import time

class CurrencyConverter:
    """Конвертер валют в рубли"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = 3600  # Кэш на 1 час
        self.last_update = 0
        
        # Фиксированные курсы (резервный вариант)
        self.fallback_rates = {
            'KRW': 0.075,  # 1 KRW = 0.075 RUB (примерно)
            'USD': 80.0,   # 1 USD = 90 RUB (примерно)
            'EUR': 98.0,   # 1 EUR = 98 RUB (примерно)
            'JPY': 0.7,    # 1 JPY = 0.6 RUB (примерно)
        }
    
    def get_exchange_rates(self) -> Dict[str, float]:
        """Получить актуальные курсы валют"""
        current_time = time.time()
        
        # Проверяем кэш
        if current_time - self.last_update < self.cache_time and self.cache:
            return self.cache
        
        try:
            # Используем бесплатный API exchangerate-api.com
            # Получаем курсы относительно USD, затем конвертируем в RUB
            response = requests.get(
                'https://api.exchangerate-api.com/v4/latest/USD',
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                rates = data.get('rates', {})
                
                # Получаем курс USD к RUB
                usd_to_rub = rates.get('RUB', 90.0)  # Резервный курс
                
                # Конвертируем все валюты в рубли
                converted_rates = {}
                
                # USD к RUB
                converted_rates['USD'] = usd_to_rub
                
                # Другие валюты через USD
                for currency, usd_rate in rates.items():
                    if currency != 'USD' and currency != 'RUB' and usd_rate > 0:
                        # currency -> USD -> RUB
                        converted_rates[currency] = usd_to_rub / usd_rate
                
                # Добавляем основные валюты явно
                if 'KRW' in rates:
                    converted_rates['KRW'] = usd_to_rub / rates['KRW']
                if 'EUR' in rates:
                    converted_rates['EUR'] = usd_to_rub / rates['EUR']
                if 'JPY' in rates:
                    converted_rates['JPY'] = usd_to_rub / rates['JPY']
                
                self.cache = converted_rates
                self.last_update = current_time
                return converted_rates
        except Exception as e:
            print(f"Ошибка при получении курсов валют: {e}, используем резервные курсы")
        
        # Используем резервные курсы
        return self.fallback_rates
    
    def extract_price(self, price_text: str) -> Optional[Dict]:
        """Извлечь цену и валюту из текста"""
        if not price_text:
            return None
        
        # Убираем пробелы и приводим к нижнему регистру для анализа
        text = price_text.replace(',', '').replace(' ', '')
        
        # Паттерны для поиска цен
        patterns = [
            # Корейские воны: 100000원, 100,000원, 100000 KRW
            (r'(\d+(?:\.\d+)?)\s*(?:원|KRW|won)', 'KRW'),
            # Доллары: $100, $100.50, 100 USD
            (r'[$\$]?\s*(\d+(?:\.\d+)?)\s*(?:USD|usd|\$)', 'USD'),
            # Евро: €100, 100 EUR
            (r'[€€]?\s*(\d+(?:\.\d+)?)\s*(?:EUR|eur|€)', 'EUR'),
            # Иены: ¥100, 100 JPY
            (r'[¥¥]?\s*(\d+(?:\.\d+)?)\s*(?:JPY|jpy|¥)', 'JPY'),
            # Просто числа (предполагаем KRW для корейских сайтов)
            (r'(\d+(?:\.\d+)?)', 'KRW'),
        ]
        
        for pattern, currency in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    return {'amount': amount, 'currency': currency}
                except ValueError:
                    continue
        
        return None
    
    def convert_to_rubles(self, price_text: str, default_currency: str = 'KRW') -> Optional[str]:
        """Конвертировать цену в рубли"""
        price_info = self.extract_price(price_text)
        
        if not price_info:
            # Пробуем извлечь число и использовать валюту по умолчанию
            numbers = re.findall(r'\d+(?:\.\d+)?', price_text.replace(',', ''))
            if numbers:
                try:
                    amount = float(numbers[0])
                    price_info = {'amount': amount, 'currency': default_currency}
                except ValueError:
                    return None
            else:
                return None
        
        amount = price_info['amount']
        currency = price_info['currency']
        
        # Получаем курс
        rates = self.get_exchange_rates()
        rate = rates.get(currency)
        
        if not rate:
            # Если валюта не найдена, используем резервный курс
            rate = self.fallback_rates.get(currency, 1.0)
        
        # Конвертируем в рубли
        rubles = amount * rate
        
        # Форматируем результат
        if rubles >= 1000:
            return f"{rubles:,.0f} RUB"
        else:
            return f"{rubles:,.2f} RUB"
    
    def format_price_with_conversion(self, original_price: str, default_currency: str = 'KRW') -> str:
        """Форматировать цену с конвертацией в рубли"""
        rubles = self.convert_to_rubles(original_price, default_currency)
        
        if rubles:
            return f"{original_price} (~{rubles})"
        else:
            return original_price

# Глобальный экземпляр конвертера
converter = CurrencyConverter()

