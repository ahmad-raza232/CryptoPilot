from django.db import models
from django.utils import timezone

class Trade(models.Model):
    SIDE_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    symbol = models.CharField(max_length=20)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    entry_price = models.DecimalField(max_digits=18, decimal_places=8)
    exit_price = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    pnl = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=18, decimal_places=8)
    take_profit = models.DecimalField(max_digits=18, decimal_places=8)
    
    def __str__(self):
        return f"{self.side} {self.symbol} @ {self.entry_price}"
    
    class Meta:
        ordering = ['-entry_time']

class WalletSnapshot(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    total_balance_usdt = models.DecimalField(max_digits=18, decimal_places=8)
    daily_pnl = models.DecimalField(max_digits=18, decimal_places=8)
    
    def __str__(self):
        return f"Balance: {self.total_balance_usdt} USDT @ {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

class TradingPair(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    base_asset = models.CharField(max_length=10)
    quote_asset = models.CharField(max_length=10)
    min_qty = models.DecimalField(max_digits=18, decimal_places=8)
    price_precision = models.IntegerField()
    qty_precision = models.IntegerField()
    last_price = models.DecimalField(max_digits=18, decimal_places=8)
    volume_24h = models.DecimalField(max_digits=24, decimal_places=8)
    price_change_24h = models.DecimalField(max_digits=8, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.symbol} @ {self.last_price}"
    
    class Meta:
        ordering = ['-volume_24h']

class BotSettings(models.Model):
    is_running = models.BooleanField(default=False)
    trading_mode = models.CharField(max_length=10, default='paper')
    max_daily_loss = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    position_size = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    stop_loss_pct = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    take_profit_pct = models.DecimalField(max_digits=5, decimal_places=2, default=4.00)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bot Settings (Mode: {self.trading_mode})"
    
    class Meta:
        verbose_name_plural = "Bot Settings"

class BotLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('DEBUG', 'Debug'),
    ]
    
    timestamp = models.DateTimeField(default=timezone.now)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    
    def __str__(self):
        return f"[{self.level}] {self.timestamp}: {self.message[:50]}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Bot Log"
        verbose_name_plural = "Bot Logs"
