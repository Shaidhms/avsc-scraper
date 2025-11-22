"""
Example usage of Avantor Sciences Scraper
"""

from avantorsciences_scraper import AvantorScraper
import json

def scrape_single_product():
    """Example: Scrape a single product"""
    scraper = None
    try:
        # Initialize scraper (set headless=True to run without browser window)
        scraper = AvantorScraper(headless=False)
        
        # Scrape product
        product_code = "76181-190"
        # You can use country names like: "Austria", "Belgium", "Denmark", "USA", "United States", "Canada", "Germany", etc.
        country_name = "USA"  # Optional - can be None (defaults to USA)
        
        print(f"Scraping product: {product_code}")
        product_data = scraper.scrape_product(product_code, country_name)
        
        if product_data:
            print("\n" + "="*60)
            print("EXTRACTED PRODUCT DATA")
            print("="*60)
            print(json.dumps(product_data, indent=2))
            print("="*60)
            
            # Save to JSON file
            json_file = f"product_{product_code}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(product_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ JSON data saved to {json_file}")
            
            # Save to CSV file
            csv_file = scraper.save_to_csv(product_data, f"product_{product_code}.csv")
            if csv_file:
                print(f"✓ CSV data saved to {csv_file}")
        else:
            print("✗ Failed to extract product data")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if scraper:
            scraper.close()


def scrape_multiple_products():
    """Example: Scrape multiple products"""
    scraper = None
    try:
        scraper = AvantorScraper(headless=False)
        
        product_codes = ["76181-190", "76182-191"]  # Add more product codes here
        # Available countries: Austria, Belgium, Denmark, Finland, France, Germany, 
        # Italy, Netherlands, Spain, United Kingdom, Canada, Mexico, USA, etc.
        country_name = "USA"
        
        all_results = []
        
        for product_code in product_codes:
            print(f"\n{'='*60}")
            print(f"Scraping product: {product_code}")
            print('='*60)
            
            product_data = scraper.scrape_product(product_code, country_name)
            
            if product_data:
                all_results.append(product_data)
                print(f"✓ Successfully scraped {product_code}")
            else:
                print(f"✗ Failed to scrape {product_code}")
            
            # Wait between requests to be respectful
            import time
            time.sleep(3)
        
        # Save all results
        if all_results:
            # Save to JSON
            json_file = "all_products.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ All JSON data saved to {json_file}")
            
            # Save to CSV
            csv_file = scraper.save_to_csv(all_results, "all_products.csv")
            if csv_file:
                print(f"✓ All CSV data saved to {csv_file}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    # Choose which example to run
    print("Avantor Sciences Scraper - Example Usage")
    print("="*60)
    
    # Run single product example
    scrape_single_product()
    
    # Uncomment to run multiple products example
    # scrape_multiple_products()

