# CryptoPilot - Automated Crypto Trading Bot

CryptoPilot is a professional-grade cryptocurrency trading bot that connects to Binance exchange and performs automated trading with risk management features. The bot includes a web dashboard for monitoring trades and controlling the trading strategy.

## Features

- 🤖 Automated trading on Binance (Spot trading)
- 📊 Technical analysis using multiple indicators (RSI, EMA, MACD)
- 💰 Risk management with position sizing, stop-loss, and take-profit
- 📈 Real-time price monitoring and trade execution
- 🔍 Special microcap coin scanner for finding trending low-price opportunities
- 📱 Telegram notifications for trades and daily summaries
- 🖥️ Web dashboard with live charts and trade history
- 📝 Paper trading mode for testing strategies

## Technology Stack

- Python 3.11+
- Django + Flask for web interface
- Celery for background tasks
- PostgreSQL for data storage
- Redis for task queue
- Docker for containerization

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cryptopilot.git
cd cryptopilot
```

2. Create a `.env` file with your configuration:
```bash
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Database Configuration
DB_NAME=cryptopilot
DB_USER=cryptopilot
DB_PASSWORD=cryptopilot
DB_HOST=db
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Trading Configuration
TRADING_MODE=paper
MAX_DAILY_LOSS=50.0
POSITION_SIZE=100.0
STOP_LOSS_PCT=2.0
TAKE_PROFIT_PCT=4.0
```

3. Build and start the Docker containers:
```bash
docker-compose build
docker-compose up -d
```

4. Run database migrations:
```bash
docker-compose exec web python manage.py migrate
```

5. Create a superuser for admin access:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Access the application:
- Web Dashboard: http://localhost:8000
- Admin Panel: http://localhost:8000/admin

## Usage

1. Log in to the web dashboard
2. Configure your trading parameters in the Settings panel
3. Click "Start Bot" to begin automated trading
4. Monitor your trades and performance in real-time
5. Receive trade notifications via Telegram

## Risk Management Features

- Maximum daily loss limit
- Position sizing based on account balance
- Stop-loss and take-profit orders
- Technical indicator confirmation for trade signals
- Paper trading mode for strategy testing

## Microcap Scanner

The bot includes a special scanner for finding low-price opportunities:
- Scans for coins under $0.01
- Monitors volume spikes and social trends
- Identifies newly listed or trending coins
- Implements risk management for microcap trades

## Monitoring and Alerts

- Real-time trade notifications via Telegram
- Daily performance summaries
- PnL tracking and visualization
- Wallet balance monitoring
- Active trade tracking

## Development

To run the development server:
```bash
docker-compose up
```

To run tests:
```bash
docker-compose exec web python manage.py test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

Trading cryptocurrencies carries a high level of risk and may not be suitable for all investors. The high degree of leverage can work against you as well as for you. Before deciding to trade cryptocurrencies, you should carefully consider your investment objectives, level of experience, and risk appetite. 