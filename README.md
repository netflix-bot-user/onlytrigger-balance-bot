# Premium Point Bot

A Telegram bot for automated account loading with key-based redemption system.

## Features

### Key System
- Generate redemption keys with specific target balances
- Keys are unique and can only be used once
- Track key usage and analytics

### Account Stock Management
- Upload accounts via file or text
- Automatic account processing
- Track account status (available, processing, loaded, failed)

### Instant Delivery
- Partial loads are saved for instant delivery
- Accounts that don't reach target are stored for lower-tier keys
- Configurable matching range

### Analytics
- Per-account load time tracking
- Success/failure rates
- Daily statistics
- Balance distribution

### Admin Panel
- Full inline keyboard interface
- Generate and manage keys
- View and manage stock
- Configure bot settings
- View analytics

## Installation

### Prerequisites
- Python 3.10+
- MongoDB 4.4+
- Telegram Bot Token (from @BotFather)

### Setup

1. **Clone the repository**
```bash
cd PremiumPointProject
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
copy .env.example .env
# Edit .env with your settings
```

5. **Start MongoDB**
```bash
# Make sure MongoDB is running on localhost:27017
# Or update MONGO_URI in .env
```

6. **Run the bot**
```bash
python -m bot.main
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | Required |
| `MONGO_URI` | MongoDB connection URI | `mongodb://localhost:27017` |
| `MONGO_DB_NAME` | Database name | `premium_point_bot` |
| `ADMIN_IDS` | Comma-separated admin user IDs | Required |
| `KEY_PREFIX` | Prefix for generated keys | `PREM` |

### Bot Settings (via /settings)

| Setting | Description | Default |
|---------|-------------|---------|
| Load Per Round | Amount to load per payment | $50 |
| Delay Per Round | Delay between payments (seconds) | 210 |
| Threads | Concurrent loading threads | 10 |
| Proxy | HTTP proxy for requests | None |
| Retry Same Card | Retry failed payments on same card | Yes |
| Halve on Failure | Halve amount on payment failure | No |
| Instant Delivery Range | Range for instant delivery matching | 0 (exact) |

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help message |
| `/redeem <key>` | Redeem a key |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| `/genkey <balance> [count]` | Generate keys |
| `/listkeys` | List all keys |
| `/stock` | View stock status |
| `/addstock` | Add accounts to stock |
| `/settings` | Bot settings |
| `/stats` | View analytics |
| `/instant` | Manage instant delivery |

## Project Structure

```
bot/
├── main.py              # Entry point
├── config.py            # Configuration
│
├── core/                # Framework
│   ├── handler.py       # BaseHandler class
│   ├── registry.py      # Auto-discovery
│   └── permissions.py   # Admin checks
│
├── database/            # MongoDB layer
│   ├── mongo.py         # Connection
│   ├── keys.py          # Keys collection
│   ├── accounts.py      # Stock collection
│   ├── instant.py       # Instant delivery
│   ├── settings.py      # Bot settings
│   └── analytics.py     # Analytics
│
├── handlers/            # Command handlers
│   ├── admin/           # Admin commands
│   │   ├── menu.py
│   │   ├── keys.py
│   │   ├── stock.py
│   │   ├── settings.py
│   │   ├── analytics.py
│   │   └── instant.py
│   ├── user/            # User commands
│   │   ├── start.py
│   │   └── redeem.py
│   └── system/          # System handlers
│       └── errors.py
│
├── loader/              # Loading engine
│   ├── api.py           # API wrapper
│   └── engine.py        # Loading logic
│
└── utils/               # Utilities
    ├── keygen.py        # Key generation
    ├── keyboards.py     # Inline keyboards
    └── formatters.py    # Message formatting
```

## Adding New Handlers

The bot uses an auto-discovery system. To add a new handler:

1. Create a new file in the appropriate `handlers/` subdirectory
2. Create a class extending `BaseHandler`
3. Set the required class attributes
4. Implement `execute()` and optionally `callback()`

Example:
```python
from bot.core import BaseHandler, HandlerCategory, HandlerType

class MyHandler(BaseHandler):
    command = "mycommand"
    description = "My custom command"
    category = HandlerCategory.USER
    handler_type = HandlerType.COMMAND
    admin_only = False
    callback_patterns = ["my_callback_"]
    
    async def execute(self, update, context):
        await update.message.reply_text("Hello!")
    
    async def callback(self, update, context):
        query = update.callback_query
        await query.answer("Callback received!")
```

The handler will be automatically discovered and registered on bot startup.

## Database Collections

### keys
- `key`: Unique key string
- `target_balance`: Target balance for this key
- `status`: active/used/expired
- `created_at`, `created_by`
- `used_at`, `used_by`

### accounts
- `credentials`: Account credentials
- `status`: available/processing/loaded/failed
- `load_started_at`, `load_finished_at`
- `load_duration_seconds`
- `initial_balance`, `final_balance`

### instant_delivery
- `credentials`: Account credentials
- `balance`: Actual loaded balance
- `original_target`: What target was requested
- `used`: Whether delivered

### settings
- Global bot configuration

### analytics
- Event logs for statistics

## License

Private - All rights reserved
