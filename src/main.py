import asyncio
import logging
import argparse
import os
import sys
from datetime import datetime
import schedule
import time
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.sheets import GoogleSheetsConfig
from scrapers.openrent import OpenRentScraper
from scrapers.rightmove import RightmoveScraper
from storage.database import PropertyStorage
from notifications.telegram import TelegramNotifier

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/data/scraper.log') if os.path.exists('/app/data') else logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PropertyScrapeBot:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.storage = PropertyStorage()
        
        # Initialize components
        try:
            self.sheets_config = GoogleSheetsConfig()
            self.telegram_notifier = TelegramNotifier(test_mode=test_mode)
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
            
    async def run_scraping_cycle(self, sheets_url: str = None):
        """Run a complete scraping cycle"""
        logger.info("Starting scraping cycle")
        
        try:
            # Use default sheet URL if provided in environment
            if not sheets_url:
                sheets_url = os.getenv('GOOGLE_SHEETS_URL')
                
            if not sheets_url:
                logger.error("No Google Sheets URL provided")
                return
                
            # Load search configurations
            search_configs = self.sheets_config.load_search_configs(sheets_url)
            
            if not search_configs:
                logger.warning("No active search configurations found")
                return
                
            logger.info(f"Processing {len(search_configs)} search configurations")
            
            for config in search_configs:
                await self._process_search_config(config)
                
            # Clean up old properties (older than 30 days)
            self.storage.cleanup_old_properties(30)
            
            logger.info("Scraping cycle completed")
            
        except Exception as e:
            logger.error(f"Error in scraping cycle: {e}")
            raise
            
    async def _process_search_config(self, config):
        """Process a single search configuration"""
        logger.info(f"Processing: {config.description} ({config.site})")
        
        try:
            # Get appropriate scraper
            if config.site == 'openrent':
                scraper = OpenRentScraper(max_price_pp=config.max_price_pp)
            elif config.site == 'rightmove':
                scraper = RightmoveScraper(max_price_pp=config.max_price_pp)
            else:
                logger.warning(f"Unsupported site: {config.site}")
                return
                
            # Scrape properties
            properties = scraper.scrape_properties(config.url)
            logger.info(f"Found {len(properties)} properties for {config.description}")
            
            # Filter out already seen properties
            new_properties = []
            for prop in properties:
                if not self.storage.is_property_seen(prop.url, config.config_id):
                    new_properties.append(prop)
                    self.storage.mark_property_as_seen(
                        prop.url, 
                        config.config_id,
                        prop.title,
                        prop.price,
                        prop.location
                    )
                    
            logger.info(f"Found {len(new_properties)} new properties for {config.description}")
            
            # Send notifications for new properties
            if new_properties:
                for prop in new_properties:
                    await self.telegram_notifier.send_property_notification(
                        prop,
                        config.telegram_chat_ids,
                        config.description
                    )
                    
                # Send summary
                await self.telegram_notifier.send_summary_notification(
                    config.telegram_chat_ids,
                    len(new_properties),
                    config.description
                )
                
        except Exception as e:
            logger.error(f"Error processing {config.description}: {e}")
            
    async def test_configuration(self, sheets_url: str):
        """Test the configuration without running a full scrape"""
        logger.info("Testing configuration...")
        
        # Test Telegram connection
        if await self.telegram_notifier.test_connection():
            logger.info("✓ Telegram bot connection successful")
        else:
            logger.error("✗ Telegram bot connection failed")
            return False
            
        # Test Google Sheets connection
        if self.sheets_config.validate_spreadsheet_format(sheets_url):
            logger.info("✓ Google Sheets connection successful")
        else:
            logger.error("✗ Google Sheets connection failed")
            return False
            
        # Load and validate configurations
        configs = self.sheets_config.load_search_configs(sheets_url)
        logger.info(f"✓ Loaded {len(configs)} search configurations")
        
        for config in configs:
            logger.info(f"  - {config.description} ({config.site}) - {len(config.telegram_chat_ids)} chats")
            
        return True

def main():
    parser = argparse.ArgumentParser(description='Property Scraper Bot')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (no actual Telegram messages)')
    parser.add_argument('--sheets-url', help='Google Sheets URL')
    parser.add_argument('--test-config', action='store_true', help='Test configuration only')
    parser.add_argument('--run-once', action='store_true', help='Run once instead of scheduling')
    
    args = parser.parse_args()
    
    try:
        bot = PropertyScrapeBot(test_mode=args.test_mode)
        
        if args.test_config:
            # Test configuration
            sheets_url = args.sheets_url or os.getenv('GOOGLE_SHEETS_URL')
            if not sheets_url:
                logger.error("No Google Sheets URL provided")
                sys.exit(1)
                
            success = asyncio.run(bot.test_configuration(sheets_url))
            sys.exit(0 if success else 1)
            
        if args.run_once:
            # Run once
            asyncio.run(bot.run_scraping_cycle(args.sheets_url))
        else:
            # Schedule to run every 30 minutes
            def run_scheduled():
                asyncio.run(bot.run_scraping_cycle(args.sheets_url))
                
            schedule.every(30).minutes.do(run_scheduled)
            
            logger.info("Bot started. Running every 30 minutes...")
            logger.info("Press Ctrl+C to stop")
            
            # Run immediately first time
            run_scheduled()
            
            # Then run on schedule
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()