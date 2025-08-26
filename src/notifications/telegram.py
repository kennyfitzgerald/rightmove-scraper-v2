import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from typing import List
import os
from scrapers.base import Property

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str = None, test_mode: bool = False):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.test_mode = test_mode
        
        if not self.bot_token:
            raise ValueError("Telegram bot token not provided")
            
        self.bot = Bot(token=self.bot_token)
        
    async def send_property_notification(self, property_obj: Property, 
                                       chat_ids: List[str], search_description: str = ""):
        """Send property notification to specified Telegram chats"""
        
        if self.test_mode:
            self._print_test_notification(property_obj, chat_ids, search_description)
            return
            
        message = self._format_property_message(property_obj, search_description)
        
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                )
                logger.info(f"Property notification sent to chat {chat_id}")
                
                # If property has images, send the first one
                if property_obj.images:
                    try:
                        await self.bot.send_photo(
                            chat_id=chat_id,
                            photo=property_obj.images[0],
                            caption=f"📸 {property_obj.title[:50]}..."
                        )
                    except TelegramError as e:
                        logger.warning(f"Failed to send image to chat {chat_id}: {e}")
                        
                # Small delay between messages to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except TelegramError as e:
                logger.error(f"Failed to send message to chat {chat_id}: {e}")
                
    def _format_property_message(self, property_obj: Property, search_description: str) -> str:
        """Format property data into a Telegram message"""
        
        # Emoji based on price range
        price_emoji = "💰"
        try:
            price_value = float(property_obj.price.replace('£', '').replace(',', '').replace(' pcm', ''))
            if price_value < 1000:
                price_emoji = "💚"
            elif price_value < 1500:
                price_emoji = "💛"
            elif price_value < 2000:
                price_emoji = "🧡"
            else:
                price_emoji = "❤️"
        except:
            pass
            
        message_parts = []
        
        # Header
        if search_description:
            message_parts.append(f"🏠 <b>New Property: {search_description}</b>")
        else:
            message_parts.append(f"🏠 <b>New Property Found</b>")
            
        message_parts.append("")
        
        # Property details
        message_parts.append(f"📍 <b>Title:</b> {property_obj.title}")
        message_parts.append(f"{price_emoji} <b>Price:</b> {property_obj.price}")
        message_parts.append(f"📌 <b>Location:</b> {property_obj.location}")
        
        if property_obj.description and len(property_obj.description.strip()) > 0:
            # Truncate description if too long
            desc = property_obj.description.strip()
            if len(desc) > 200:
                desc = desc[:200] + "..."
            message_parts.append(f"📝 <b>Description:</b> {desc}")
            
        message_parts.append("")
        message_parts.append(f"🔗 <a href='{property_obj.url}'>View Property</a>")
        
        return "\n".join(message_parts)
        
    def _print_test_notification(self, property_obj: Property, chat_ids: List[str], search_description: str):
        """Print notification to console for testing"""
        print("\n" + "="*60)
        print("📱 TEST MODE - TELEGRAM NOTIFICATION")
        print("="*60)
        print(f"Chat IDs: {', '.join(chat_ids)}")
        print(f"Search: {search_description}")
        print("-"*60)
        print(self._format_property_message(property_obj, search_description))
        print("="*60)
        
    async def send_summary_notification(self, chat_ids: List[str], 
                                      properties_count: int, search_description: str = ""):
        """Send a summary notification"""
        
        if properties_count == 0:
            return
            
        message = f"📊 <b>Search Summary</b>\n\n"
        if search_description:
            message += f"Search: {search_description}\n"
        message += f"New properties found: {properties_count}"
        
        if self.test_mode:
            print(f"\n📊 TEST MODE - SUMMARY: {properties_count} new properties for '{search_description}'")
            return
            
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Summary notification sent to chat {chat_id}")
            except TelegramError as e:
                logger.error(f"Failed to send summary to chat {chat_id}: {e}")
                
    async def test_connection(self) -> bool:
        """Test if the bot token is valid"""
        try:
            await self.bot.get_me()
            logger.info("Telegram bot connection test successful")
            return True
        except TelegramError as e:
            logger.error(f"Telegram bot connection test failed: {e}")
            return False