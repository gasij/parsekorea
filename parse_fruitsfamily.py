"""
Скрипт для парсинга товаров с сайта fruitsfamily.com
"""
from parser import FruitsFamilyParser
import json

def parse_fruitsfamily():
    """Парсинг товаров с fruitsfamily.com"""
    base_url = "https://fruitsfamily.com/"
    
    print(f"Парсинг товаров с fruitsfamily.com...")
    print(f"URL: {base_url}\n")
    
    # Создаем парсер
    parser = FruitsFamilyParser(
        base_url=base_url,
        use_selenium=True,  # Используем Selenium для динамического контента
        brands_filter=None  # Можно указать фильтр по брендам, например: [{'name': 'maison margiela', 'category': None}]
    )
    
    try:
        # Парсим товары с главной страницы
        products = parser.parse_products(limit=50)
        
        if products:
            print(f"\n{'='*60}")
            print(f"Найдено {len(products)} товаров:\n")
            print(f"{'='*60}\n")
            
            for i, product in enumerate(products, 1):
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
                if product.get('image'):
                    print(f"   Изображение: {product['image']}")
                if product.get('description'):
                    try:
                        print(f"   Описание: {product['description'][:100]}...")
                    except UnicodeEncodeError:
                        desc = product['description'][:100]
                        print(f"   Описание: {desc.encode('ascii', 'ignore').decode('ascii')}...")
                print()
            
            # Сохраняем результаты в JSON файл
            output_file = 'fruitsfamily_products.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Результаты сохранены в файл: {output_file}")
            
        else:
            print("[ERROR] Товары не найдены.")
            print("Возможно, страница использует динамическую загрузку контента.")
            print("Попробуйте проверить, работает ли Selenium.")
    
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        parser.close()

if __name__ == '__main__':
    parse_fruitsfamily()

