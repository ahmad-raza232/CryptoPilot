from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Trade, WalletSnapshot, TradingPair, BotSettings, BotLog
from .tasks import run_trading_bot
from .bot.trading_bot import TradingBot
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

def dashboard(request):
    # Get bot settings
    bot_settings = BotSettings.objects.first()
    if not bot_settings:
        bot_settings = BotSettings.objects.create()
    
    # Get recent trades
    recent_trades = Trade.objects.all()[:10]
    
    # Calculate ROI for each trade
    for trade in recent_trades:
        if trade.entry_price and float(trade.entry_price) > 0:
            trade.roi = (float(trade.pnl or 0) / float(trade.entry_price)) * 100
        else:
            trade.roi = 0
    
    # Get or create wallet snapshot
    bot = TradingBot()
    balance = bot.get_wallet_balance()
    latest_snapshot = WalletSnapshot.objects.first()
    
    # Get daily PnL data for chart
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_pnl = WalletSnapshot.objects.filter(
        timestamp__gte=seven_days_ago
    ).values('timestamp__date').annotate(
        total_pnl=Sum('daily_pnl')
    ).order_by('timestamp__date')
    
    # Get top trading pairs by volume
    top_pairs = TradingPair.objects.all()[:5]
    
    context = {
        'bot_settings': bot_settings,
        'recent_trades': recent_trades,
        'wallet_snapshot': latest_snapshot,
        'daily_pnl': list(daily_pnl),
        'top_pairs': top_pairs,
    }
    
    return render(request, 'trading/dashboard.html', context)

@csrf_exempt
def toggle_bot(request):
    if request.method == 'POST':
        bot_settings = BotSettings.objects.first()
        if not bot_settings:
            bot_settings = BotSettings.objects.create()
        
        # Toggle bot status
        bot_settings.is_running = not bot_settings.is_running
        bot_settings.save()
        
        if bot_settings.is_running:
            # Start the bot
            run_trading_bot.delay()
            message = "Bot started successfully"
        else:
            message = "Bot stopped successfully"
        
        return JsonResponse({
            'status': 'success',
            'message': message,
            'is_running': bot_settings.is_running
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def update_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bot_settings = BotSettings.objects.first()
            if not bot_settings:
                bot_settings = BotSettings.objects.create()
            
            # Update settings
            bot_settings.trading_mode = data.get('trading_mode', bot_settings.trading_mode)
            bot_settings.max_daily_loss = Decimal(str(data.get('max_daily_loss', bot_settings.max_daily_loss)))
            bot_settings.position_size = Decimal(str(data.get('position_size', bot_settings.position_size)))
            bot_settings.stop_loss_pct = Decimal(str(data.get('stop_loss_pct', bot_settings.stop_loss_pct)))
            bot_settings.take_profit_pct = Decimal(str(data.get('take_profit_pct', bot_settings.take_profit_pct)))
            bot_settings.min_volume = Decimal(str(data.get('min_volume', bot_settings.min_volume)))
            bot_settings.min_price_change = Decimal(str(data.get('min_price_change', bot_settings.min_price_change)))
            bot_settings.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Settings updated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def get_trade_history(request):
    trades = Trade.objects.all()[:50]  # Get last 50 trades
    trade_data = []
    
    for trade in trades:
        trade_data.append({
            'symbol': trade.symbol,
            'side': trade.side,
            'quantity': float(trade.quantity),
            'entry_price': float(trade.entry_price),
            'exit_price': float(trade.exit_price) if trade.exit_price else None,
            'pnl': float(trade.pnl) if trade.pnl else None,
            'status': trade.status,
            'entry_time': trade.entry_time.isoformat(),
            'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
        })
    
    return JsonResponse({'trades': trade_data})

@csrf_exempt
def get_wallet_balance(request):
    bot = TradingBot()
    balance = bot.get_wallet_balance()
    
    return JsonResponse({'balance': balance})

@login_required
def get_microcap_opportunities(request):
    """Get microcap trading opportunities."""
    try:
        # Get bot instance
        bot = TradingBot()
        
        # Get new listings and opportunities
        opportunities = bot.scan_new_listings()
        
        # Format the data for frontend
        formatted_opportunities = []
        for opp in opportunities:
            formatted_opportunities.append({
                'symbol': opp['symbol'],
                'price': float(opp['price']),
                'volume_24h': float(opp['volume_24h']),
                'price_change': float(opp['price_change']),
                'is_new': opp['is_new'],
                'first_trade_time': opp['first_trade_time'],
                'spread': float(opp['spread']),
                'volatility': float(opp['volatility']),
                'low_24h': float(opp['low_24h']),
                'high_24h': float(opp['high_24h']),
                'bid_price': float(opp['bid_price']),
                'ask_price': float(opp['ask_price']),
                'volume_change_24h': float(opp['volume_change_24h']),
                'market_cap': float(opp['market_cap']) if 'market_cap' in opp else None,
                'rank': opp['rank'] if 'rank' in opp else None,
            })
        
        return JsonResponse({
            'status': 'success',
            'opportunities': formatted_opportunities
        })
    except Exception as e:
        logger.error(f"Error getting microcap opportunities: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
def simulate_trade(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bot = TradingBot()
            
            # Create a simulated trade
            trade = Trade.objects.create(
                symbol=data['symbol'],
                side=data['side'],
                quantity=Decimal(str(data['quantity'])),
                entry_price=Decimal(str(data['price'])),
                status='CLOSED' if data['side'] == 'SELL' else 'OPEN',
                entry_time=timezone.now()
            )
            
            if data['side'] == 'SELL':
                trade.exit_price = Decimal(str(data['price']))
                trade.exit_time = timezone.now()
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                trade.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Trade simulated successfully',
                'trade_id': trade.id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def force_buy(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bot = TradingBot()
            
            # Execute force buy
            result = bot.execute_trade(
                symbol=data['symbol'],
                side='BUY',
                amount=Decimal(str(data['amount']))
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Force buy executed successfully',
                'trade_id': result.get('trade_id')
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def close_trade(request, trade_id):
    if request.method == 'POST':
        try:
            trade = Trade.objects.get(id=trade_id, status='OPEN')
            bot = TradingBot()
            
            # Get current price
            current_price = bot.get_current_price(trade.symbol)
            
            # Update trade
            trade.exit_price = Decimal(str(current_price))
            trade.exit_time = timezone.now()
            trade.status = 'CLOSED'
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            trade.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Trade closed successfully'
            })
        except Trade.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Trade not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
def bot_status(request):
    """Get current bot status."""
    try:
        settings = BotSettings.objects.first()
        if not settings:
            settings = BotSettings.objects.create()
        
        return JsonResponse({
            'status': 'success',
            'is_running': settings.is_running,
            'trading_mode': settings.trading_mode,
            'last_update': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
def get_logs(request):
    logs = BotLog.objects.all()[:100]
    return JsonResponse({
        'logs': [
            {
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': log.level,
                'message': log.message
            } for log in logs
        ]
    })
