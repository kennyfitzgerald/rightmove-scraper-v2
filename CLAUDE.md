# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Testing
```bash
# Test configuration (validates Telegram bot, Google Sheets access)
python src/main.py --test-config --sheets-url "your_sheets_url"

# Run once in test mode (prints to console instead of sending Telegram messages)
python src/main.py --run-once --test-mode --sheets-url "your_sheets_url" 

# Run once for real (sends actual Telegram notifications)
python src/main.py --run-once --sheets-url "your_sheets_url"

# Run with scheduling (production mode, runs every 30 minutes)
python src/main.py --sheets-url "your_sheets_url"
```

### Docker Development
```bash
# Test configuration
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --test-config --sheets-url "your_sheets_url"

# Run once in test mode
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --run-once --test-mode --sheets-url "your_sheets_url"

# Run once for real
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --run-once --sheets-url "your_sheets_url"
```

### Testing
```bash
# Run unit tests
python -m pytest tests/
# or
python -m unittest discover tests/
```

## Architecture

### Core Components
- **main.py**: Main application orchestrator with CLI interface and scheduling
- **scrapers/**: Modular scrapers with abstract base class pattern
  - `base.py`: Abstract BaseScraper class and Property data model
  - `openrent.py`: OpenRent-specific scraper implementation  
  - `rightmove.py`: Rightmove-specific scraper implementation
- **config/sheets.py**: Google Sheets integration for search configuration
- **storage/database.py**: SQLite database for tracking seen properties
- **notifications/telegram.py**: Telegram bot notifications

### Key Design Patterns
- **Abstract Base Class**: BaseScraper provides common interface for all property scrapers
- **Selenium WebDriver**: Modern JavaScript-rendered property sites handled via Chrome/Chromium headless
- **Infinite Scroll Support**: Automatically scrolls to load additional property listings (20+ vs 5 previously)
- **Individual Property Page Visits**: Visits each property page for accurate price extraction
- **Per-Person Price Calculations**: Automatically divides total rent by bedroom count
- **Rate Limiting**: Processes max 15 properties per search to avoid overwhelming sites
- **Configuration-Driven**: Search parameters defined in Google Sheets, not hardcoded
- **Database Persistence**: GitHub Actions artifact-based database persistence between runs

### Data Flow
1. Load search configurations from Google Sheets (URL, site, telegram chats, max price per person, etc.)
2. For each active configuration, instantiate appropriate scraper (Selenium-based for Rightmove)
3. **Selenium Process**: Load page → Execute JavaScript → Scroll to load more properties → Extract property links
4. **Individual Property Visits**: For each property → Visit property page → Extract accurate price → Calculate per-person cost
5. Filter properties by per-person price limits and check against SQLite database for duplicates
6. Send rich Telegram notifications with per-person pricing for new properties
7. Store seen properties in database with auto-cleanup (30+ days)

### Modern Scraping Capabilities (v2.0)
- **JavaScript Execution**: Full Chrome browser automation for modern property sites
- **Dynamic Content Loading**: Handles infinite scroll and lazy-loaded content
- **Anti-Bot Resilience**: Headless browser with realistic user agents and timing delays  
- **Comprehensive Property Data**: Title, location, price, bedrooms, descriptions, images
- **Accurate Pricing**: Visits individual property pages for exact rent amounts (not search page estimates)

### Environment Requirements
- `TELEGRAM_BOT_TOKEN`: Telegram bot API token
- `GOOGLE_SHEETS_CREDENTIALS_JSON`: Base64 encoded service account credentials (optional for public sheets)
- `GOOGLE_SHEETS_URL`: URL to Google Sheets configuration (can also be passed as CLI arg)

### Google Sheets Configuration Format
Required columns: url, site, telegram_chat_ids, max_price_pp, active, description
- `site`: Must be 'openrent' or 'rightmove' (Rightmove uses advanced Selenium scraping)
- `telegram_chat_ids`: Comma-separated chat IDs for notifications
- `max_price_pp`: **Maximum price per person per month** (total rent ÷ bedrooms)
- `active`: true/false to enable/disable searches
- `description`: Human-readable search description

**Per-Person Price Logic**: If a 3-bedroom property costs £3000/month → price per person = £1000/month

### Database Schema
SQLite database (`/app/data/properties.db`) stores:
- Property URL (UNIQUE constraint prevents duplicates)
- Title, calculated per-person price, location, bedroom count
- Config ID (links to specific search configuration)  
- Timestamp (for cleanup of properties >30 days)
- **GitHub Actions**: Database persisted as artifacts between scheduled runs

### Docker Setup
- **Production**: `property-scraper` service with Chrome/Chromium + ChromeDriver
- **Development**: `property-scraper-dev` service with volume mounts for live code updates
- **Base Image**: Python 3.11 + Chrome/Chromium + ChromeDriver for Selenium
- **Dev Container**: VS Code devcontainer configuration available in `.devcontainer/`
- **Headless Browser**: Full Chrome automation for JavaScript-heavy property sites

### Performance Characteristics
- **Runtime**: 3-5 minutes per search (due to individual property page visits)
- **Properties Found**: 20+ per search (vs 5 without scrolling)
- **Rate Limiting**: Max 15 properties processed per search to prevent site overload
- **Memory Requirements**: ~2GB recommended for Chrome processes
- **Network**: Multiple HTTP requests per property (search page + individual property pages)