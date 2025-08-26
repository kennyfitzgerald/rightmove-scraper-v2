# Property Scraper Bot

A powerful, production-ready bot that scrapes property listings from OpenRent and Rightmove using modern web scraping techniques, with intelligent price-per-person calculations and Telegram notifications.

## ✨ Features

- 🏠 **Advanced Property Scraping**: Uses Selenium for JavaScript-rendered modern property sites
- 🔄 **Infinite Scroll Support**: Automatically scrolls to load additional property listings
- 💰 **Smart Price Calculations**: Calculates price per person (total rent ÷ bedrooms)
- 🎯 **Intelligent Filtering**: Filters properties by price per person limits
- 📊 **Google Sheets Integration**: Reads search configurations from public or private sheets
- 📱 **Rich Telegram Notifications**: Sends formatted property details with working links
- 🗄️ **SQLite Database**: Tracks seen properties to prevent duplicates with auto-cleanup
- ⏰ **Flexible Scheduling**: Runs every 30 minutes via GitHub Actions or on-demand
- 🐳 **Fully Dockerized**: Easy deployment with Chrome/Chromium headless browser
- 🔧 **Dev Container Support**: Complete VS Code development environment
- 🌐 **Individual Page Visits**: Visits each property page for accurate price extraction

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_SHEETS_CREDENTIALS_JSON=your_base64_encoded_credentials_here
GOOGLE_SHEETS_URL=your_google_sheets_url_here
```

⚠️ **Security Note:** Never commit `.env` files to git. The `.gitignore` file already excludes these files.

#### Getting Telegram Bot Token
1. Message @BotFather on Telegram
2. Use `/newbot` command and follow instructions
3. Copy the bot token

#### Getting Google Sheets Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create service account credentials
5. Download JSON credentials file
6. Base64 encode the JSON: `cat credentials.json | base64 -w 0`

### 2. Google Sheets Setup

**For Public Sheets (Easiest):**
1. Make your Google Sheet public (Share → Anyone with the link can view)
2. Just use the sheet URL in `GOOGLE_SHEETS_URL` environment variable
3. No credentials needed!

**For Private Sheets:**
1. Set up Google Sheets API credentials (see original instructions below)
2. Add `GOOGLE_SHEETS_CREDENTIALS_JSON` environment variable

**Required Columns:**
- `url` - Property search URL from Rightmove or OpenRent
- `site` - Either 'openrent' or 'rightmove' 
- `telegram_chat_ids` - Comma-separated chat IDs for notifications
- `max_price_pp` - Maximum price **per person per month** (total rent will be divided by bedrooms)
- `active` - true/false to enable/disable this search
- `description` - Human-readable description for notifications

**💡 Price Per Person Logic:**
- If a 3-bedroom property costs £3000/month, price per person = £1000/month
- Set `max_price_pp` to your budget per person (e.g., 1000 for £1000 pp/pcm limit)

Example: [Sample Google Sheet](https://docs.google.com/spreadsheets/d/1PVl4iOOuNSwYjAHw1YYOjd9C0LXyH7kcI1ugmXOpp1I/edit?gid=0#gid=0)

### 3. Telegram Chat IDs

To get your chat ID:
1. Message your bot or add it to a group
2. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for the `chat` → `id` field

## Local Development

### Using Dev Container (Recommended)
1. Open in VS Code
2. Install Dev Containers extension
3. Press F1 → "Dev Containers: Reopen in Container"

### Using Docker Compose
```bash
# Test configuration
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --test-config --sheets-url "your_sheets_url"

# Run once in test mode
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --run-once --test-mode --sheets-url "your_sheets_url"

# Run once for real
docker-compose --profile dev run --rm property-scraper-dev python src/main.py --run-once --sheets-url "your_sheets_url"
```

## 🚀 GitHub Actions Deployment

### Setup
1. **Add Repository Secrets:**
   - `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
   - `GOOGLE_SHEETS_CREDENTIALS_JSON` - Base64 encoded service account JSON (optional for public sheets)
   - `GOOGLE_SHEETS_URL` - Your Google Sheets configuration URL

### Automated Operation
- **Scheduled Runs:** Every 30 minutes automatically
- **Manual Runs:** Actions → Property Scraper → Run workflow
- **Docker-Based:** Uses full Selenium + Chrome setup for reliable scraping

### 🗄️ Database Persistence
The workflow automatically handles database persistence:
1. **Downloads** previous database from GitHub artifacts (if exists)
2. **Runs** scraper with existing seen properties to avoid duplicates
3. **Uploads** updated database for next run (30-day retention)
4. **Prevents** sending duplicate property notifications

**First Run:** Database starts empty, all matching properties sent as notifications  
**Subsequent Runs:** Only new properties (not in database) trigger notifications

### Monitoring
- **Build Logs:** Check Actions tab for detailed scraping logs
- **Artifacts:** Download database and log files from completed runs
- **Errors:** Failed runs will show in Actions tab with error details
- **Database Size:** Check artifacts to monitor database growth over time

### GitHub Actions Debugging
If the workflow fails:

1. **Check the specific failing step** in Actions tab
2. **Common failure points:**
   - Docker build (Chrome installation issues)
   - Database download (first run will skip this step)
   - Scraper execution (memory limits, timeouts)
   - Artifact upload (permissions, size limits)

3. **Memory issues:** GitHub runners have 7GB RAM, but Chrome can be memory-intensive
4. **Timeout issues:** Individual property visits can take 3-5 minutes total
5. **Network issues:** Property sites may block GitHub IP ranges

