from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def calculate_roi(pnl, entry_price):
    """Calculate ROI percentage"""
    try:
        if not entry_price or float(entry_price) == 0:
            return 0
        return (float(pnl) / float(entry_price)) * 100
    except (ValueError, TypeError):
        return 0 