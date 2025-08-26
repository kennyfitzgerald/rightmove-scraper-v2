import unittest
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.base import Property
from scrapers.openrent import OpenRentScraper

class TestScrapers(unittest.TestCase):
    
    def test_property_creation(self):
        """Test Property class"""
        prop = Property(
            url="https://example.com/property/1",
            title="Test Property",
            price="£1200 pcm",
            location="Test Location",
            description="A nice property",
            images=["image1.jpg"]
        )
        
        self.assertEqual(prop.url, "https://example.com/property/1")
        self.assertEqual(prop.title, "Test Property")
        self.assertEqual(prop.price, "£1200 pcm")
        
        prop_dict = prop.to_dict()
        self.assertIn('url', prop_dict)
        self.assertIn('title', prop_dict)
        
    def test_price_filtering(self):
        """Test price filtering functionality"""
        scraper = OpenRentScraper(max_price_pp=1500)
        
        properties = [
            Property("url1", "Cheap Property", "£1000 pcm", "Location 1"),
            Property("url2", "Expensive Property", "£2000 pcm", "Location 2"),
            Property("url3", "Weekly Property", "£300 pw", "Location 3"),  # £1300 pcm
        ]
        
        filtered = scraper.filter_by_price(properties)
        self.assertEqual(len(filtered), 2)  # Should filter out the £2000 property
        
if __name__ == '__main__':
    unittest.main()