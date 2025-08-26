from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Property:
    def __init__(self, url: str, title: str, price: str, location: str, 
                 description: str = "", images: List[str] = None):
        self.url = url
        self.title = title
        self.price = price
        self.location = location
        self.description = description
        self.images = images or []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'title': self.title,
            'price': self.price,
            'location': self.location,
            'description': self.description,
            'images': self.images
        }

class BaseScraper(ABC):
    def __init__(self, max_price_pp: float = None):
        self.max_price_pp = max_price_pp
        
    @abstractmethod
    def scrape_properties(self, search_url: str) -> List[Property]:
        pass
        
    def filter_by_price(self, properties: List[Property]) -> List[Property]:
        if not self.max_price_pp:
            return properties
            
        filtered = []
        for prop in properties:
            try:
                price_str = prop.price
                
                # Handle per-person price format: "£1250 pp/pcm (£5000 total/4br)"
                if 'pp/pcm' in price_str:
                    # Extract the per-person price (first number)
                    import re
                    pp_match = re.search(r'£([\d,]+)\s*pp/pcm', price_str)
                    if pp_match:
                        price = float(pp_match.group(1).replace(',', ''))
                    else:
                        continue
                else:
                    # Legacy format handling
                    price_clean = price_str.replace('£', '').replace(',', '').replace(' pcm', '').replace(' pw', '')
                    if 'pw' in price_str.lower():
                        price = float(price_clean) * 52 / 12  # Convert weekly to monthly
                    else:
                        price = float(price_clean)
                        
                if price <= self.max_price_pp:
                    filtered.append(prop)
                    logger.info(f"Property {prop.title[:30]}... passes price filter: £{price:.0f} <= £{self.max_price_pp}")
                else:
                    logger.info(f"Property {prop.title[:30]}... filtered out: £{price:.0f} > £{self.max_price_pp}")
                    
            except (ValueError, AttributeError, TypeError) as e:
                logger.warning(f"Could not parse price for property {prop.title}: {prop.price} - {e}")
                continue
                
        return filtered