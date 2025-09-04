import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import os
import logging
import requests
import csv
import hashlib
from io import StringIO
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchConfig:
    url: str
    site: str
    telegram_chat_ids: List[str]
    max_price_pp: float
    active: bool
    description: str
    config_id: str  # Unique identifier for this search configuration

class GoogleSheetsConfig:
    def __init__(self, credentials_json: str = None):
        self.credentials_json = credentials_json or os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        self.gc = None
        self.use_public_access = False
        self._authenticate()
        
    def _authenticate(self):
        # Try public access first if no credentials provided
        if not self.credentials_json:
            logger.info("No credentials provided, will try public sheet access")
            self.use_public_access = True
            return
            
        try:
            # Try to decode if it's base64 encoded
            try:
                credentials_data = base64.b64decode(self.credentials_json)
                credentials_dict = json.loads(credentials_data)
            except:
                # If not base64, assume it's already JSON
                if os.path.isfile(self.credentials_json):
                    with open(self.credentials_json, 'r') as f:
                        credentials_dict = json.load(f)
                else:
                    credentials_dict = json.loads(self.credentials_json)
                    
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_info(
                credentials_dict, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(credentials)
            logger.info("Google Sheets authentication successful")
            
        except Exception as e:
            logger.warning(f"Failed to authenticate with Google Sheets, falling back to public access: {e}")
            self.use_public_access = True
            
    def load_search_configs(self, spreadsheet_url: str) -> List[SearchConfig]:
        try:
            # Extract spreadsheet ID from URL
            if '/d/' in spreadsheet_url:
                spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
            else:
                spreadsheet_id = spreadsheet_url
            
            # Load data based on access method
            if self.use_public_access:
                records = self._load_public_sheet_data(spreadsheet_id)
            else:
                sheet = self.gc.open_by_key(spreadsheet_id).sheet1
                records = sheet.get_all_records()
            
            configs = []
            for i, record in enumerate(records):
                try:
                    # Parse telegram chat IDs (can be comma-separated)
                    chat_ids_str = str(record.get('telegram_chat_ids', ''))
                    telegram_chat_ids = [
                        chat_id.strip() 
                        for chat_id in chat_ids_str.split(',') 
                        if chat_id.strip()
                    ]
                    
                    # Parse max price
                    max_price_str = str(record.get('max_price_pp', '0'))
                    try:
                        max_price_pp = float(max_price_str) if max_price_str else 0
                    except ValueError:
                        max_price_pp = 0
                        
                    # Parse active status
                    active_str = str(record.get('active', 'true')).lower()
                    active = active_str in ['true', '1', 'yes', 'on']
                    
                    config = SearchConfig(
                        url=record.get('url', ''),
                        site=record.get('site', '').lower(),
                        telegram_chat_ids=telegram_chat_ids,
                        max_price_pp=max_price_pp,
                        active=active,
                        description=record.get('description', ''),
                        config_id=f"config_{i}_{hashlib.md5(record.get('url', '').encode()).hexdigest()[:8]}"
                    )
                    
                    # Validate required fields
                    if config.url and config.site and config.telegram_chat_ids and config.active:
                        configs.append(config)
                        logger.info(f"Loaded config: {config.description} ({config.site})")
                    else:
                        logger.warning(f"Skipping invalid config at row {i+2}: missing required fields")
                        
                except Exception as e:
                    logger.error(f"Error parsing row {i+2}: {e}")
                    continue
                    
            logger.info(f"Loaded {len(configs)} valid search configurations")
            return configs
            
        except Exception as e:
            logger.error(f"Failed to load search configurations: {e}")
            return []
            
    def _load_public_sheet_data(self, spreadsheet_id: str) -> List[Dict]:
        """Load data from public Google Sheet using CSV export URL"""
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid=0"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV data
            csv_content = StringIO(response.text)
            reader = csv.DictReader(csv_content)
            records = list(reader)
            
            logger.info(f"Loaded {len(records)} records from public sheet")
            return records
            
        except Exception as e:
            logger.error(f"Failed to load public sheet data: {e}")
            return []

    def validate_spreadsheet_format(self, spreadsheet_url: str) -> bool:
        try:
            if '/d/' in spreadsheet_url:
                spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
            else:
                spreadsheet_id = spreadsheet_url
            
            # Get headers based on access method
            if self.use_public_access:
                records = self._load_public_sheet_data(spreadsheet_id)
                if not records:
                    return False
                headers = list(records[0].keys()) if records else []
            else:
                sheet = self.gc.open_by_key(spreadsheet_id).sheet1
                headers = sheet.row_values(1)
            
            required_headers = ['url', 'site', 'telegram_chat_ids', 'max_price_pp', 'active', 'description']
            missing_headers = [h for h in required_headers if h not in headers]
            
            if missing_headers:
                logger.error(f"Missing required headers: {missing_headers}")
                return False
                
            logger.info("Spreadsheet format validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate spreadsheet format: {e}")
            return False