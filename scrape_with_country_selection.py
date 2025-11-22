"""
Interactive scraper with country selection
Shows list of countries, lets user select, then scrapes products from CSV
"""

from avantorsciences_scraper import AvantorScraper
import json
import os
import csv
import time

def load_countries():
    """Load countries from JSON file"""
    try:
        # Try to load from flat list first
        if os.path.exists('countries_flat_list.json'):
            with open('countries_flat_list.json', 'r', encoding='utf-8') as f:
                countries = json.load(f)
                return countries
        
        # Fallback to nested structure
        if os.path.exists('countries_and_urls.json'):
            with open('countries_and_urls.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Flatten the nested structure
                countries = []
                for region, country_list in data.items():
                    if isinstance(country_list, list):
                        for country in country_list:
                            countries.append({
                                'region': region,
                                'country': country.get('country', ''),
                                'url': country.get('url', '')
                            })
                return countries
    except Exception as e:
        print(f"Error loading countries: {e}")
        return None

def display_countries(countries):
    """Display countries organized by region"""
    if not countries:
        print("No countries found. Please run extract_countries.py first.")
        return
    
    # Organize by region
    regions = {}
    for country in countries:
        region = country.get('region', 'Unknown')
        if region not in regions:
            regions[region] = []
        regions[region].append(country)
    
    # Display countries by region
    print("\n" + "="*60)
    print("AVAILABLE COUNTRIES")
    print("="*60)
    
    all_countries_flat = []
    index = 1
    
    for region in sorted(regions.keys()):
        print(f"\n{region}:")
        print("-" * 60)
        region_countries = sorted(regions[region], key=lambda x: x.get('country', ''))
        for country in region_countries:
            country_name = country.get('country', 'N/A')
            print(f"  {index:3d}. {country_name}")
            country['selection_index'] = index
            all_countries_flat.append(country)
            index += 1
    
    print("\n" + "="*60)
    return all_countries_flat

def get_country_selection(countries):
    """Get country selection from user"""
    if not countries:
        return None
    
    # Get the flat list with indices
    all_countries = display_countries(countries)
    
    if not all_countries:
        return None
    
    max_index = len(all_countries)
    
    while True:
        try:
            print(f"\nPlease select a country (1-{max_index}) or 'q' to quit:")
            selection = input("Enter country number: ").strip().lower()
            
            if selection == 'q':
                print("Exiting...")
                return None
            
            selection_num = int(selection)
            
            if 1 <= selection_num <= max_index:
                selected = all_countries[selection_num - 1]
                print(f"\n✓ Selected: {selected.get('country')} ({selected.get('region')})")
                print(f"  URL: {selected.get('url')}")
                return selected
            else:
                print(f"Please enter a number between 1 and {max_index}")
        
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return None

def load_product_codes_from_csv(csv_file):
    """Load product codes from CSV file"""
    product_codes = []
    
    if not os.path.exists(csv_file):
        print(f"\n✗ CSV file not found: {csv_file}")
        return product_codes
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Look for common column names that might contain product codes
            possible_columns = ['product_code', 'product code', 'Product Code', 'code', 'Code', 
                              'catalog_number', 'catalog number', 'Catalog Number', 'SKU', 'sku']
            
            # Get first row to identify column
            first_row = next(reader, None)
            if not first_row:
                print(f"✗ CSV file is empty: {csv_file}")
                return product_codes
            
            # Find the product code column
            product_code_column = None
            for col in possible_columns:
                if col in first_row:
                    product_code_column = col
                    break
            
            if not product_code_column:
                # Try to use first column
                product_code_column = list(first_row.keys())[0]
                print(f"⚠ No standard product code column found. Using first column: {product_code_column}")
            
            # Add first row's product code
            if first_row.get(product_code_column):
                product_codes.append(first_row[product_code_column].strip())
            
            # Read remaining rows
            for row in reader:
                code = row.get(product_code_column, '').strip()
                if code:
                    product_codes.append(code)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_codes = []
        for code in product_codes:
            if code and code not in seen:
                seen.add(code)
                unique_codes.append(code)
        
        print(f"✓ Loaded {len(unique_codes)} product code(s) from {csv_file}")
        return unique_codes
    
    except Exception as e:
        print(f"✗ Error reading CSV file: {e}")
        return product_codes

def scrape_products_from_csv():
    """Scrape multiple products from CSV file"""
    scraper = None
    
    try:
        print("="*60)
        print("Avantor Sciences Batch Product Scraper")
        print("="*60)
        
        # Load countries
        print("\nLoading countries...")
        countries = load_countries()
        
        if not countries:
            print("\n✗ Could not load countries.")
            print("Please run 'python extract_countries.py' first to extract country list.")
            return
        
        # Get country selection
        selected_country = get_country_selection(countries)
        
        if not selected_country:
            return
        
        country_url = selected_country.get('url')
        country_name = selected_country.get('country')
        
        # Get CSV file path
        print("\n" + "-"*60)
        csv_file = input("Enter path to CSV file with product codes (e.g., products.csv): ").strip()
        
        if not csv_file:
            print("CSV file path cannot be empty!")
            return
        
        # Load product codes from CSV
        print(f"\nLoading product codes from {csv_file}...")
        product_codes = load_product_codes_from_csv(csv_file)
        
        if not product_codes:
            print("No product codes found in CSV file!")
            return
        
        print(f"\nFound {len(product_codes)} product code(s) to scrape:")
        for i, code in enumerate(product_codes[:10], 1):  # Show first 10
            print(f"  {i}. {code}")
        if len(product_codes) > 10:
            print(f"  ... and {len(product_codes) - 10} more")
        
        confirm = input(f"\nProceed with scraping {len(product_codes)} product(s)? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Scraping cancelled.")
            return
        
        print(f"\n{'='*60}")
        print(f"Country: {country_name}")
        print(f"Total Products: {len(product_codes)}")
        print(f"{'='*60}\n")
        
        # Initialize scraper
        scraper = AvantorScraper(headless=False)
        
        # Scrape all products
        all_results = []
        successful = 0
        failed = 0
        
        for index, product_code in enumerate(product_codes, 1):
            try:
                print(f"\n[{index}/{len(product_codes)}] Scraping product: {product_code}")
                print("-" * 60)
                
                # Scrape product using country URL
                product_data = scraper.scrape_product(
                    product_code, 
                    country_name=country_name, 
                    country_url=country_url
                )
                
                if product_data:
                    all_results.append(product_data)
                    successful += 1
                    print(f"✓ Successfully scraped {product_code}")
                else:
                    failed += 1
                    print(f"✗ Failed to scrape {product_code}")
                    # Add empty entry for tracking
                    all_results.append({
                        'product_code': product_code,
                        'product_name': None,
                        'error': 'Failed to extract product data'
                    })
                
                # Wait between requests to be respectful (except for last item)
                if index < len(product_codes):
                    wait_time = 3
                    print(f"Waiting {wait_time} seconds before next product...")
                    time.sleep(wait_time)
            
            except KeyboardInterrupt:
                print(f"\n\nScraping interrupted by user at product {index}/{len(product_codes)}")
                break
            except Exception as e:
                failed += 1
                print(f"✗ Error scraping {product_code}: {e}")
                all_results.append({
                    'product_code': product_code,
                    'product_name': None,
                    'error': str(e)
                })
                continue
        
        # Save all results
        if all_results:
            print(f"\n{'='*60}")
            print("SAVING RESULTS")
            print("="*60)
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Total: {len(all_results)}")
            
            # Generate output filename
            timestamp = int(time.time())
            output_csv = f"batch_products_{country_name.replace(' ', '_')}_{timestamp}.csv"
            output_json = f"batch_products_{country_name.replace(' ', '_')}_{timestamp}.json"
            
            # Save to CSV
            csv_file_path = scraper.save_to_csv(all_results, output_csv)
            if csv_file_path:
                print(f"\n✓ All products saved to CSV: {csv_file_path}")
            
            # Save to JSON
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"✓ All products saved to JSON: {output_json}")
            
            print(f"\n{'='*60}")
            print("SCRAPING COMPLETE")
            print("="*60)
        else:
            print("\n✗ No products were successfully scraped")
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()

