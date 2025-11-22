"""
Script to extract all countries and their URLs from Avantor Sciences country popup
"""

from avantorsciences_scraper import AvantorScraper
import json
import time

def extract_countries():
    """Extract all countries and URLs from the popup"""
    scraper = None
    try:
        print("="*60)
        print("Avantor Sciences - Country & URL Extractor")
        print("="*60)
        
        # Initialize scraper
        scraper = AvantorScraper(headless=False)
        
        # Navigate to website
        print(f"\nNavigating to {scraper.base_url}...")
        scraper.driver.get(scraper.base_url)
        time.sleep(5)
        
        # Extract countries and URLs
        print("\nExtracting countries and URLs from popup...")
        countries_data = scraper.extract_countries_and_urls()
        
        # Display results
        print("\n" + "="*60)
        print("EXTRACTED COUNTRIES AND URLs")
        print("="*60)
        
        total_countries = 0
        for region, countries in countries_data.items():
            if countries:
                print(f"\n{region} ({len(countries)} countries):")
                print("-" * 60)
                for country_info in countries:
                    print(f"  • {country_info['country']:30s} -> {country_info['url']}")
                    total_countries += 1
        
        print("\n" + "="*60)
        print(f"Total: {total_countries} countries extracted")
        print("="*60)
        
        # Save to JSON file
        output_file = "countries_and_urls.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(countries_data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Data saved to {output_file}")
        
        # Also save a flat list for easy reference
        flat_list = []
        for region, countries in countries_data.items():
            for country_info in countries:
                flat_list.append({
                    "region": region,
                    "country": country_info["country"],
                    "url": country_info["url"]
                })
        
        flat_output_file = "countries_flat_list.json"
        with open(flat_output_file, 'w', encoding='utf-8') as f:
            json.dump(flat_list, f, indent=2, ensure_ascii=False)
        print(f"✓ Flat list saved to {flat_output_file}")
        
        return countries_data
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if scraper:
            input("\nPress Enter to close the browser...")
            scraper.close()

if __name__ == "__main__":
    extract_countries()

