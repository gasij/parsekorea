"""
Скрипт для парсинга товаров Maison Margiela по указанной ссылке
"""
from parser import BunjangParser
import json

def parse_maison_margiela():
    """Парсинг товаров Maison Margiela с указанной страницы"""
    search_url = "https://globalbunjang.com/search?categoryId=405&q=maison%20margiela&soldout=exclude"
    
    print(f"Парсинг товаров Maison Margiela...")
    print(f"URL: {search_url}\n")
    
    # Создаем парсер
    parser = BunjangParser(
        base_url='https://globalbunjang.com/',
        use_selenium=True,  # Используем Selenium для динамического контента
        brands_filter=[{'name': 'maison margiela', 'category': None}]  # Фильтр по бренду
    )
    
    try:
        # Парсим товары из результатов поиска
        products = parser.parse_products_from_search(search_url, limit=50)
        
        if products:
            print(f"\n{'='*60}")
            print(f"Найдено {len(products)} товаров:\n")
            print(f"{'='*60}\n")
            
            for i, product in enumerate(products, 1):
                print(f"{i}. {product.get('title', 'Без названия')}")
                if product.get('price'):
                    print(f"   Цена: {product['price']}")
                if product.get('link'):
                    print(f"   Ссылка: {product['link']}")
                if product.get('image'):
                    print(f"   Изображение: {product['image']}")
                if product.get('description'):
                    print(f"   Описание: {product['description'][:100]}...")
                print()
            
            # Сохраняем результаты в JSON файл
            output_file = 'maison_margiela_products.json'
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
    parse_maison_margiela()

