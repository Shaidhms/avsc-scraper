# Avantor Sciences Web Scraper

A Python-based web scraper for extracting product information from [Avantor Sciences](https://www.avantorsciences.com/).

## Features

- **Extract Countries & URLs**: Scrape all available countries and their respective URLs from the popup
- Handles country selection popup automatically - clicks on country links (Austria, Belgium, Denmark, USA, Canada, etc.)
- Searches for products by product code
- Extracts comprehensive product data including:
  - Product name and code
  - Model number
  - Description
  - Price and currency
  - Specifications
  - Availability status

## Available Countries

The scraper supports all countries available on Avantor Sciences, including:

**Europe**: Austria, Belgium, Czech Republic, Denmark, Finland, France, Germany, Hungary, Ireland, Italy, Netherlands, Norway, Poland, Portugal, Slovakia, Slovenia, Spain, Sweden, Switzerland, United Kingdom

**North America**: Canada, Mexico, Puerto Rico, USA

**Asia/Pacific**: China Mainland, India, Japan, Singapore, South Korea

## Requirements

- Python 3.7+
- Chrome browser installed
- ChromeDriver (can be automatically managed with webdriver-manager)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install ChromeDriver (if not using webdriver-manager):
   - Download from: https://chromedriver.chromium.org/
   - Or install via package manager:
     - macOS: `brew install chromedriver`
     - Linux: `sudo apt-get install chromium-chromedriver`
     - Windows: Download and add to PATH

## Usage

### Basic Usage

```python
from avantorsciences_scraper import AvantorScraper

# Initialize scraper
scraper = AvantorScraper(headless=False)

# Scrape a product
product_data = scraper.scrape_product(
    product_code="76181-190",
    country_name="USA"  # Optional: "Austria", "Belgium", "Denmark", "USA", "Canada", etc.
)

# Print results
print(product_data)

# Close browser
scraper.close()
```

### Command Line Usage

**Extract Countries and URLs:**
```bash
python extract_countries.py
```
or
```bash
python avantorsciences_scraper.py --countries
```

This will:
1. Navigate to Avantor Sciences website
2. Extract all countries and their URLs from the popup
3. Save results to `countries_and_urls.json` and `countries_flat_list.json`

**Scrape Product:**
```bash
python avantorsciences_scraper.py
```

This will:
1. Navigate to Avantor Sciences website
2. Handle the country popup
3. Search for product "76181-190"
4. Extract all available product data
5. Save results to `product_76181-190.json`

### Extract Countries and URLs

```python
from avantorsciences_scraper import AvantorScraper
import json

scraper = AvantorScraper(headless=False)
scraper.driver.get(scraper.base_url)
time.sleep(5)

# Extract all countries and their URLs
countries_data = scraper.extract_countries_and_urls()

# Print results
print(json.dumps(countries_data, indent=2))

# Save to file
with open('countries.json', 'w') as f:
    json.dump(countries_data, f, indent=2)

scraper.close()
```

### Customizing the Scraper

```python
# Run in headless mode (no browser window)
scraper = AvantorScraper(headless=True)

# Scrape multiple products
products = ["76181-190", "76182-191", "76183-192"]
for product_code in products:
    data = scraper.scrape_product(product_code, country_name="USA")
    # Process data...
```

## Output Formats

### Countries and URLs Output

The `extract_countries_and_urls()` method returns a dictionary organized by region:

```json
{
  "Europe": [
    {"country": "Austria", "url": "https://www.avantorsciences.com/at/"},
    {"country": "Belgium", "url": "https://www.avantorsciences.com/be/"},
    ...
  ],
  "North America": [
    {"country": "USA", "url": "https://www.avantorsciences.com/us/"},
    {"country": "Canada", "url": "https://www.avantorsciences.com/ca/"},
    ...
  ],
  "Asia/Pacific": [...]
}
```

### Product Data Output

The scraper returns a dictionary with the following structure:

```json
{
  "product_code": "76181-190",
  "product_name": "Product Name",
  "model_number": "Model-123",
  "description": "Product description...",
  "price": "123.45",
  "currency": "USD",
  "specifications": {
    "Property 1": "Value 1",
    "Property 2": "Value 2"
  },
  "availability": "In Stock",
  "url": "https://www.avantorsciences.com/..."
}
```

## Configuration

You can modify the scraper behavior by editing `avantorsciences_scraper.py`:

- **Timeout values**: Adjust wait times in `WebDriverWait` calls
- **Selectors**: Modify XPath selectors if website structure changes
- **User agent**: Change the user agent string in `setup_driver()`

## Troubleshooting

### ChromeDriver Issues

If you encounter ChromeDriver errors:

1. Ensure Chrome browser is up to date
2. Install matching ChromeDriver version:
   ```bash
   pip install webdriver-manager
   ```
   Then modify the script to use webdriver-manager (see commented code in script)

### Popup Not Found

If the country popup isn't being detected:
- The popup might have been dismissed previously (cookies)
- Try clearing browser cookies or using incognito mode
- Adjust the popup selectors in `handle_country_popup()`

### Product Not Found

If product search fails:
- Verify the product code is correct
- Check if the product is available in the selected country
- Inspect the page to find correct search input selectors

## Legal Considerations

⚠️ **Important**: Before scraping, please:
- Review Avantor Sciences [Terms of Use](https://www.avantorsciences.com/terms-of-use)
- Review their [Privacy Policy](https://www.avantorsciences.com/privacy-policy)
- Respect robots.txt and rate limits
- Consider contacting Avantor for official APIs or data access

## License

This scraper is provided as-is for educational and research purposes.

