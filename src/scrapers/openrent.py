import requests
from bs4 import BeautifulSoup
from typing import List
import time
import random
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

class OpenRentScraper(BaseScraper):
    def __init__(self, max_price_pp: float = None):
        super().__init__(max_price_pp)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def scrape_properties(self, search_url: str) -> List[Property]:
        try:
            logger.info(f"Scraping OpenRent URL: {search_url}")
            
            # Add random delay to avoid being blocked
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            properties = []
            
            # Find property listings - OpenRent uses specific class names
            property_cards = soup.find_all('div', class_='listing-result')
            
            if not property_cards:
                # Try alternative selectors
                property_cards = soup.find_all('article', class_='property-card')
                
            if not property_cards:
                logger.warning(f"No property cards found for URL: {search_url}")
                return []
                
            for card in property_cards:
                try:
                    prop = self._extract_property_data(card, search_url)
                    if prop:
                        properties.append(prop)
                except Exception as e:
                    logger.error(f"Error extracting property data: {e}")
                    continue
                    
            logger.info(f"Found {len(properties)} properties")
            return self.filter_by_price(properties)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {search_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping {search_url}: {e}")
            return []
            
    def _extract_property_data(self, card, base_url: str) -> Property:
        # Extract URL
        url_elem = card.find('a', href=True)
        if not url_elem:
            return None
            
        relative_url = url_elem['href']
        full_url = urljoin('https://www.openrent.com', relative_url)
        
        # Extract title
        title_elem = card.find('h2') or card.find('h3') or card.find('a')
        title = title_elem.get_text(strip=True) if title_elem else "No title"
        
        # Extract price
        price_elem = card.find('span', class_='price') or card.find('div', class_='price')
        if not price_elem:
            # Try alternative price selectors
            price_elem = card.find('strong') or card.find('b')
            
        price = "Price not found"
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            if '£' in price_text:
                price = price_text
                
        # Extract location
        location_elem = card.find('span', class_='location') or card.find('div', class_='location')
        if not location_elem:
            # Try to find address or area information
            location_elem = card.find('span', class_='address') or card.find('div', class_='address')
            
        location = location_elem.get_text(strip=True) if location_elem else "Location not found"
        
        # Extract description
        desc_elem = card.find('p', class_='description') or card.find('div', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract images
        images = []
        img_elem = card.find('img')
        if img_elem and img_elem.get('src'):
            images.append(urljoin('https://www.openrent.com', img_elem['src']))
            
        return Property(
            url=full_url,
            title=title,
            price=price,
            location=location,
            description=description,
            images=images
        )