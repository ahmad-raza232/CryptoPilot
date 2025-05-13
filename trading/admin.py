from django.contrib import admin
from .models import Trade, WalletSnapshot, TradingPair, BotSettings

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'side', 'quantity', 'entry_price', 'exit_price', 'pnl', 'status', 'entry_time')
    list_filter = ('symbol', 'side', 'status')
    search_fields = ('symbol',)
    ordering = ('-entry_time',)

@admin.register(WalletSnapshot)
class WalletSnapshotAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'total_balance_usdt', 'daily_pnl')
    ordering = ('-timestamp',)

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'base_asset', 'quote_asset', 'last_price', 'volume_24h', 'price_change_24h')
    list_filter = ('quote_asset',)
    search_fields = ('symbol', 'base_asset')
    ordering = ('-volume_24h',)

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('trading_mode', 'is_running', 'max_daily_loss', 'position_size', 'stop_loss_pct', 'take_profit_pct')
    
    def has_add_permission(self, request):
        # Only allow one BotSettings instance
        if self.model.objects.exists():
            return False
        return True