## Commands

```bash
# Test configuration only
python src/main.py --test-config --sheets-url "your_url"

# Run once (no scheduling)
python src/main.py --run-once --sheets-url "your_url"

# Run once in test mode (prints to console instead of Telegram)
python src/main.py --run-once --test-mode --sheets-url "your_url"

# Run with scheduling (production mode)
python src/main.py --sheets-url "your_url"

# Clear database (for testing - will re-send all notifications)
rm -f ./data/properties.db
```

## 🗄️ Storage & Performance

**SQLite Database:**
- **Location**: `/app/data/properties.db` 
- **Stores**: Property URLs, titles, calculated per-person prices, locations, bedroom counts
- **Deduplication**: Prevents duplicate notifications using URL-based tracking
- **Auto-cleanup**: Removes properties older than 30 days to keep database size manageable

**Performance Optimizations:**
- **Selenium WebDriver**: Handles modern JavaScript-rendered property sites
- **Infinite Scroll**: Loads 20+ properties per search (vs 5 without scrolling)
- **Rate Limiting**: Processes max 15 properties per search to avoid overwhelming sites
- **Individual Page Visits**: Visits each property page for accurate price extraction
- **Headless Browser**: Runs Chrome/Chromium in headless mode for efficiency

## 📱 Notification Format

When properties matching your criteria are found, you'll receive rich Telegram notifications like:

```
🏠 New Property: Your Search Name

📍 Title: Windsor Street, Islington, London, N1
💰 Price: £1000 pp/pcm (£3000 total/3br)
📌 Location: Windsor Street, Islington, London, N1

🔗 View Property (clickable link to Rightmove/OpenRent)
```

**Test Mode**: Add `--test-mode` to print notifications to console instead of sending to Telegram.

## 🏗️ Architecture

```
src/
├── main.py              # Main application with CLI interface
├── scrapers/
│   ├── base.py         # Abstract base scraper with price filtering
│   ├── openrent.py     # OpenRent scraper (basic HTTP)
│   └── rightmove.py    # Rightmove scraper (Selenium + scrolling)
├── config/
│   └── sheets.py       # Google Sheets configuration reader
├── storage/
│   └── database.py     # SQLite database with auto-cleanup
└── notifications/
    └── telegram.py     # Rich Telegram message formatting
```

**Docker Setup:**
- **Base Image**: Python 3.11 with Chrome/Chromium and ChromeDriver
- **Volumes**: Persistent data storage in `/app/data/`
- **Networks**: Isolated container networking

## 🔧 Troubleshooting

### Common Issues

1. **Chrome/Selenium Issues**: 
   - Ensure Docker has enough memory (recommend 2GB+)
   - Check Chrome processes aren't hanging: `docker system prune`
   - ChromeDriver version conflicts: Rebuild Docker image with `--no-cache`

2. **No Properties Found**:
   - Verify search URLs work manually in browser
   - Check if Rightmove changed their HTML structure
   - Individual property pages may be loading slowly (increase timeouts)

3. **Price Extraction Failures**:
   - Properties show "Price not found" → Website structure may have changed
   - Check individual property page loads correctly
   - Regex patterns may need updating for different price formats

4. **Performance Issues**:
   - Scraping takes 3-5 minutes due to individual page visits
   - Reduce properties processed by lowering `max_properties_to_extract` limit
   - Consider running less frequently if hitting rate limits

5. **Memory Issues**:
   - Chrome processes can consume significant RAM
   - Monitor with `docker stats` during execution
   - Restart containers if memory usage is high

6. **Legacy Issues**:
   - **Import errors in IDE**: Install dependencies or use dev container
   - **Telegram bot not working**: Check token and chat IDs  
   - **Google Sheets access**: Verify service account has access to sheet

### 📋 Logs & Debugging

**Log Locations:**
- **Local Development**: `./data/scraper.log`
- **Docker Container**: Check with `docker-compose logs`
- **GitHub Actions**: Download artifacts from workflow runs

**Debug Mode:**
- Add `--test-mode` flag to see detailed console output without sending Telegram messages
- Individual property page visits are logged with extracted prices
- Scroll progress shows number of properties loaded at each step

**Monitoring:**
- Each run shows summary: "Found X properties for 'search name'"
- Price filtering logs show which properties pass/fail budget limits
- Database cleanup reports how many old records were removed

---

## 🚀 Recent Major Improvements

**v2.0 - Selenium & Modern Web Scraping (2024)**
- ✅ **Selenium Integration**: Handles JavaScript-rendered modern property websites
- ✅ **Infinite Scroll Support**: Automatically loads additional properties (20+ vs 5 previously)
- ✅ **Individual Property Page Visits**: Visits each property for accurate price extraction  
- ✅ **Per-Person Price Calculation**: Divides total rent by bedroom count automatically
- ✅ **Enhanced Price Filtering**: Smart filtering by price per person with detailed logging
- ✅ **Chrome/Chromium Integration**: Full headless browser support in Docker
- ✅ **Rate Limiting**: Prevents overwhelming property sites with configurable limits
- ✅ **Rich Telegram Notifications**: Improved message formatting with per-person pricing

**Performance Impact:**
- **Before**: Found ~5 properties per search, basic HTTP scraping
- **After**: Finds 20+ properties per search with accurate pricing, full JavaScript support
- **Runtime**: 3-5 minutes per search (due to individual page visits for price accuracy)

This scraper now works reliably with modern property websites and provides accurate, actionable property information with per-person pricing calculations.