def scrape_product_interactive():
    """Interactive scraping with country selection (single product)"""
    scraper = None
    
    try:
        print("="*60)
        print("Avantor Sciences Product Scraper")
        print("="*60)
        
        # Load countries
        print("\nLoading countries...")
        countries = load_countries()
        
        if not countries:
            print("\n✗ Could not load countries.")
            print("Please run 'python extract_countries.py' first to extract country list.")
            return
        
        # Get country selection
        selected_country = get_country_selection(countries)
        
        if not selected_country:
            return
        
        country_url = selected_country.get('url')
        country_name = selected_country.get('country')
        
        # Get product code
        print("\n" + "-"*60)
        product_code = input("Enter product code (e.g., 76181-190): ").strip()
        
        if not product_code:
            print("Product code cannot be empty!")
            return
        
        print(f"\n{'='*60}")
        print(f"Scraping Product: {product_code}")
        print(f"Country: {country_name}")
        print(f"{'='*60}\n")
        
        # Initialize scraper
        scraper = AvantorScraper(headless=False)
        
        # Scrape product using country URL
        product_data = scraper.scrape_product(product_code, country_name=country_name, country_url=country_url)
        
        if product_data:
            print("\n" + "="*60)
            print("EXTRACTED PRODUCT DATA")
            print("="*60)
            print(json.dumps(product_data, indent=2, ensure_ascii=False))
            print("="*60)
            
            # Save to JSON
            json_file = f"product_{product_code}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(product_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ JSON data saved to {json_file}")
            
            # Save to CSV
            csv_file = scraper.save_to_csv(product_data, f"product_{product_code}.csv")
            if csv_file:
                print(f"✓ CSV data saved to {csv_file}")
        else:
            print("\n✗ Failed to extract product data")
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    import sys
    
    # Check if user wants batch scraping or single product
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        scrape_products_from_csv()
    else:
        print("Choose mode:")
        print("  1. Single product scraping")
        print("  2. Batch scraping from CSV")
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "2":
            scrape_products_from_csv()
        else:
            scrape_product_interactive()

