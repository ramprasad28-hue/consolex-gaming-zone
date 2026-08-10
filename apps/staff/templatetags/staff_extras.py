"""Custom template filters for the staff panel.

Provides Indian-style digit grouping for rupee amounts used across the
payments / billing / reports UI. Values arrive from the services layer as
Decimals in rupees (converted from paise), so this filter only formats.
"""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _group_indian(whole):
    """Apply Indian digit grouping (###,##,##,###) to a whole-number string."""
    if len(whole) <= 3:
        return whole
    last3 = whole[-3:]
    rest = whole[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


@register.filter
def inr(value, arg=""):
    """Format a rupee amount with Indian grouping.

    Usage: {{ amount|inr }}         -> 12,345
           {{ amount|inr:2 }}       -> 12,345.67
    """
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    places = 2 if str(arg) == "2" else 0
    quant = Decimal("1") if places == 0 else Decimal("0.01")
    value = value.quantize(quant)
    sign = "-" if value < 0 else ""
    text = str(abs(value))
    if "." in text:
        whole, frac = text.split(".", 1)
        return f"{sign}{_group_indian(whole)}.{frac}"
    return f"{sign}{_group_indian(text)}"


@register.filter
def inr_paise(value, arg="2"):
    """Convert a paise amount to rupees and format with Indian grouping.

    Usage: {{ amount_in_paise|inr_paise }}     -> 12,345.67
           {{ amount_in_paise|inr_paise:0 }}   -> 12,346
    """
    try:
        value = Decimal(value) / Decimal(100)
    except (InvalidOperation, TypeError, ValueError):
        return value
    places = 0 if str(arg) == "0" else 2
    quant = Decimal("1") if places == 0 else Decimal("0.01")
    value = value.quantize(quant)
    sign = "-" if value < 0 else ""
    text = str(abs(value))
    if "." in text:
        whole, frac = text.split(".", 1)
        return f"{sign}{_group_indian(whole)}.{frac}"
    return f"{sign}{_group_indian(text)}"
