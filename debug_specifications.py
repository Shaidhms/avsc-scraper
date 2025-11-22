"""
Debug script to find where specifications are located on the product page
"""

from avantorsciences_scraper import AvantorScraper
import time
import json

def debug_specifications():
    """Debug script to find specifications on product page"""
    scraper = None
    try:
        print("="*60)
        print("Specification Debugging Tool")
        print("="*60)
        
        # Initialize scraper
        scraper = AvantorScraper(headless=False)
        
        # Navigate to product
        product_code = "76181-190"
        country_name = "USA"
        
        print(f"\nNavigating to product: {product_code}")
        scraper.driver.get(scraper.base_url)
        time.sleep(5)
        
        # Handle country popup
        scraper.handle_country_popup(country_name)
        time.sleep(3)
        
        # Search for product
        print(f"Searching for product...")
        scraper.search_product(product_code)
        time.sleep(5)
        
        # Expand sections
        scraper._expand_specification_sections()
        time.sleep(3)
        
        print("\nAnalyzing page structure...")
        print("="*60)
        
        # 1. Find all tables
        print("\n1. TABLES FOUND:")
        print("-" * 60)
        tables = scraper.driver.find_elements(By.XPATH, "//table")
        print(f"Total tables: {len(tables)}")
        for i, table in enumerate(tables):
            try:
                rows = table.find_elements(By.XPATH, ".//tr")
                print(f"\nTable {i+1}: {len(rows)} rows")
                # Show first few rows
                for j, row in enumerate(rows[:5]):
                    cells = row.find_elements(By.XPATH, ".//td | .//th")
                    row_text = [cell.text.strip() for cell in cells]
                    print(f"  Row {j+1}: {row_text}")
            except Exception as e:
                print(f"  Error reading table {i+1}: {e}")
        
        # 2. Find all definition lists
        print("\n\n2. DEFINITION LISTS FOUND:")
        print("-" * 60)
        dls = scraper.driver.find_elements(By.XPATH, "//dl")
        print(f"Total definition lists: {len(dls)}")
        for i, dl in enumerate(dls):
            try:
                dts = dl.find_elements(By.XPATH, ".//dt")
                dds = dl.find_elements(By.XPATH, ".//dd")
                print(f"\nDL {i+1}: {len(dts)} terms")
                for j in range(min(5, len(dts), len(dds))):
                    print(f"  {dts[j].text.strip()}: {dds[j].text.strip()}")
            except Exception as e:
                print(f"  Error reading DL {i+1}: {e}")
        
        # 3. Find elements with "spec" in class/id
        print("\n\n3. ELEMENTS WITH 'SPEC' IN CLASS/ID:")
        print("-" * 60)
        spec_elements = scraper.driver.find_elements(By.XPATH,
            "//*[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')] | " +
            "//*[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'spec')]"
        )
        print(f"Total spec-related elements: {len(spec_elements)}")
        for i, elem in enumerate(spec_elements[:10]):  # Show first 10
            try:
                tag = elem.tag_name
                classes = elem.get_attribute('class') or ''
                elem_id = elem.get_attribute('id') or ''
                text = elem.text.strip()[:100]  # First 100 chars
                print(f"\nElement {i+1}: <{tag}> class='{classes}' id='{elem_id}'")
                print(f"  Text: {text}")
            except Exception as e:
                print(f"  Error reading element {i+1}: {e}")
        
        # 4. Find elements with "specification" or "property" text
        print("\n\n4. ELEMENTS CONTAINING 'SPECIFICATION' OR 'PROPERTY' TEXT:")
        print("-" * 60)
        text_elements = scraper.driver.find_elements(By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specification')] | " +
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'property')] | " +
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specs')]"
        )
        print(f"Total elements with spec-related text: {len(text_elements)}")
        for i, elem in enumerate(text_elements[:10]):
            try:
                print(f"\nElement {i+1}: <{elem.tag_name}> {elem.text.strip()[:200]}")
                # Show parent structure
                parent = elem.find_element(By.XPATH, "./parent::*")
                print(f"  Parent: <{parent.tag_name}> class='{parent.get_attribute('class') or ''}'")
            except Exception as e:
                print(f"  Error reading element {i+1}: {e}")
        
        # 5. Find all divs with product-related classes
        print("\n\n5. PRODUCT-RELATED DIVS:")
        print("-" * 60)
        product_divs = scraper.driver.find_elements(By.XPATH,
            "//div[contains(@class, 'product')] | " +
            "//div[contains(@class, 'details')] | " +
            "//div[contains(@class, 'info')] | " +
            "//div[contains(@class, 'content')]"
        )
        print(f"Total product-related divs: {len(product_divs)}")
        for i, div in enumerate(product_divs[:5]):
            try:
                classes = div.get_attribute('class') or ''
                div_id = div.get_attribute('id') or ''
                text = div.text.strip()[:200]
                print(f"\nDiv {i+1}: class='{classes}' id='{div_id}'")
                print(f"  Text preview: {text}")
            except Exception as e:
                print(f"  Error reading div {i+1}: {e}")
        
        # 6. Save page source
        print("\n\n6. SAVING PAGE FOR INSPECTION:")
        print("-" * 60)
        scraper._save_page_for_debugging()
        print("Page HTML and screenshot saved for manual inspection")
        
        print("\n" + "="*60)
        print("Debugging complete!")
        print("="*60)
        print("\nCheck the saved files:")
        print("  - debug_page_source.html")
        print("  - debug_page_screenshot.png")
        print("  - debug_product_section.html")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            input("\nPress Enter to close the browser...")
            scraper.close()

if __name__ == "__main__":
    from selenium.webdriver.common.by import By
    debug_specifications()

