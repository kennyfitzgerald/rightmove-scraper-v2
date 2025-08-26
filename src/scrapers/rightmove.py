import time
import random
import logging
import json
import re
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

class RightmoveScraper(BaseScraper):
    def __init__(self, max_price_pp: float = None):
        super().__init__(max_price_pp)
        self.driver = None
    
    def _setup_driver(self):
        """Setup Chrome driver with headless options"""
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Use chromium-driver path for ARM64/Debian
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception:
            # Fallback to chromium
            self.driver = webdriver.Chrome(
                service=Service('/usr/bin/chromedriver'),
                options=chrome_options
            )
        return self.driver
    
    def _cleanup_driver(self):
        """Clean up the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def scrape_properties(self, search_url: str) -> List[Property]:
        try:
            logger.info(f"Scraping Rightmove URL: {search_url}")
            
            # Setup driver
            driver = self._setup_driver()
            
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(2, 5))
            
            # Load the page
            driver.get(search_url)
            
            # Wait for properties to load
            wait = WebDriverWait(driver, 20)
            
            # Try to find property listings after page loads
            properties = []
            
            try:
                # Wait for property listings to appear
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 
                    "[data-test='search-result'], .l-searchResult, .propertyCard, [id*='property']")))
                
                # Give it a bit more time for all elements to load
                time.sleep(3)
                
                # Implement scrolling to load more properties
                logger.info("Starting to scroll to load more properties...")
                last_property_count = 0
                max_scrolls = 10  # Limit scrolling to prevent infinite loops
                scroll_attempts = 0
                
                while scroll_attempts < max_scrolls:
                    # Scroll to the bottom of the page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for new content to load
                    
                    # Check if new properties loaded
                    current_property_elements = driver.find_elements(By.CSS_SELECTOR, "[data-test*='property']")
                    current_count = len(current_property_elements)
                    
                    logger.info(f"Scroll {scroll_attempts + 1}: Found {current_count} properties (was {last_property_count})")
                    
                    if current_count > last_property_count:
                        # New properties loaded, continue scrolling
                        last_property_count = current_count
                        scroll_attempts += 1
                    else:
                        # No new properties loaded, we've reached the end
                        logger.info(f"No new properties loaded after scroll {scroll_attempts + 1}, stopping")
                        break
                
                logger.info(f"Finished scrolling. Total properties found: {current_count}")
                
                # Try to find property elements directly in the rendered page
                property_selectors = [
                    "div[data-test='search-result']",
                    "[data-test*='property']", 
                    "div.l-searchResult", 
                    "div.propertyCard",
                    "article[data-test*='property']",
                    "div[class*='propertyCard']",
                    ".propertyCard-wrapper",
                    ".searchResults div[data-test]",
                    "[class*='SearchResult']",
                    "[class*='searchResult']",
                    "div[class*='Property']",
                    "div[class*='Card']"
                ]
                
                property_elements = []
                for selector in property_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        
                        # If we found link elements, get their parent containers instead
                        if elements and elements[0].tag_name == 'a':
                            logger.info("Found link elements - getting parent containers...")
                            parent_elements = []
                            for link_elem in elements:
                                parent = link_elem.find_element(By.XPATH, "..")  # Get parent element
                                parent_elements.append(parent)
                            property_elements = parent_elements
                        else:
                            property_elements = elements
                        break
                
                # If no specific property elements found, look for all data-test elements for debugging
                if not property_elements:
                    logger.warning("No property elements found with standard selectors. Checking all data-test elements...")
                    all_data_test_elements = driver.find_elements(By.CSS_SELECTOR, "[data-test]")
                    logger.info(f"Found {len(all_data_test_elements)} elements with data-test attributes")
                    
                    # Log first few data-test values
                    for i, elem in enumerate(all_data_test_elements[:10]):
                        data_test_val = elem.get_attribute('data-test')
                        elem_text = elem.text.strip()[:50] if elem.text else 'no-text'
                        logger.info(f"  data-test='{data_test_val}', text='{elem_text}'")
                        
                        # If we find something that looks like a property result, use it
                        if any(keyword in data_test_val.lower() for keyword in ['result', 'card', 'listing', 'item']):
                            property_elements.append(elem)
                
                logger.info(f"Found {len(property_elements)} property elements to extract")
                
                # Limit extraction to reasonable number to avoid too many individual page visits
                max_properties_to_extract = 15
                properties_to_process = property_elements[:max_properties_to_extract]
                logger.info(f"Processing first {len(properties_to_process)} properties to avoid excessive page visits")
                
                # Extract data from each property element
                for i, element in enumerate(properties_to_process):
                    try:
                        logger.info(f"Extracting property {i+1}/{len(properties_to_process)}")
                        
                        # Debug: log element info
                        element_tag = element.tag_name
                        element_id = element.get_attribute('id') or 'no-id'
                        element_class = element.get_attribute('class') or 'no-class'
                        element_text = element.text.strip()[:100] if element.text else 'no-text'
                        logger.info(f"Element {i+1}: tag={element_tag}, id={element_id}, class={element_class[:50]}, text={element_text}...")
                        
                        prop = self._extract_property_from_element(element, driver)
                        if prop:
                            properties.append(prop)
                            logger.info(f"Successfully extracted: {prop.title[:50]}... - {prop.price}")
                        else:
                            logger.warning(f"Failed to extract property data from element {i+1}")
                    except Exception as e:
                        logger.error(f"Error extracting property from element {i+1}: {e}")
                        continue
                
            except TimeoutException:
                logger.warning("Timeout waiting for properties to load - checking page content")
                
                # Try alternative approach - look for any property cards directly
                property_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "[data-test='search-result'], .l-searchResult, .propertyCard, div[id*='property']")
                
                logger.info(f"Found {len(property_elements)} property elements via direct search")
                
                # Limit to reasonable number for fallback as well
                properties_to_process = property_elements[:15]
                logger.info(f"Processing first {len(properties_to_process)} properties from fallback search")
                
                for i, element in enumerate(properties_to_process):
                    try:
                        logger.info(f"Fallback extraction: property {i+1}/{len(properties_to_process)}")
                        prop = self._extract_property_from_element(element, driver)
                        if prop:
                            properties.append(prop)
                    except Exception as e:
                        logger.error(f"Error extracting property from element {i+1}: {e}")
                        continue
            
            logger.info(f"Found {len(properties)} properties total")
            return self.filter_by_price(properties)
            
        except Exception as e:
            logger.error(f"Unexpected error scraping {search_url}: {e}")
            return []
        finally:
            self._cleanup_driver()
    
    def _extract_property_ids(self, driver) -> List[str]:
        """Extract property IDs from the page"""
        property_ids = []
        
        try:
            # Look for property IDs in the page source/JavaScript
            page_source = driver.page_source
            
            # Try to find property IDs in various formats
            patterns = [
                r'property-(\d+)',
                r'"id":\s*"?(\d+)"?',
                r'propertyId["\']:\s*["\']?(\d+)["\']?',
                r'data-id=["\'](\d+)["\']',
                r'/property-details/(\d+)',
            ]
            
            found_ids = set()
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    logger.info(f"Pattern '{pattern}' found {len(matches)} matches: {matches[:3]}...")
                found_ids.update(matches)
            
            property_ids = list(found_ids)
            logger.info(f"Total unique property IDs from regex: {len(property_ids)}")
            
            # Also try to find IDs in DOM elements
            elements_with_ids = driver.find_elements(By.CSS_SELECTOR, "[data-id], [id*='property']")
            for element in elements_with_ids:
                data_id = element.get_attribute('data-id')
                if data_id and data_id.isdigit():
                    property_ids.append(data_id)
                    
                element_id = element.get_attribute('id')
                if element_id and 'property' in element_id:
                    # Extract numeric part from ID like 'property-123456'
                    id_match = re.search(r'(\d+)', element_id)
                    if id_match:
                        property_ids.append(id_match.group(1))
            
            return list(set(property_ids))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting property IDs: {e}")
            return []
    
    def _extract_property_from_id(self, driver, prop_id: str, base_url: str) -> Property:
        """Extract property data using property ID"""
        try:
            # Try to find element by various ID patterns
            selectors = [
                f"[data-id='{prop_id}']",
                f"#property-{prop_id}",
                f"[id*='{prop_id}']",
            ]
            
            element = None
            for selector in selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if element:
                return self._extract_property_from_element(element, driver)
                
        except Exception as e:
            logger.error(f"Error finding element for property ID {prop_id}: {e}")
        
        return None
    
    def _extract_property_from_element(self, element, driver) -> Property:
        """Extract property data from a DOM element"""
        try:
            # Extract URL - try multiple approaches
            url = ""
            link_selectors = [
                "a[href*='property-details']",
                "a[href*='/properties/']", 
                "a[href*='rightmove.co.uk']",
                "a"
            ]
            
            for selector in link_selectors:
                try:
                    link_element = element.find_element(By.CSS_SELECTOR, selector)
                    href = link_element.get_attribute('href')
                    if href and ('rightmove' in href or href.startswith('/')):
                        url = href if href.startswith('http') else f"https://www.rightmove.co.uk{href}"
                        break
                except NoSuchElementException:
                    continue
            
            # Extract title from element text - first line is usually the address/title
            full_text = element.text.strip()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            title = "No title"
            if lines:
                # First line is typically the address/title
                title = lines[0]
            
            # Fallback to CSS selectors if needed
            if title == "No title" or len(title) < 3:
                title_selectors = [
                    "h2", "h3", "h4", 
                    ".propertyCard-title", 
                    "[data-test*='title']",
                    "[data-test*='heading']",
                    "a[href*='property']"
                ]
                
                for selector in title_selectors:
                    try:
                        title_element = element.find_element(By.CSS_SELECTOR, selector)
                        title_text = title_element.text.strip()
                        if title_text and len(title_text) > 3:
                            title = title_text
                            break
                    except NoSuchElementException:
                        continue
            
            # Extract price and bedrooms for per-person calculation
            price = "Price not found"
            bedrooms = 1  # Default to 1 if not found
            
            # Parse text to find price and bedroom count
            logger.debug(f"Parsing text: {lines}")
            
            # First try to find price in the text lines
            for line in lines:
                if '£' in line:
                    price = line.strip()
                    break
            
            # If no price in main text, try CSS selectors
            if price == "Price not found":
                price_selectors = [
                    ".propertyCard-priceValue",
                    "[data-test*='price']", 
                    ".price",
                    "span[class*='price']",
                    "div[class*='price']",
                    "*[class*='Price']"
                ]
                
                for selector in price_selectors:
                    try:
                        price_element = element.find_element(By.CSS_SELECTOR, selector)
                        price_text = price_element.text.strip()
                        if price_text and '£' in price_text:
                            price = price_text
                            break
                    except NoSuchElementException:
                        continue
            
            # Extract bedroom count from text (look for number that appears to be bedrooms)
            for line in lines:
                # Look for standalone numbers that could be bedroom count
                if line.isdigit() and 1 <= int(line) <= 10:
                    bedrooms = int(line)
                    break
                # Sometimes it's in format like "4 bed" or "4 bedroom"
                import re
                bed_match = re.search(r'(\d+)\s*bed', line.lower())
                if bed_match:
                    bedrooms = int(bed_match.group(1))
                    break
            
            # Try to find price in parent/ancestor elements if still not found
            if price == "Price not found":
                try:
                    # Try parent element first
                    parent = element.find_element(By.XPATH, "..")
                    price_elements = parent.find_elements(By.CSS_SELECTOR, "*")
                    for elem in price_elements:
                        elem_text = elem.text.strip()
                        if '£' in elem_text and ('pcm' in elem_text.lower() or 'pw' in elem_text.lower() or 'month' in elem_text.lower() or len(elem_text) < 20):
                            price = elem_text
                            logger.info(f"Found price in parent element: {price}")
                            break
                    
                    # If still not found, try grandparent
                    if price == "Price not found":
                        grandparent = parent.find_element(By.XPATH, "..")
                        price_elements = grandparent.find_elements(By.CSS_SELECTOR, "*")
                        for elem in price_elements:
                            elem_text = elem.text.strip()
                            if '£' in elem_text and ('pcm' in elem_text.lower() or 'pw' in elem_text.lower() or 'month' in elem_text.lower() or len(elem_text) < 20):
                                price = elem_text
                                logger.info(f"Found price in grandparent element: {price}")
                                break
                                
                except NoSuchElementException:
                    pass
            
            
            # Extract location/address
            location = "Location not found"
            location_selectors = [
                ".propertyCard-address", 
                "[data-test*='address']",
                "address",
                ".address",
                "*[class*='address']",
                "*[class*='location']"
            ]
            
            for selector in location_selectors:
                try:
                    location_element = element.find_element(By.CSS_SELECTOR, selector)
                    location_text = location_element.text.strip()
                    if location_text and len(location_text) > 3:
                        location = location_text
                        break
                except NoSuchElementException:
                    continue
            
            # Extract description
            description = ""
            desc_selectors = [
                ".propertyCard-description", 
                "[data-test*='description']",
                ".description"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_element = element.find_element(By.CSS_SELECTOR, selector)
                    description = desc_element.text.strip()
                    if description:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract images
            images = []
            try:
                img_element = element.find_element(By.CSS_SELECTOR, "img")
                img_src = img_element.get_attribute('src')
                if img_src and 'http' in img_src:
                    images.append(img_src)
            except NoSuchElementException:
                pass
            
            # Debug: if we have a URL, visit the individual property page to get the price
            if url and price == "Price not found":
                try:
                    logger.info(f"Visiting individual property page for price: {url}")
                    original_window = driver.current_window_handle
                    driver.execute_script(f"window.open('{url}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])
                    
                    # Wait for page to load
                    time.sleep(3)
                    
                    # Look for price on the individual property page
                    price_selectors_individual = [
                        "span[data-testid='price']",
                        ".propertyHeaderPrice",
                        "[data-test*='price']",
                        ".price",
                        "span[class*='price']",
                        "div[class*='price']",
                        "*[class*='Price']"
                    ]
                    
                    for selector in price_selectors_individual:
                        try:
                            price_elem = driver.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and '£' in price_text:
                                price = price_text
                                logger.info(f"Found price on individual page: {price}")
                                break
                        except NoSuchElementException:
                            continue
                    
                    # If still not found, search page source for price patterns
                    if price == "Price not found":
                        page_source = driver.page_source
                        import re
                        price_patterns = [
                            r'£([\d,]+)\s*pcm',
                            r'£([\d,]+)\s*per calendar month',
                            r'£([\d,]+)\s*per month',
                            r'"price"["\s:]*"?£?([\d,]+)"?',
                            r'price["\s:]*£([\d,]+)'
                        ]
                        
                        for pattern in price_patterns:
                            matches = re.findall(pattern, page_source.lower())
                            if matches:
                                # Take the first reasonable price (between £500-£50000)
                                for match in matches:
                                    price_val = int(match.replace(',', ''))
                                    if 500 <= price_val <= 50000:
                                        price = f"£{price_val} pcm"
                                        logger.info(f"Found price in page source: {price}")
                                        break
                                if price != "Price not found":
                                    break
                    
                    # Close the individual property tab and return to main page
                    driver.close()
                    driver.switch_to.window(original_window)
                    
                except Exception as e:
                    logger.warning(f"Error getting price from individual page: {e}")
                    try:
                        driver.switch_to.window(original_window)
                    except:
                        pass
            
            # Calculate price per person if we have a valid price
            if price != "Price not found" and '£' in price:
                try:
                    # Extract numeric price
                    import re
                    price_match = re.search(r'£([\d,]+)', price.replace(' ', ''))
                    if price_match:
                        total_price = float(price_match.group(1).replace(',', ''))
                        price_per_person = total_price / bedrooms
                        price = f"£{price_per_person:.0f} pp/pcm (£{total_price:.0f} total/{bedrooms}br)"
                        logger.info(f"Calculated price per person: £{total_price}/month ÷ {bedrooms} bedrooms = £{price_per_person:.0f} pp/pcm")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not calculate price per person: {e}")
            
            # Debug logging  
            logger.info(f"Final extracted data - URL: {url[:50] if url else 'none'}, Title: {title[:30]}, Price: {price}, Location: {location[:30] if location != 'Location not found' else 'none'}")
            
            if url or (title != "No title" and len(title) > 5):  # Return if we found meaningful data
                return Property(
                    url=url,
                    title=title,
                    price=price,
                    location=location,
                    description=description,
                    images=images
                )
                
        except Exception as e:
            logger.error(f"Error extracting property data from element: {e}")
        
        return None
