from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('toggle-bot/', views.toggle_bot, name='toggle_bot'),
    path('update-settings/', views.update_settings, name='update_settings'),
    path('trade-history/', views.get_trade_history, name='trade_history'),
    path('wallet-balance/', views.get_wallet_balance, name='wallet_balance'),
    path('microcap-opportunities/', views.get_microcap_opportunities, name='microcap_opportunities'),
    path('simulate-trade/', views.simulate_trade, name='simulate_trade'),
    path('force-buy/', views.force_buy, name='force_buy'),
    path('close-trade/<int:trade_id>/', views.close_trade, name='close_trade'),
    path('bot-status/', views.bot_status, name='bot_status'),
    path('logs/', views.get_logs, name='get_logs'),
] 