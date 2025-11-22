"""
Avantor Sciences Web Scraper
Handles country popup, product search, and data extraction
"""

import time
import json
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import logging
import re
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AvantorScraper:
    def __init__(self, headless=False):
        """
        Initialize the scraper with Chrome WebDriver
        
        Args:
            headless (bool): Run browser in headless mode
        """
        self.base_url = "https://www.avantorsciences.com/"
        self.driver = None
        self.setup_driver(headless)
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Use webdriver-manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            logger.info("Trying without webdriver-manager...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.maximize_window()
                logger.info("Chrome WebDriver initialized successfully")
            except Exception as e2:
                logger.error(f"Error initializing WebDriver: {e2}")
                raise
    
    def handle_cookie_banner(self):
        """Handle cookie consent banner if present"""
        try:
            logger.info("Checking for cookie banner...")
            wait = WebDriverWait(self.driver, 3)
            
            # Common cookie banner selectors
            cookie_selectors = [
                "//button[contains(text(), 'Accept All Cookies')]",
                "//button[contains(text(), 'Accept')]",
                "//button[contains(@class, 'cookie') and contains(text(), 'Accept')]",
                "//*[contains(text(), 'Accept All Cookies')]",
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    # Click using JavaScript to avoid interception
                    self.driver.execute_script("arguments[0].click();", cookie_button)
                    logger.info("Accepted cookie consent")
                    time.sleep(1)
                    return True
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.debug(f"Cookie banner handling: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"No cookie banner found or already dismissed: {e}")
        
        return False
    
    def extract_countries_and_urls(self):
        """
        Extract all countries and their URLs from the country selection popup
        
        Returns:
            dict: Dictionary with regions as keys and list of {country, url} dicts as values
                  Format: {
                      "Europe": [{"country": "Austria", "url": "https://..."}, ...],
                      "North America": [...],
                      "Asia/Pacific": [...]
                  }
        """
        countries_data = {
            "Europe": [],
            "North America": [],
            "Asia/Pacific": []
        }
        
        try:
            logger.info("Extracting countries and URLs from popup...")
            wait = WebDriverWait(self.driver, 20)
            
            # Handle cookie banner first
            self.handle_cookie_banner()
            
            # Wait for the country popup modal
            popup_selectors = [
                "//ngb-modal-window[contains(@class, 'modal')]",
                "//div[contains(@class, 'modal') and contains(@class, 'show')]",
                "//*[contains(text(), 'Select an Avantor Country')]",
            ]
            
            popup_found = False
            for selector in popup_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    popup_found = True
                    logger.info(f"Popup found using: {selector}")
                    time.sleep(2)
                    break
                except TimeoutException:
                    continue
            
            if not popup_found:
                logger.warning("Country popup not found")
                return countries_data
            
            # Find all country list containers
            # Based on HTML structure: ul.country-list-items contains li.list-item with a.link
            country_lists = self.driver.find_elements(By.XPATH, 
                "//ul[contains(@class, 'country-list-items')] | " +
                "//ul[contains(@class, 'list')] | " +
                "//div[contains(@class, 'country-selector-countries')]//ul"
            )
            
            if not country_lists:
                # Try alternative selectors
                country_lists = self.driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'col-md-4')]//ul | " +
                    "//div[contains(@class, 'country')]//ul"
                )
            
            logger.info(f"Found {len(country_lists)} country list(s)")
            
            # Extract countries from each list, grouped by region
            for list_elem in country_lists:
                try:
                    # Try to find the region heading (h5.country-name) before this list
                    region_heading = None
                    try:
                        # Look for h5 with class country-name that's a sibling or parent
                        region_heading = list_elem.find_element(By.XPATH, 
                            "./preceding-sibling::h5[contains(@class, 'country-name')] | " +
                            "../h5[contains(@class, 'country-name')] | " +
                            "./ancestor::div//h5[contains(@class, 'country-name')]"
                        )
                        region = region_heading.text.strip()
                    except:
                        # If no heading found, try to determine from parent structure
                        try:
                            parent = list_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'col')]")
                            # Check if there's a heading in the same column
                            region_elem = parent.find_element(By.XPATH, ".//h5 | .//h4 | .//h3")
                            region = region_elem.text.strip()
                        except:
                            region = "Unknown"
                    
                    logger.info(f"Processing region: {region}")
                    
                    # Find all country links in this list
                    country_links = list_elem.find_elements(By.XPATH, 
                        ".//li[contains(@class, 'list-item')]//a | " +
                        ".//li//a | " +
                        ".//a[contains(@class, 'link')] | " +
                        ".//a"
                    )
                    
                    logger.info(f"Found {len(country_links)} countries in {region}")
                    
                    for link in country_links:
                        try:
                            country_name = link.text.strip()
                            country_url = link.get_attribute('href')
                            
                            if country_name and country_url:
                                country_info = {
                                    "country": country_name,
                                    "url": country_url
                                }
                                
                                # Add to appropriate region
                                if "Europe" in region or region == "Europe":
                                    countries_data["Europe"].append(country_info)
                                elif "North America" in region or region == "North America":
                                    countries_data["North America"].append(country_info)
                                elif "Asia" in region or "Pacific" in region or region == "Asia/Pacific":
                                    countries_data["Asia/Pacific"].append(country_info)
                                else:
                                    # If region not recognized, add to a new key or default
                                    if region not in countries_data:
                                        countries_data[region] = []
                                    countries_data[region].append(country_info)
                                
                                logger.debug(f"  - {country_name}: {country_url}")
                        
                        except Exception as e:
                            logger.debug(f"Error extracting country from link: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error processing country list: {e}")
                    continue
            
            # Alternative method: Find all links directly in modal
            if sum(len(v) for v in countries_data.values()) == 0:
                logger.info("Trying alternative extraction method...")
                try:
                    # Find all links in the modal
                    all_links = self.driver.find_elements(By.XPATH,
                        "//ngb-modal-window//a[contains(@class, 'link')] | " +
                        "//div[contains(@class, 'modal')]//a | " +
                        "//ul[contains(@class, 'country')]//a | " +
                        "//li[contains(@class, 'list-item')]//a"
                    )
                    
                    logger.info(f"Found {len(all_links)} total links in modal")
                    
                    # Group by finding region headings
                    current_region = "Unknown"
                    for link in all_links:
                        try:
                            country_name = link.text.strip()
                            country_url = link.get_attribute('href')
                            
                            if not country_name or not country_url:
                                continue
                            
                            # Skip if it's not a country link (check URL pattern)
                            if 'avantorsciences.com' not in country_url:
                                continue
                            
                            # Try to determine region by looking at preceding headings
                            try:
                                # Find the closest h5 heading before this link
                                heading = link.find_element(By.XPATH, 
                                    "./ancestor::div//h5[contains(@class, 'country-name')] | " +
                                    "./preceding::h5[contains(@class, 'country-name')][1]"
                                )
                                current_region = heading.text.strip()
                            except:
                                pass
                            
                            country_info = {
                                "country": country_name,
                                "url": country_url
                            }
                            
                            # Add to appropriate region
                            if "Europe" in current_region:
                                countries_data["Europe"].append(country_info)
                            elif "North America" in current_region:
                                countries_data["North America"].append(country_info)
                            elif "Asia" in current_region or "Pacific" in current_region:
                                countries_data["Asia/Pacific"].append(country_info)
                            else:
                                if current_region not in countries_data:
                                    countries_data[current_region] = []
                                countries_data[current_region].append(country_info)
                            
                            logger.debug(f"  - {country_name}: {country_url}")
                        
                        except Exception as e:
                            logger.debug(f"Error processing link: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error in alternative extraction: {e}")
            
            total_countries = sum(len(v) for v in countries_data.values())
            logger.info(f"Successfully extracted {total_countries} countries")
            
        except Exception as e:
            logger.error(f"Error extracting countries: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return countries_data
    
    def handle_country_popup(self, country_name=None):
        """
        Handle the country selection popup
        
        Args:
            country_name (str): Name of the country to select (e.g., "Austria", "Belgium", "Denmark", 
                             "United States", "USA", "Canada", "Germany", etc.)
                             If None, will default to "USA"
        """
        try:
            logger.info("Waiting for country popup to appear...")
            wait = WebDriverWait(self.driver, 20)
            
            # Default to USA if no country specified
            if not country_name:
                country_name = "USA"
            
            # First, handle cookie banner if present
            self.handle_cookie_banner()
            
            # Wait for the country popup modal - look for "Select an Avantor Country" heading
            logger.info("Looking for 'Select an Avantor Country' popup...")
            popup_selectors = [
                "//*[contains(text(), 'Select an Avantor Country')]",
                "//h1[contains(text(), 'Select an Avantor Country')]",
                "//h2[contains(text(), 'Select an Avantor Country')]",
                "//div[contains(@class, 'modal')]//*[contains(text(), 'Select an Avantor Country')]",
                "//div[contains(@class, 'popup')]//*[contains(text(), 'Select an Avantor Country')]",
                "//div[contains(@class, 'country-selector')]",
                "//div[contains(@class, 'country') and contains(@class, 'modal')]",
            ]
            
            popup_found = False
            popup_element = None
            
            for selector in popup_selectors:
                try:
                    popup_element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    popup_found = True
                    logger.info(f"Country popup found using selector: {selector}")
                    time.sleep(2)  # Give popup time to fully load
                    break
                except TimeoutException:
                    continue
            
            if not popup_found:
                logger.warning("Could not find country popup - may already be dismissed or not present")
                # Take screenshot for debugging
                try:
                    self.driver.save_screenshot("popup_not_found.png")
                    logger.info("Screenshot saved as popup_not_found.png")
                except:
                    pass
                return
            
            # Scroll to top to ensure popup is visible
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Handle different country name variations
            country_variations = {
                "United States": ["USA", "United States", "US"],
                "USA": ["USA", "United States", "US"],
                "US": ["USA", "United States", "US"],
                "United Kingdom": ["United Kingdom", "UK"],
                "UK": ["United Kingdom", "UK"],
                "China Mainland": ["China Mainland", "China"],
            }
            
            # Get list of possible names to search for
            search_names = [country_name]
            if country_name in country_variations:
                search_names.extend(country_variations[country_name])
            
            logger.info(f"Attempting to click country: {search_names}")
            
            # Try to find and click the country - try multiple methods
            country_clicked = False
            
            for name_to_search in search_names:
                if country_clicked:
                    break
                
                # Try multiple selectors - countries are in list items (li) with links (a)
                country_selectors = [
                    # Look for links with exact text match
                    f"//a[normalize-space(text())='{name_to_search}']",
                    # Look for list items containing the country name with links inside
                    f"//li//a[normalize-space(text())='{name_to_search}']",
                    # Look for any clickable element with exact text
                    f"//*[normalize-space(text())='{name_to_search}' and (self::a or self::button or contains(@class, 'link') or contains(@onclick, 'country'))]",
                    # Look in modal/popup for links
                    f"//div[contains(@class, 'modal')]//a[normalize-space(text())='{name_to_search}']",
                    f"//div[contains(@class, 'popup')]//a[normalize-space(text())='{name_to_search}']",
                    # Contains text (partial match)
                    f"//a[contains(normalize-space(text()), '{name_to_search}')]",
                    f"//li//a[contains(normalize-space(text()), '{name_to_search}')]",
                    # Case-insensitive exact match
                    f"//a[translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{name_to_search.lower()}']",
                    f"//li//a[translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{name_to_search.lower()}']",
                ]
                
                for selector in country_selectors:
                    try:
                        # Find the element
                        country_elements = self.driver.find_elements(By.XPATH, selector)
                        
                        if not country_elements:
                            continue
                        
                        # Try each matching element
                        for country_element in country_elements:
                            try:
                                # Wait for element to be visible and clickable
                                WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable(country_element)
                                )
                                
                                # Scroll element into view
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                                    country_element
                                )
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                try:
                                    # Method 1: Regular click
                                    country_element.click()
                                    logger.info(f"Clicked country '{name_to_search}' using regular click")
                                except Exception as e1:
                                    logger.debug(f"Regular click failed, trying JavaScript click: {e1}")
                                    try:
                                        # Method 2: JavaScript click (more reliable for modals)
                                        self.driver.execute_script("arguments[0].click();", country_element)
                                        logger.info(f"Clicked country '{name_to_search}' using JavaScript click")
                                    except Exception as e2:
                                        logger.debug(f"JavaScript click failed: {e2}")
                                        # Method 3: Click via ActionChains
                                        ActionChains(self.driver).move_to_element(country_element).click().perform()
                                        logger.info(f"Clicked country '{name_to_search}' using ActionChains")
                                
                                country_clicked = True
                                time.sleep(4)  # Wait for page to load after country selection
                                break
                                
                            except Exception as e:
                                logger.debug(f"Error clicking element: {e}")
                                continue
                        
                        if country_clicked:
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {e}")
                        continue
                
                if country_clicked:
                    break
            
            if not country_clicked:
                logger.warning(f"Could not find or click country '{country_name}'")
                logger.info("Attempting to list available countries for debugging...")
                
                # Debug: Find all potential country links
                try:
                    # Look for all links in the modal/popup area
                    all_country_elements = self.driver.find_elements(By.XPATH, 
                        "//div[contains(@class, 'modal')]//a | "
                        "//div[contains(@class, 'popup')]//a | "
                        "//li//a | "
                        "//*[contains(text(), 'Europe') or contains(text(), 'North America') or contains(text(), 'Asia/Pacific')]//following-sibling::*//a | "
                        "//ul//a"
                    )
                    
                    if all_country_elements:
                        logger.info(f"Found {len(all_country_elements)} potential country links:")
                        for i, elem in enumerate(all_country_elements[:20]):  # Show first 20
                            try:
                                text = elem.text.strip()
                                if text and len(text) < 50:  # Filter out long text
                                    logger.info(f"  {i+1}. '{text}' (tag: {elem.tag_name})")
                            except:
                                pass
                    
                    # Save screenshot for debugging
                    try:
                        self.driver.save_screenshot("country_popup_debug.png")
                        logger.info("Debug screenshot saved as country_popup_debug.png")
                    except:
                        pass
                        
                except Exception as e:
                    logger.debug(f"Could not list available countries: {e}")
            
            logger.info("Country popup handling completed")
            
        except Exception as e:
            logger.error(f"Error handling country popup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue anyway as popup might not be blocking
    
    def search_product(self, product_code):
        """
        Search for a product using the product code
        
        Args:
            product_code (str): Product code to search (e.g., "76181-190")
        
        Returns:
            bool: True if search was successful
        """
        try:
            logger.info(f"Searching for product: {product_code}")
            wait = WebDriverWait(self.driver, 15)
            
            # Find search input field - common selectors
            search_selectors = [
                "//input[contains(@name, 'search')]",
                "//input[contains(@id, 'search')]",
                "//input[contains(@placeholder, 'Search')]",
                "//input[contains(@type, 'search')]",
                "//input[contains(@class, 'search')]",
                "//*[@role='searchbox']",
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    logger.info(f"Found search input using: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not search_input:
                logger.error("Could not find search input field")
                return False
            
            # Clear and enter product code
            search_input.clear()
            search_input.send_keys(product_code)
            time.sleep(1)
            
            # Find and click search button
            search_button_selectors = [
                "//button[contains(@type, 'submit')]",
                "//button[contains(@class, 'search')]",
                "//button[contains(@aria-label, 'Search')]",
                "//*[@type='submit']",
                "//button[contains(text(), 'Search')]",
            ]
            
            for btn_selector in search_button_selectors:
                try:
                    search_btn = self.driver.find_element(By.XPATH, btn_selector)
                    search_btn.click()
                    logger.info("Clicked search button")
                    break
                except:
                    continue
            else:
                # Try pressing Enter
                search_input.send_keys("\n")
                logger.info("Pressed Enter in search field")
            
            # Wait for search results or product page to load
            time.sleep(5)
            
            logger.info("Search completed")
            return True
            
        except Exception as e:
            logger.error(f"Error searching for product: {e}")
            return False
    
    def _expand_specification_sections(self):
        """
        Try to expand any accordion/tabs sections that might contain specifications
        """
        try:
            logger.info("Looking for expandable specification sections...")
            
            # Common accordion/tab selectors
            expand_selectors = [
                "//button[contains(text(), 'Specification')]",
                "//a[contains(text(), 'Specification')]",
                "//div[contains(@class, 'accordion-header')]//button[contains(text(), 'Spec')]",
                "//ngb-accordion//button",
                "//div[contains(@class, 'tab')]//a[contains(text(), 'Spec')]",
                "//div[contains(@class, 'panel-heading')]//a[contains(text(), 'Spec')]",
                "//*[contains(text(), 'More Product Details')]",
                "//*[contains(text(), 'View Details')]",
                "//*[contains(text(), 'Show More')]",
                "//*[contains(text(), 'View Specifications')]",
            ]
            
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            # Check if it's visible and clickable
                            if elem.is_displayed() and elem.is_enabled():
                                # Scroll into view
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                time.sleep(0.5)
                                # Try clicking
                                elem.click()
                                logger.info(f"Expanded section: {elem.text.strip()}")
                                time.sleep(1)  # Wait for content to load
                        except:
                            continue
                except:
                    continue
            
            # Also try to find and click any collapsed accordion items
            try:
                collapsed_items = self.driver.find_elements(By.XPATH,
                    "//button[contains(@aria-expanded, 'false')] | " +
                    "//a[contains(@aria-expanded, 'false')] | " +
                    "//div[contains(@class, 'collapsed')]"
                )
                for item in collapsed_items[:3]:  # Try first 3 collapsed items
                    try:
                        if item.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                            time.sleep(0.5)
                            item.click()
                            time.sleep(1)
                    except:
                        continue
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error expanding sections: {e}")
    
    def _extract_specs_from_all_elements(self):
        """
        Try to extract specifications by examining all elements on the page
        Returns dict of found specifications
        """
        specs = {}
        
        try:
            logger.info("Examining all page elements for specification patterns...")
            
            # Get all text elements that might contain specs
            all_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
            
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    if not text or len(text) < 3:
                        continue
                    
                    # Look for patterns like "Property: Value" or "Property - Value"
                    # Check if element or parent has spec-related class/id
                    parent_classes = elem.find_elements(By.XPATH, "./ancestor::*[@class]")
                    is_spec_related = False
                    
                    # Check element classes
                    try:
                        elem_class = elem.get_attribute('class') or ''
                        elem_id = elem.get_attribute('id') or ''
                        if any(word in elem_class.lower() + elem_id.lower() for word in ['spec', 'property', 'attribute', 'detail', 'feature']):
                            is_spec_related = True
                    except:
                        pass
                    
                    # Check parent classes
                    for parent in parent_classes[:3]:  # Check up to 3 levels up
                        try:
                            parent_class = parent.get_attribute('class') or ''
                            if any(word in parent_class.lower() for word in ['spec', 'property', 'attribute', 'detail']):
                                is_spec_related = True
                                break
                        except:
                            continue
                    
                    # If looks like spec-related, try to extract key-value pairs
                    if is_spec_related or ':' in text:
                        # Try colon pattern
                        if ':' in text and len(text.split(':')) == 2:
                            parts = text.split(':', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key and value and 2 < len(key) < 80:
                                # Filter out common non-spec patterns
                                skip_patterns = ['javascript', 'function', 'click', 'button', 'link', 'http', 'www']
                                if not any(pattern in key.lower() for pattern in skip_patterns):
                                    specs[key] = value
                        
                        # Try dash pattern
                        elif ' - ' in text and len(text.split(' - ')) == 2:
                            parts = text.split(' - ', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key and value and 2 < len(key) < 80:
                                specs[key] = value
                    
                    # Look for adjacent elements that might form key-value pairs
                    try:
                        # Check if this element's text looks like a key and next sibling is value
                        elem_tag = elem.tag_name
                        if elem_tag in ['dt', 'th', 'strong', 'b']:
                            # Try to find following sibling or next element for value
                            value_elem = elem.find_elements(By.XPATH, "./following-sibling::dd | ./following-sibling::td | ./following-sibling::*[1]")
                            if value_elem:
                                key = elem.text.strip()
                                value = value_elem[0].text.strip()
                                if key and value and 2 < len(key) < 80:
                                    specs[key] = value
                    except:
                        pass
                        
                except Exception as e:
                    continue
            
            if specs:
                logger.info(f"Found {len(specs)} specifications from element examination")
            
        except Exception as e:
            logger.debug(f"Error in _extract_specs_from_all_elements: {e}")
        
        return specs
    
    def _save_page_for_debugging(self):
        """Save page HTML and screenshot for debugging specifications"""
        try:
            logger.info("Saving page HTML for debugging...")
            
            # Save full page HTML
            html_content = self.driver.page_source
            with open("debug_page_source.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info("Page HTML saved to debug_page_source.html")
            
            # Save screenshot
            self.driver.save_screenshot("debug_page_screenshot.png")
            logger.info("Screenshot saved to debug_page_screenshot.png")
            
            # Try to find and save just the product details section
            try:
                product_sections = self.driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'product')] | " +
                    "//div[contains(@class, 'details')] | " +
                    "//main | " +
                    "//div[contains(@class, 'content')]"
                )
                
                if product_sections:
                    # Get HTML of first product section
                    section_html = product_sections[0].get_attribute('outerHTML')
                    with open("debug_product_section.html", 'w', encoding='utf-8') as f:
                        f.write(section_html)
                    logger.info("Product section HTML saved to debug_product_section.html")
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error saving page for debugging: {e}")
    
    def extract_product_data(self):
        """
        Extract product data including specifications, price, model description, etc.
        
        Returns:
            dict: Dictionary containing extracted product data
        """
        product_data = {
            "product_code": None,
            "product_name": None,
            "model_number": None,
            "description": None,
            "price": None,
            "currency": None,
            "specifications": {},
            "availability": None,
            "url": self.driver.current_url,
        }
        
        try:
            logger.info("Extracting product data...")
            wait = WebDriverWait(self.driver, 10)
            
            # Extract product name/title
            title_selectors = [
                "//h1[contains(@class, 'product-title')]",
                "//h1[contains(@class, 'product-name')]",
                "//h1[contains(@class, 'title')]",
                "//h1",
                "//*[contains(@class, 'product-title')]",
            ]
            for selector in title_selectors:
                try:
                    title = self.driver.find_element(By.XPATH, selector)
                    product_data["product_name"] = title.text.strip()
                    logger.info(f"Found product name: {product_data['product_name']}")
                    break
                except:
                    continue
            
            # Extract product code/SKU
            sku_selectors = [
                "//*[contains(text(), 'SKU')]/following-sibling::*",
                "//*[contains(text(), 'Product Code')]/following-sibling::*",
                "//*[contains(text(), 'Catalog Number')]/following-sibling::*",
                "//*[contains(@class, 'sku')]",
                "//*[contains(@class, 'product-code')]",
                "//*[contains(@class, 'catalog-number')]",
            ]
            for selector in sku_selectors:
                try:
                    sku = self.driver.find_element(By.XPATH, selector)
                    product_data["product_code"] = sku.text.strip()
                    break
                except:
                    continue
            
            # Extract price
            price_selectors = [
                "//*[contains(@class, 'price')]",
                "//*[contains(@class, 'product-price')]",
                "//*[contains(@data-testid, 'price')]",
                "//span[contains(@class, 'price')]",
            ]
            for selector in price_selectors:
                try:
                    price_elem = self.driver.find_element(By.XPATH, selector)
                    price_text = price_elem.text.strip()
                    # Extract price and currency
                    import re
                    price_match = re.search(r'[\d,]+\.?\d*', price_text)
                    if price_match:
                        product_data["price"] = price_match.group().replace(',', '')
                    currency_match = re.search(r'[A-Z]{3}|\$|€|£', price_text)
                    if currency_match:
                        product_data["currency"] = currency_match.group()
                    logger.info(f"Found price: {price_text}")
                    break
                except:
                    continue
            
            # Extract description - specifically target div.no-select-spec
            logger.info("Extracting description from div.no-select-spec...")
            
            # First, try to expand the collapsed section if needed
            try:
                collapsed_section = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'no-select-spec') and contains(@class, 'collapsed')]"
                )
                # Try to expand it by clicking "More Product Details" or similar
                try:
                    expand_link = self.driver.find_element(By.XPATH,
                        "//div[contains(@class, 'no-select-spec')]//a[contains(text(), 'More Product Details')] | " +
                        "//div[contains(@class, 'no-select-spec')]//a[contains(text(), 'More')] | " +
                        "//div[contains(@class, 'no-select-spec')]//button[contains(text(), 'More')]"
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", expand_link)
                    time.sleep(0.5)
                    expand_link.click()
                    time.sleep(2)
                    logger.info("Expanded no-select-spec section")
                except:
                    # Try to remove collapsed class or click the div itself
                    try:
                        self.driver.execute_script("arguments[0].classList.remove('collapsed');", collapsed_section)
                        time.sleep(1)
                    except:
                        pass
            except:
                pass
            
            # Extract description from div.no-select-spec
            desc_selectors = [
                # Primary target: div.no-select-spec
                "//div[contains(@class, 'no-select-spec')]",
                "//div[@class='no-select-spec collapsed']",
                "//div[contains(@class, 'no-select-spec') and contains(@class, 'collapsed')]",
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.XPATH, selector)
                    desc_text = desc_elem.text.strip()
                    
                    if desc_text and len(desc_text) > 20:  # Ensure it's meaningful content
                        product_data["description"] = desc_text
                        logger.info(f"Found product description from {selector}")
                        logger.info(f"Description length: {len(desc_text)} characters")
                        break
                except:
                    continue
            
            # If still no description, try fallback selectors
            if not product_data["description"]:
                fallback_selectors = [
                    "//div[contains(@class, 'no-select-spec')]//div[contains(@class, 'd-block')]",
                    "//div[contains(@class, 'no-select-spec')]//p",
                    "//div[contains(@class, 'product-description')]",
                    "//div[contains(@class, 'description')]",
                    "//div[contains(@class, 'product-details')]//p",
                ]
                
                for selector in fallback_selectors:
                    try:
                        desc = self.driver.find_element(By.XPATH, selector)
                        desc_text = desc.text.strip()
                        if desc_text and len(desc_text) > 20:
                            product_data["description"] = desc_text
                            logger.info(f"Found product description from fallback: {selector}")
                            break
                    except:
                        continue
            
            # Extract specifications - try multiple methods and locations
            logger.info("Extracting specifications...")
            
            # Method 0: Specifically target the spec-table ul element (highest priority)
            # Structure: <ul class="spec-table text-break">
            #   <li>
            #     <div class="name-col ...">Key:</div>
            #     <div class="value-col ...">Value</div>
            #   </li>
            try:
                logger.info("Looking for ul.spec-table element...")
                spec_table_ul = self.driver.find_elements(By.XPATH, 
                    "//ul[contains(@class, 'spec-table')] | " +
                    "//ul[@class='spec-table text-break'] | " +
                    "//ul[contains(@class, 'spec-table') and contains(@class, 'text-break')]"
                )
                
                if spec_table_ul:
                    logger.info(f"Found {len(spec_table_ul)} spec-table ul element(s)")
                    for ul in spec_table_ul:
                        try:
                            # Find all list items in the ul
                            list_items = ul.find_elements(By.XPATH, ".//li")
                            
                            for li in list_items:
                                try:
                                    # Find name-col (key) and value-col (value)
                                    name_col = li.find_elements(By.XPATH, ".//div[contains(@class, 'name-col')]")
                                    value_col = li.find_elements(By.XPATH, ".//div[contains(@class, 'value-col')]")
                                    
                                    if name_col and value_col:
                                        key = name_col[0].text.strip()
                                        value = value_col[0].text.strip()
                                        
                                        # Remove colon from key if present
                                        if key.endswith(':'):
                                            key = key[:-1].strip()
                                        
                                        if key and value:
                                            product_data["specifications"][key] = value
                                            logger.debug(f"  - {key}: {value}")
                                
                                except Exception as e:
                                    logger.debug(f"Error parsing list item: {e}")
                                    continue
                            
                            if product_data["specifications"]:
                                logger.info(f"Extracted {len(product_data['specifications'])} specifications from spec-table ul")
                                break
                                
                        except Exception as e:
                            logger.debug(f"Error parsing spec-table ul: {e}")
                            continue
                    
                    if product_data["specifications"]:
                        # Already extracted, skip other methods
                        logger.info("Successfully extracted specifications from spec-table ul element")
            except Exception as e:
                logger.debug(f"Error finding spec-table ul: {e}")
            
            # First, specifically look for "Product Details & Documents and Specifications" section (only if not already extracted)
            if not product_data["specifications"]:
                spec_section_found = False
            spec_section_selectors = [
                "//*[contains(text(), 'Product Details & Documents and Specifications')]",
                "//*[contains(text(), 'Product Details') and contains(text(), 'Specifications')]",
                "//*[contains(text(), 'Specifications')]/ancestor::*[contains(@class, 'accordion') or contains(@class, 'panel') or contains(@class, 'tab')]",
                "//*[contains(text(), 'Product Details')]/ancestor::*[contains(@class, 'accordion') or contains(@class, 'panel')]",
                "//*[contains(text(), 'Specifications')]/parent::*",
                "//button[contains(text(), 'Product Details')] | //a[contains(text(), 'Product Details')]",
                "//button[contains(text(), 'Specifications')] | //a[contains(text(), 'Specifications')]",
            ]
            
            for selector in spec_section_selectors:
                try:
                    spec_section_elem = self.driver.find_element(By.XPATH, selector)
                    
                    # If it's a button/link, try clicking it to expand
                    if spec_section_elem.tag_name in ['button', 'a']:
                        try:
                            logger.info("Found specifications section button/link, clicking to expand...")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", spec_section_elem)
                            time.sleep(0.5)
                            spec_section_elem.click()
                            time.sleep(2)  # Wait for content to load
                            logger.info("Expanded specifications section")
                        except:
                            # Try JavaScript click
                            self.driver.execute_script("arguments[0].click();", spec_section_elem)
                            time.sleep(2)
                    
                    # Now try to find the content
                    spec_section_found = True
                    
                    # Get the parent container or following sibling that contains the actual content
                    try:
                        # Try to find content in parent or following elements
                        parent = spec_section_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'accordion') or contains(@class, 'panel') or contains(@class, 'tab-content')][1]")
                        
                        # Extract from this parent container
                        logger.info("Extracting from 'Product Details & Documents and Specifications' section...")
                        
                        # Try tables first
                        tables = parent.find_elements(By.XPATH, ".//table")
                        if tables:
                            for table in tables:
                                rows = table.find_elements(By.XPATH, ".//tr")
                                for row in rows:
                                    try:
                                        cells = row.find_elements(By.XPATH, ".//td | .//th")
                                        if len(cells) >= 2:
                                            key = cells[0].text.strip()
                                            value = cells[1].text.strip()
                                            if key and value and key.lower() not in ['property', 'value', 'specification']:
                                                product_data["specifications"][key] = value
                                    except:
                                        continue
                        
                        # Try definition lists
                        if not product_data["specifications"]:
                            dls = parent.find_elements(By.XPATH, ".//dl")
                            for dl in dls:
                                dts = dl.find_elements(By.XPATH, ".//dt")
                                dds = dl.find_elements(By.XPATH, ".//dd")
                                for i in range(min(len(dts), len(dds))):
                                    key = dts[i].text.strip()
                                    value = dds[i].text.strip()
                                    if key and value:
                                        product_data["specifications"][key] = value
                        
                        # Try any divs or spans with key-value pattern
                        if not product_data["specifications"]:
                            all_text = parent.text
                            lines = all_text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if ':' in line and len(line.split(':')) == 2:
                                    parts = line.split(':', 1)
                                    key = parts[0].strip()
                                    value = parts[1].strip()
                                    if key and value and 2 < len(key) < 80:
                                        product_data["specifications"][key] = value
                                elif ' - ' in line and len(line.split(' - ')) == 2:
                                    parts = line.split(' - ', 1)
                                    key = parts[0].strip()
                                    value = parts[1].strip()
                                    if key and value and 2 < len(key) < 80:
                                        product_data["specifications"][key] = value
                        
                        if product_data["specifications"]:
                            logger.info(f"Extracted {len(product_data['specifications'])} specifications from 'Product Details & Documents and Specifications' section")
                            break
                    
                    except Exception as e:
                        logger.debug(f"Error extracting from section parent: {e}")
                        # Try extracting from the element itself or its siblings
                        try:
                            # Try following siblings
                            following_siblings = spec_section_elem.find_elements(By.XPATH, "./following-sibling::*")
                            for sibling in following_siblings[:5]:  # Check first 5 siblings
                                try:
                                    text = sibling.text.strip()
                                    if text:
                                        lines = text.split('\n')
                                        for line in lines:
                                            if ':' in line:
                                                parts = line.split(':', 1)
                                                if len(parts) == 2:
                                                    key = parts[0].strip()
                                                    value = parts[1].strip()
                                                    if key and value:
                                                        product_data["specifications"][key] = value
                                except:
                                    continue
                        except:
                            pass
                    
                    if product_data["specifications"]:
                        break
                        
                except:
                    continue
            
            if spec_section_found and product_data["specifications"]:
                logger.info("Successfully extracted specifications from 'Product Details & Documents and Specifications' section")
            
            # Method 1: Try tables with various class patterns
            spec_selectors = [
                "//table[contains(@class, 'specification')]",
                "//table[contains(@class, 'spec')]",
                "//table[contains(@class, 'property')]",
                "//table[contains(@class, 'attribute')]",
                "//table[contains(@class, 'details')]",
                "//dl[contains(@class, 'specification')]",
                "//dl[contains(@class, 'property')]",
                "//div[contains(@class, 'specifications')]//table",
                "//div[contains(@class, 'specs')]//table",
                "//*[contains(@class, 'specification-table')]",
                "//*[contains(@class, 'product-specifications')]//table",
                "//*[contains(@class, 'product-specs')]//table",
            ]
            
            for selector in spec_selectors:
                try:
                    spec_table = self.driver.find_element(By.XPATH, selector)
                    logger.info(f"Found specification table using: {selector}")
                    # Extract table data
                    rows = spec_table.find_elements(By.XPATH, ".//tr")
                    for row in rows:
                        try:
                            cells = row.find_elements(By.XPATH, ".//td | .//th")
                            if len(cells) >= 2:
                                key = cells[0].text.strip()
                                value = cells[1].text.strip()
                                if key and value and key.lower() not in ['', 'property', 'value', 'specification']:
                                    product_data["specifications"][key] = value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from table")
                        break
                except:
                    continue
            
            # Method 2: Try definition lists (dl/dt/dd)
            if not product_data["specifications"]:
                try:
                    dl_selectors = [
                        "//dl[contains(@class, 'specification')]",
                        "//dl[contains(@class, 'property')]",
                        "//dl[contains(@class, 'attribute')]",
                        "//dl[contains(@class, 'details')]",
                        "//div[contains(@class, 'specifications')]//dl",
                        "//div[contains(@class, 'specs')]//dl",
                    ]
                    
                    for dl_selector in dl_selectors:
                        try:
                            dl_elements = self.driver.find_elements(By.XPATH, dl_selector)
                            for dl in dl_elements:
                                dts = dl.find_elements(By.XPATH, ".//dt")
                                dds = dl.find_elements(By.XPATH, ".//dd")
                                
                                for i in range(min(len(dts), len(dds))):
                                    try:
                                        key = dts[i].text.strip()
                                        value = dds[i].text.strip()
                                        if key and value:
                                            product_data["specifications"][key] = value
                                    except:
                                        continue
                            
                            if product_data["specifications"]:
                                logger.info(f"Extracted {len(product_data['specifications'])} specifications from definition list")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Error extracting from definition lists: {e}")
            
            # Method 3: Try div-based specifications (key-value pairs in divs)
            if not product_data["specifications"]:
                try:
                    # Look for common patterns: div with key and value classes
                    spec_items = self.driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'specification')]//div[contains(@class, 'property')] | " +
                        "//div[contains(@class, 'spec-item')] | " +
                        "//div[contains(@class, 'property-item')] | " +
                        "//div[contains(@class, 'attribute-item')] | " +
                        "//div[contains(@class, 'spec')]//div[contains(@class, 'row')]"
                    )
                    
                    for item in spec_items:
                        try:
                            # Try to find key and value within the item
                            key_elem = item.find_elements(By.XPATH, ".//*[contains(@class, 'key')] | .//*[contains(@class, 'label')] | .//*[contains(@class, 'name')] | .//strong | .//b")
                            value_elem = item.find_elements(By.XPATH, ".//*[contains(@class, 'value')] | .//*[contains(@class, 'data')] | .//span[not(contains(@class, 'key'))]")
                            
                            if key_elem and value_elem:
                                key = key_elem[0].text.strip()
                                value = value_elem[0].text.strip()
                                if key and value:
                                    product_data["specifications"][key] = value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from div items")
                except Exception as e:
                    logger.debug(f"Error extracting from div items: {e}")
            
            # Method 4: Try lists (ul/li) with specifications
            if not product_data["specifications"]:
                try:
                    spec_lists = self.driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'specification')]//ul | " +
                        "//div[contains(@class, 'specs')]//ul | " +
                        "//*[contains(@class, 'product-specifications')]//ul | " +
                        "//ul[contains(@class, 'specification')]"
                    )
                    
                    for ul in spec_lists:
                        try:
                            list_items = ul.find_elements(By.XPATH, ".//li")
                            for li in list_items:
                                text = li.text.strip()
                                # Try to split on colon or dash
                                if ':' in text:
                                    parts = text.split(':', 1)
                                    if len(parts) == 2:
                                        key = parts[0].strip()
                                        value = parts[1].strip()
                                        if key and value:
                                            product_data["specifications"][key] = value
                                elif ' - ' in text:
                                    parts = text.split(' - ', 1)
                                    if len(parts) == 2:
                                        key = parts[0].strip()
                                        value = parts[1].strip()
                                        if key and value:
                                            product_data["specifications"][key] = value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from lists")
                except Exception as e:
                    logger.debug(f"Error extracting from lists: {e}")
            
            # Method 5: Try accordion/tabs sections (common in Angular apps)
            if not product_data["specifications"]:
                try:
                    # Look for accordion panels or tabs
                    accordion_selectors = [
                        "//div[contains(@class, 'accordion')]//div[contains(text(), 'Specification') or contains(text(), 'Specs')]/following-sibling::*",
                        "//div[contains(@class, 'tab-content')]//div[contains(@class, 'specification')]",
                        "//ngb-accordion//*[contains(text(), 'Specification')]/following-sibling::*",
                        "//div[contains(@class, 'panel')]//div[contains(@class, 'specification')]",
                    ]
                    
                    for selector in accordion_selectors:
                        try:
                            spec_section = self.driver.find_element(By.XPATH, selector)
                            # Try to extract as table or list from this section
                            rows = spec_section.find_elements(By.XPATH, ".//tr")
                            if rows:
                                for row in rows:
                                    try:
                                        cells = row.find_elements(By.XPATH, ".//td | .//th")
                                        if len(cells) >= 2:
                                            key = cells[0].text.strip()
                                            value = cells[1].text.strip()
                                            if key and value:
                                                product_data["specifications"][key] = value
                                    except:
                                        continue
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from accordion/tabs")
                except Exception as e:
                    logger.debug(f"Error extracting from accordion: {e}")
            
            # Method 6: Try to find any div with "Specification" or "Property" in class/id
            if not product_data["specifications"]:
                try:
                    all_spec_divs = self.driver.find_elements(By.XPATH,
                        "//div[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specification')] | " +
                        "//div[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'property')] | " +
                        "//div[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specification')] | " +
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specification')]/following-sibling::*"
                    )
                    
                    for div in all_spec_divs:
                        try:
                            # Try extracting as key-value pairs from text content
                            text = div.text.strip()
                            lines = text.split('\n')
                            for line in lines:
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    if len(parts) == 2:
                                        key = parts[0].strip()
                                        value = parts[1].strip()
                                        if key and value and len(key) < 100 and len(value) < 500:
                                            product_data["specifications"][key] = value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from generic divs")
                except Exception as e:
                    logger.debug(f"Error extracting from generic divs: {e}")
            
            # Method 7: Try extracting from JSON-LD structured data
            if not product_data["specifications"]:
                try:
                    json_ld_scripts = self.driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                    for script in json_ld_scripts:
                        try:
                            import json
                            data = json.loads(script.get_attribute('innerHTML'))
                            # Look for specification properties in JSON-LD
                            if isinstance(data, dict):
                                if 'offers' in data and isinstance(data['offers'], dict):
                                    if 'itemOffered' in data['offers']:
                                        item = data['offers']['itemOffered']
                                        # Extract additional properties
                                        for key, value in item.items():
                                            if key not in ['@type', '@context', 'name', 'image', 'description']:
                                                if isinstance(value, (str, int, float)):
                                                    product_data["specifications"][key] = str(value)
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from JSON-LD")
                except Exception as e:
                    logger.debug(f"Error extracting from JSON-LD: {e}")
            
            # Method 8: Extract from ANY table on the page (last resort)
            if not product_data["specifications"]:
                try:
                    logger.info("Trying to extract from any table on the page...")
                    all_tables = self.driver.find_elements(By.XPATH, "//table")
                    logger.info(f"Found {len(all_tables)} tables on the page")
                    
                    for idx, table in enumerate(all_tables):
                        try:
                            rows = table.find_elements(By.XPATH, ".//tr")
                            if len(rows) >= 2:  # At least header and one data row
                                for row in rows:
                                    try:
                                        cells = row.find_elements(By.XPATH, ".//td | .//th")
                                        if len(cells) >= 2:
                                            key = cells[0].text.strip()
                                            value = cells[1].text.strip()
                                            # Filter out non-spec data
                                            if key and value and len(key) > 0 and len(key) < 100:
                                                # Skip if it looks like navigation/header
                                                if key.lower() not in ['home', 'products', 'services', 'about', 'contact', 'menu']:
                                                    product_data["specifications"][key] = value
                                    except:
                                        continue
                                
                                if product_data["specifications"]:
                                    logger.info(f"Extracted {len(product_data['specifications'])} specifications from table {idx+1}")
                                    break
                        except Exception as e:
                            logger.debug(f"Error processing table {idx+1}: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Error extracting from all tables: {e}")
            
            # Method 9: Try extracting key-value pairs from any text content
            if not product_data["specifications"]:
                try:
                    logger.info("Trying to extract key-value pairs from text content...")
                    # Look for common spec patterns in the description or any text
                    all_text_elements = self.driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'product')] | " +
                        "//div[contains(@class, 'details')] | " +
                        "//div[contains(@class, 'content')]"
                    )
                    
                    for elem in all_text_elements:
                        try:
                            text = elem.text.strip()
                            lines = text.split('\n')
                            
                            for line in lines:
                                line = line.strip()
                                # Look for patterns like "Key: Value" or "Key - Value" or "Key Value"
                                if ':' in line and len(line.split(':')) == 2:
                                    parts = line.split(':', 1)
                                    key = parts[0].strip()
                                    value = parts[1].strip()
                                    if key and value and 2 < len(key) < 50 and len(value) < 200:
                                        # Skip common non-spec text
                                        skip_words = ['price', 'cart', 'buy', 'add to', 'description', 'overview', 'return']
                                        if not any(skip in key.lower() for skip in skip_words):
                                            product_data["specifications"][key] = value
                                elif ' - ' in line and len(line.split(' - ')) == 2:
                                    parts = line.split(' - ', 1)
                                    key = parts[0].strip()
                                    value = parts[1].strip()
                                    if key and value and 2 < len(key) < 50 and len(value) < 200:
                                        product_data["specifications"][key] = value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from text content")
                except Exception as e:
                    logger.debug(f"Error extracting from text content: {e}")
            
            # Method 10: Look for Angular component attributes/data
            if not product_data["specifications"]:
                try:
                    logger.info("Trying to extract from Angular component attributes...")
                    # Look for elements with data attributes that might contain specs
                    data_elements = self.driver.find_elements(By.XPATH,
                        "//*[@data-spec] | " +
                        "//*[@data-property] | " +
                        "//*[@data-attribute] | " +
                        "//*[contains(@data-*, 'spec')]"
                    )
                    
                    for elem in data_elements:
                        try:
                            # Try to get all data attributes
                            attrs = self.driver.execute_script(
                                "var items = {}; "
                                "for (index = 0; index < arguments[0].attributes.length; ++index) { "
                                "  items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value "
                                "}; "
                                "return items;",
                                elem
                            )
                            
                            for attr_name, attr_value in attrs.items():
                                if 'spec' in attr_name.lower() or 'property' in attr_name.lower():
                                    product_data["specifications"][attr_name] = attr_value
                        except:
                            continue
                    
                    if product_data["specifications"]:
                        logger.info(f"Extracted {len(product_data['specifications'])} specifications from Angular attributes")
                except Exception as e:
                    logger.debug(f"Error extracting from Angular attributes: {e}")
            
            # Log final result
            if product_data["specifications"]:
                logger.info(f"Total specifications extracted: {len(product_data['specifications'])}")
                for key, value in list(product_data["specifications"].items())[:5]:  # Log first 5
                    logger.info(f"  - {key}: {value}")
            else:
                logger.warning("No specifications found using any extraction method")
                logger.info("Consider checking the page HTML manually or inspecting with browser DevTools")
            
            # Extract availability/stock status
            availability_selectors = [
                "//*[contains(@class, 'availability')]",
                "//*[contains(@class, 'stock')]",
                "//*[contains(text(), 'In Stock')] | //*[contains(text(), 'Out of Stock')]",
            ]
            for selector in availability_selectors:
                try:
                    avail = self.driver.find_element(By.XPATH, selector)
                    product_data["availability"] = avail.text.strip()
                    break
                except:
                    continue
            
            logger.info("Product data extraction completed")
            
        except Exception as e:
            logger.error(f"Error extracting product data: {e}")
        
        return product_data
    
    def scrape_product(self, product_code, country_name=None, country_url=None):
        """
        Main method to scrape a product
        
        Args:
            product_code (str): Product code to search (e.g., "76181-190")
            country_name (str): Optional country name for popup selection (if country_url not provided)
            country_url (str): Optional direct country URL (e.g., "https://www.avantorsciences.com/us/")
        
        Returns:
            dict: Extracted product data
        """
        try:
            logger.info(f"Starting scrape for product: {product_code}")
            
            # If country_url is provided, navigate directly to it
            if country_url:
                logger.info(f"Navigating directly to country URL: {country_url}")
                self.driver.get(country_url)
                time.sleep(5)
                
                # Handle cookie banner
                self.handle_cookie_banner()
            else:
                # Navigate to main website and handle country popup
                logger.info(f"Navigating to {self.base_url}")
                self.driver.get(self.base_url)
                time.sleep(5)
                
                # Handle country popup
                self.handle_country_popup(country_name)
            
            # Search for product
            if not self.search_product(product_code):
                logger.error("Product search failed")
                return None
            
            # Wait for product page to load
            time.sleep(5)
            
            # Try to expand any accordion/tabs sections that might contain specifications
            self._expand_specification_sections()
            
            # Wait a bit more after expanding
            time.sleep(2)
            
            # Extract product data
            product_data = self.extract_product_data()
            product_data["product_code"] = product_code  # Ensure product code is set
            
            # If still no specifications, try additional methods and save for debugging
            if not product_data.get("specifications"):
                logger.info("No specifications found yet, trying additional extraction methods...")
                # Try one more time with a longer wait and scroll
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Retry extraction with different approach
                additional_specs = self._extract_specs_from_all_elements()
                if additional_specs:
                    product_data["specifications"].update(additional_specs)
                
                # Save page for debugging
                self._save_page_for_debugging()
            
            return product_data
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return None
    
    def save_to_csv(self, product_data, filename=None):
        """
        Save product data to CSV file
        
        Args:
            product_data (dict): Product data dictionary or list of product data dictionaries
            filename (str): Output CSV filename. If None, generates from product code or timestamp
        
        Returns:
            str: Path to saved CSV file
        """
        try:
            # Handle single product or list of products
            if isinstance(product_data, dict):
                products = [product_data]
            else:
                products = product_data
            
            if not products:
                logger.warning("No product data to save")
                return None
            
            # Generate filename if not provided
            if not filename:
                if len(products) == 1 and products[0].get('product_code'):
                    filename = f"product_{products[0]['product_code']}.csv"
                else:
                    filename = f"products_{int(time.time())}.csv"
            
            # Helper function to clean and normalize text for CSV
            def clean_text_for_csv(text):
                """Clean text for CSV export, preserving special characters"""
                if text is None:
                    return ''
                # Convert to string
                text = str(text)
                # Replace newlines with spaces for CSV readability
                text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
                # Replace multiple spaces with single space
                import re
                text = re.sub(r'\s+', ' ', text)
                # Strip whitespace
                text = text.strip()
                return text
            
            # Flatten specifications for CSV
            rows = []
            for product in products:
                row = {
                    'Product Code': clean_text_for_csv(product.get('product_code', '')),
                    'Product Name': clean_text_for_csv(product.get('product_name', '')),
                    'Model Number': clean_text_for_csv(product.get('model_number', '')),
                    'Description': clean_text_for_csv(product.get('description', '')),
                    'Price': clean_text_for_csv(product.get('price', '')),
                    'Currency': clean_text_for_csv(product.get('currency', '')),
                    'Availability': clean_text_for_csv(product.get('availability', '')),
                    'URL': product.get('url', ''),
                }
                
                # Add specifications as separate columns
                specs = product.get('specifications', {})
                if isinstance(specs, dict):
                    for key, value in specs.items():
                        # Clean key for CSV column name using helper function
                        clean_key = clean_text_for_csv(key)
                        if clean_key:
                            # Use key as column name, value as cell content
                            if clean_key not in row:
                                row[clean_key] = clean_text_for_csv(value)
                            else:
                                # If key already exists, append value
                                row[clean_key] = clean_text_for_csv(row[clean_key]) + '; ' + clean_text_for_csv(value)
                
                rows.append(row)
            
            # Get all unique keys (columns) across all rows
            all_keys = set()
            for row in rows:
                all_keys.update(row.keys())
            
            # Sort keys to have standard fields first, then specifications
            standard_fields = ['Product Code', 'Product Name', 'Model Number', 'Description', 
                             'Price', 'Currency', 'Availability', 'URL']
            ordered_keys = [k for k in standard_fields if k in all_keys]
            spec_keys = sorted([k for k in all_keys if k not in standard_fields])
            fieldnames = ordered_keys + spec_keys
            
            # Write to CSV with UTF-8 BOM for Excel compatibility
            # Use 'utf-8-sig' encoding to add BOM (Byte Order Mark) which helps Excel open UTF-8 files correctly
            # This ensures special characters like ®, ×, etc. are displayed properly in Excel
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore', quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                for row in rows:
                    # Ensure all keys exist in row
                    cleaned_row = {}
                    for key in fieldnames:
                        if key in row:
                            # Values are already cleaned by clean_text_for_csv function
                            cleaned_row[key] = row[key]
                        else:
                            cleaned_row[key] = ''
                    writer.writerow(cleaned_row)
            
            logger.info(f"Product data saved to {filename}")
            logger.info(f"Saved {len(rows)} product(s) with {len(fieldnames)} columns")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """Example usage"""
    import sys
    
    scraper = None
    try:
        # Initialize scraper
        scraper = AvantorScraper(headless=False)  # Set to True for headless mode
        
        # Check if user wants to extract countries first
        if len(sys.argv) > 1 and sys.argv[1] == "--countries":
            print("Extracting countries and URLs from popup...")
            scraper.driver.get(scraper.base_url)
            time.sleep(5)
            
            countries_data = scraper.extract_countries_and_urls()
            
            print("\n" + "="*60)
            print("EXTRACTED COUNTRIES AND URLs")
            print("="*60)
            print(json.dumps(countries_data, indent=2))
            print("="*60)
            
            # Save to JSON file
            output_file = "countries_and_urls.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(countries_data, f, indent=2, ensure_ascii=False)
            print(f"\nData saved to {output_file}")
            return
        
        # Scrape product
        product_code = "76181-190"
        country_name = "United States"  # Optional: specify country
        
        product_data = scraper.scrape_product(product_code, country_name)
        
        if product_data:
            print("\n" + "="*50)
            print("EXTRACTED PRODUCT DATA")
            print("="*50)
            print(json.dumps(product_data, indent=2))
            print("="*50)
            
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
            print("Failed to extract product data")
    
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()

