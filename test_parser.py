"""
Тестовый скрипт для проверки парсера
"""
from parser import BunjangParser
import config

def test_parser():
    print("Тестирование парсера globalbunjang.com...")
    
    # Создаем парсер с фильтром брендов из config
    parser = BunjangParser(
        use_selenium=False,
        brands_filter=config.BRANDS_TO_PARSE
    )
    
    try:
        # Парсим товары
        products = parser.parse_trending_products(limit=5)
        
        if products:
            print(f"\nНайдено {len(products)} товаров:\n")
            for i, product in enumerate(products, 1):
                print(f"{i}. {product.get('title', 'Без названия')}")
                if product.get('price'):
                    print(f"   Цена: {product['price']}")
                if product.get('link'):
                    print(f"   Ссылка: {product['link']}")
                print()
        else:
            print("Товары не найдены. Возможно, нужно использовать Selenium.")
            print("Попробуйте запустить с use_selenium=True")
    
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        parser.close()

if __name__ == '__main__':
    test_parser()

