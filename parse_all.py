"""
Единый скрипт для парсинга товаров с обоих сайтов:
- globalbunjang.com
- fruitsfamily.com
"""
from parser import BunjangParser, FruitsFamilyParser
import json
import time

def parse_all_sites():
    """Парсинг товаров со всех сайтов"""
    all_products = {}
    
    print("="*60)
    print("ПАРСИНГ ТОВАРОВ СО ВСЕХ САЙТОВ")
    print("="*60)
    print()
    
    # 1. Парсинг Bunjang Global
    print("[1/2] Парсинг globalbunjang.com...")
    print("-" * 60)
    
    bunjang_parser = BunjangParser(
        base_url='https://globalbunjang.com/',
        use_selenium=True,
        brands_filter=[
            {'name': 'maison margiela', 'category': None}
        ]
    )
    
    try:
        # Парсим по ссылке для maison margiela
        search_url = "https://globalbunjang.com/search?categoryId=405&q=maison%20margiela&soldout=exclude"
        bunjang_products = bunjang_parser.parse_products_from_search(search_url, limit=50)
        all_products['bunjang'] = bunjang_products
        print(f"[OK] Найдено {len(bunjang_products)} товаров на Bunjang")
    except Exception as e:
        print(f"[ERROR] Ошибка при парсинге Bunjang: {e}")
        all_products['bunjang'] = []
    finally:
        bunjang_parser.close()
    
    print()
    time.sleep(2)  # Небольшая пауза между парсингами
    
    # 2. Парсинг FruitsFamily
    print("[2/2] Парсинг fruitsfamily.com...")
    print("-" * 60)
    
    fruits_parser = FruitsFamilyParser(
        base_url='https://fruitsfamily.com/',
        use_selenium=True,
        brands_filter=None  # Можно указать фильтр, например: [{'name': 'maison margiela', 'category': None}]
    )
    
    try:
        fruits_products = fruits_parser.parse_products(limit=50)
        all_products['fruitsfamily'] = fruits_products
        print(f"[OK] Найдено {len(fruits_products)} товаров на FruitsFamily")
    except Exception as e:
        print(f"[ERROR] Ошибка при парсинге FruitsFamily: {e}")
        all_products['fruitsfamily'] = []
    finally:
        fruits_parser.close()
    
    print()
    print("="*60)
    print("РЕЗУЛЬТАТЫ ПАРСИНГА")
    print("="*60)
    
    # Выводим статистику
    total_bunjang = len(all_products.get('bunjang', []))
    total_fruits = len(all_products.get('fruitsfamily', []))
    total_all = total_bunjang + total_fruits
    
    print(f"Bunjang Global: {total_bunjang} товаров")
    print(f"FruitsFamily: {total_fruits} товаров")
    print(f"Всего: {total_all} товаров")
    print()
    
    # Выводим товары
    if total_bunjang > 0:
        print(f"\n{'='*60}")
        print(f"ТОВАРЫ С BUNJANG GLOBAL ({total_bunjang}):")
        print(f"{'='*60}\n")
        for i, product in enumerate(all_products['bunjang'][:10], 1):  # Показываем первые 10
            title = product.get('title', 'Без названия')
            try:
                print(f"{i}. {title}")
            except UnicodeEncodeError:
                print(f"{i}. {title.encode('ascii', 'ignore').decode('ascii')}")
            
            if product.get('price'):
                try:
                    print(f"   Цена: {product['price']}")
                except UnicodeEncodeError:
                    print(f"   Цена: {product['price'].encode('ascii', 'ignore').decode('ascii')}")
            
            if product.get('link'):
                print(f"   Ссылка: {product['link']}")
            print()
    
    if total_fruits > 0:
        print(f"\n{'='*60}")
        print(f"ТОВАРЫ С FRUITSFAMILY ({total_fruits}):")
        print(f"{'='*60}\n")
        for i, product in enumerate(all_products['fruitsfamily'][:10], 1):  # Показываем первые 10
            title = product.get('title', 'Без названия')
            try:
                print(f"{i}. {title}")
            except UnicodeEncodeError:
                print(f"{i}. {title.encode('ascii', 'ignore').decode('ascii')}")
            
            if product.get('price'):
                try:
                    print(f"   Цена: {product['price']}")
                except UnicodeEncodeError:
                    print(f"   Цена: {product['price'].encode('ascii', 'ignore').decode('ascii')}")
            
            if product.get('link'):
                print(f"   Ссылка: {product['link']}")
            print()
    
    # Сохраняем результаты в JSON файлы
    if total_bunjang > 0:
        bunjang_file = 'bunjang_products.json'
        with open(bunjang_file, 'w', encoding='utf-8') as f:
            json.dump(all_products['bunjang'], f, ensure_ascii=False, indent=2)
        print(f"[OK] Результаты Bunjang сохранены в: {bunjang_file}")
    
    if total_fruits > 0:
        fruits_file = 'fruitsfamily_products.json'
        with open(fruits_file, 'w', encoding='utf-8') as f:
            json.dump(all_products['fruitsfamily'], f, ensure_ascii=False, indent=2)
        print(f"[OK] Результаты FruitsFamily сохранены в: {fruits_file}")
    
    # Сохраняем объединенный файл
    if total_all > 0:
        all_file = 'all_products.json'
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"[OK] Все результаты сохранены в: {all_file}")
    
    print()
    print("="*60)
    print("ПАРСИНГ ЗАВЕРШЕН")
    print("="*60)

if __name__ == '__main__':
    parse_all_sites()

