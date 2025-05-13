from celery import shared_task
from .bot.trading_bot import TradingBot
from .models import BotSettings, WalletSnapshot, Trade
from datetime import datetime, timedelta
from django.utils import timezone
import logging
import time

logger = logging.getLogger(__name__)

@shared_task
def run_trading_bot():
    """Main trading bot task that runs continuously."""
    try:
        # Get bot settings
        settings = BotSettings.objects.first()
        if not settings or not settings.is_running:
            logger.info("Bot is not running or settings not found")
            return

        # Initialize bot
        bot = TradingBot()
        logger.info("Trading bot started")

        while settings.is_running:
            try:
                # Scan for new opportunities
                opportunities = bot.scan_new_listings()
                logger.info(f"Found {len(opportunities)} new opportunities")

                # Check active trades
                active_trades = Trade.objects.filter(status='OPEN')
                for trade in active_trades:
                    # Check stop loss and take profit
                    current_price = bot.get_current_price(trade.symbol)
                    if current_price:
                        if current_price <= float(trade.stop_loss):
                            bot.execute_trade(trade.symbol, 'SELL', float(trade.quantity))
                            logger.info(f"Stop loss triggered for {trade.symbol}")
                        elif current_price >= float(trade.take_profit):
                            bot.execute_trade(trade.symbol, 'SELL', float(trade.quantity))
                            logger.info(f"Take profit triggered for {trade.symbol}")

                # Update wallet snapshot
                balance = bot.get_wallet_balance()
                WalletSnapshot.objects.create(
                    total_balance_usdt=balance,
                    daily_pnl=bot.daily_pnl
                )

                # Sleep for 5 seconds before next iteration
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                time.sleep(5)  # Wait before retrying

    except Exception as e:
        logger.error(f"Fatal error in trading bot: {str(e)}")
        settings.is_running = False
        settings.save()

@shared_task
def daily_summary():
    """Generate daily trading summary."""
    try:
        # Get today's trades
        today = timezone.now().date()
        trades = Trade.objects.filter(
            entry_time__date=today
        )

        # Calculate daily PnL
        daily_pnl = sum(float(trade.pnl or 0) for trade in trades)

        # Get active trades
        active_trades = trades.filter(status='OPEN')

        # Get bot settings
        settings = BotSettings.objects.first()
        trading_mode = settings.trading_mode if settings else 'paper'

        # Prepare summary message
        summary = f"""
📊 Daily Trading Summary ({today})

💰 Balance: ${settings.total_balance_usdt:.2f}
📈 Daily PnL: ${daily_pnl:.2f}
🔄 Active Trades: {active_trades.count()}
🤖 Trading Mode: {trading_mode}
📝 Total Trades: {trades.count()}
        """

        # Send summary via Telegram
        bot = TradingBot()
        bot.send_telegram_alert(summary)

    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}") 