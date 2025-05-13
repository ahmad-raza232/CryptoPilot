import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.trend import MACD
import telegram
from datetime import datetime, timedelta
import os
from trading.models import WalletSnapshot, Trade, TradingPair, BotLog
from decimal import Decimal

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, api_key=None, api_secret=None, telegram_token=None, telegram_chat_id=None):
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        self.client = Client(self.api_key, self.api_secret)

        # Telegram settings
        self.telegram_bot = telegram.Bot(token=telegram_token or "7370945412:AAFSf2Qt6R35pncrfG2_IIblZIlEtV8Uj8E")
        self.telegram_chat_id = telegram_chat_id or "6573232846"

        # Trading parameters
        self.trading_mode = os.getenv('TRADING_MODE', 'paper')
        self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', 50))
        self.position_size = float(os.getenv('POSITION_SIZE', 100))
        self.stop_loss_pct = float(os.getenv('DEFAULT_STOP_LOSS', 2))
        self.take_profit_pct = float(os.getenv('DEFAULT_TAKE_PROFIT', 4))

        self.active_trades = {}
        self.daily_pnl = 0
        self.is_running = False
        self.watchlist = set()

    def log_bot_action(self, message, level='INFO'):
        try:
            BotLog.objects.create(message=message, level=level)
        except Exception as e:
            logger.error(f"Failed to log bot action: {e}")

    def send_telegram_alert(self, message):
        self.log_bot_action(f"[TELEGRAM] {message}", level='INFO')
        if self.telegram_bot and self.telegram_chat_id:
            try:
                self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
                self.log_bot_action(f"Failed to send Telegram alert: {e}", level='ERROR')

    def get_technical_indicators(self, symbol, interval='1h', limit=100):
        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])

        df['rsi'] = RSIIndicator(close=df['close']).rsi()
        df['ema20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
        macd = MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        return df

    def get_wallet_balance(self):
        """Get current wallet balance from Binance."""
        try:
            account = self.client.get_account()
            for asset in account['balances']:
                if asset['asset'] == 'USDT':
                    free_balance = float(asset['free'])
                    locked_balance = float(asset['locked'])
                    total_balance = free_balance + locked_balance
                    self.log_bot_action(f"USDT Balance - Free: {free_balance}, Locked: {locked_balance}, Total: {total_balance}")
                    return total_balance
            self.log_bot_action("No USDT balance found in account", level='WARNING')
            return 0.0
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            self.log_bot_action(f"Error getting wallet balance: {str(e)}", level='ERROR')
            return 0.0

    def scan_new_listings(self):
        self.log_bot_action("Scanning Binance for new listings...")
        try:
            # Get all USDT pairs
            exchange_info = self.client.get_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols'] if s['quoteAsset'] == 'USDT']
            
            new_opportunities = []
            for symbol in symbols:
                try:
                    # Get ticker information
                    ticker = self.client.get_ticker(symbol=symbol)
                    price = float(ticker['lastPrice'])
                    volume_24h = float(ticker['volume']) * price
                    price_change = float(ticker['priceChangePercent'])
                    
                    # Get recent trades to check if it's a new listing
                    trades = self.client.get_recent_trades(symbol=symbol, limit=1)
                    first_trade_time = datetime.fromtimestamp(trades[0]['time'] / 1000)
                    is_new = (datetime.now() - first_trade_time) < timedelta(hours=24)
                    
                    # Get additional market data
                    depth = self.client.get_order_book(symbol=symbol, limit=5)
                    bid_price = float(depth['bids'][0][0])
                    ask_price = float(depth['asks'][0][0])
                    spread = ((ask_price - bid_price) / bid_price) * 100
                    
                    # Get 24h price statistics
                    stats = self.client.get_ticker(symbol=symbol)
                    high_24h = float(stats['highPrice'])
                    low_24h = float(stats['lowPrice'])
                    
                    # Calculate volatility
                    volatility = ((high_24h - low_24h) / low_24h) * 100
                    
                    # Check if it meets our criteria
                    if (price <= 0.01 and volume_24h > 100000) or is_new:
                        new_opportunities.append({
                            'symbol': symbol,
                            'price': price,
                            'volume_24h': volume_24h,
                            'price_change': price_change,
                            'is_new': is_new,
                            'spread': spread,
                            'volatility': volatility,
                            'high_24h': high_24h,
                            'low_24h': low_24h,
                            'first_trade_time': first_trade_time.isoformat(),
                            'bid_price': bid_price,
                            'ask_price': ask_price
                        })
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Sort by volume and newness
            self.log_bot_action(f"Found {len(new_opportunities)} new opportunities.")
            return sorted(new_opportunities, 
                         key=lambda x: (x['is_new'], x['volume_24h']), 
                         reverse=True)
        except Exception as e:
            logger.error(f"Error scanning new listings: {e}")
            self.log_bot_action(f"Error scanning new listings: {e}", level='ERROR')
            return []

    def execute_trade(self, symbol, side, quantity):
        self.log_bot_action(f"Executing trade: {side} {quantity} {symbol}")
        try:
            if self.trading_mode == 'paper':
                current_price = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
                trade_id = f"paper_{datetime.now().timestamp()}"
                
                # Create trade record
                trade = Trade.objects.create(
                    symbol=symbol,
                    side=side,
                    quantity=Decimal(str(quantity)),
                    entry_price=Decimal(str(current_price)),
                    status='OPEN',
                    stop_loss=Decimal(str(current_price * (1 - self.stop_loss_pct/100))),
                    take_profit=Decimal(str(current_price * (1 + self.take_profit_pct/100)))
                )
                
                if side == 'BUY':
                    self.active_trades[trade_id] = {
                        'symbol': symbol,
                        'entry_price': current_price,
                        'quantity': quantity,
                        'side': side,
                        'timestamp': datetime.now(),
                        'trade_id': trade.id
                    }
                    
                    # Send notification
                    self.send_telegram_alert(
                        f"🟢 Paper Trade Executed\n"
                        f"Symbol: {symbol}\n"
                        f"Side: {side}\n"
                        f"Price: ${current_price:.8f}\n"
                        f"Quantity: {quantity:.2f}"
                    )
                
                self.log_bot_action(f"Trade executed: {side} {quantity} {symbol}")
                return {
                    'orderId': trade_id,
                    'status': 'FILLED',
                    'price': current_price,
                    'trade_id': trade.id
                }
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
                
                # Create trade record
                trade = Trade.objects.create(
                    symbol=symbol,
                    side=side,
                    quantity=Decimal(str(quantity)),
                    entry_price=Decimal(str(float(order['fills'][0]['price']))),
                    status='OPEN',
                    stop_loss=Decimal(str(float(order['fills'][0]['price']) * (1 - self.stop_loss_pct/100))),
                    take_profit=Decimal(str(float(order['fills'][0]['price']) * (1 + self.take_profit_pct/100)))
                )
                
                # Send notification
                self.send_telegram_alert(
                    f"🟢 Live Trade Executed\n"
                    f"Symbol: {symbol}\n"
                    f"Side: {side}\n"
                    f"Price: ${float(order['fills'][0]['price']):.8f}\n"
                    f"Quantity: {quantity:.2f}"
                )
                
                self.log_bot_action(f"Trade executed: {side} {quantity} {symbol}")
                return {
                    'orderId': order['orderId'],
                    'status': order['status'],
                    'price': float(order['fills'][0]['price']),
                    'trade_id': trade.id
                }
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self.send_telegram_alert(f"❌ Trade Error: {str(e)}")
            self.log_bot_action(f"Trade error: {str(e)}", level='ERROR')
            return None

    def check_trade_conditions(self, symbol):
        try:
            df = self.get_technical_indicators(symbol)
            current_rsi = df['rsi'].iloc[-1]
            current_price = float(df['close'].iloc[-1])
            current_ema = df['ema20'].iloc[-1]
            macd_line = df['macd'].iloc[-1]
            signal_line = df['macd_signal'].iloc[-1]
            
            # Get 24h price change
            ticker = self.client.get_ticker(symbol=symbol)
            price_change = float(ticker['priceChangePercent'])
            
            # Check if price is rising and volume is increasing
            volume_increasing = float(ticker['volume']) > float(ticker['quoteVolume']) * 1.5
            
            return {
                'should_buy': (
                    current_rsi < 30 and
                    current_price > current_ema and
                    macd_line > signal_line and
                    price_change > 5 and
                    volume_increasing
                ),
                'should_sell': (
                    current_rsi > 70 or
                    current_price < current_ema or
                    macd_line < signal_line
                ),
                'current_price': current_price,
                'indicators': {
                    'rsi': current_rsi,
                    'ema': current_ema,
                    'macd': macd_line,
                    'signal': signal_line,
                    'price_change': price_change
                }
            }
        except Exception as e:
            logger.error(f"Error checking trade conditions: {e}")
            self.log_bot_action(f"Error checking trade conditions: {e}", level='ERROR')
            return None

    def start_trading(self):
        self.is_running = True
        self.log_bot_action("Trading bot started.")
        self.send_telegram_alert("🤖 Trading Bot Started")
        
        # Initial scan for opportunities
        opportunities = self.scan_new_listings()
        for opp in opportunities[:3]:  # Check top 3 opportunities
            if opp['symbol'] not in self.watchlist:
                self.watchlist.add(opp['symbol'])
                self.send_telegram_alert(
                    f"🔍 New Opportunity Found\n"
                    f"Symbol: {opp['symbol']}\n"
                    f"Price: ${opp['price']:.8f}\n"
                    f"24h Change: {opp['price_change']}%\n"
                    f"Volume: ${opp['volume_24h']/1000000:.2f}M"
                )

    def stop_trading(self):
        self.is_running = False
        self.log_bot_action("Trading bot stopped.")
        self.send_telegram_alert("🛑 Trading Bot Stopped")
