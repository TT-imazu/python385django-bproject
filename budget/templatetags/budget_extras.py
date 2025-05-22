from django import template
from django.db.models import Sum

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def filter_by_date_range(transactions, date_range):
    return transactions.filter(daterange=date_range)

@register.filter
def filter_by_itemtype(transactions, itemtypes):
    if isinstance(itemtypes, str):
        itemtypes = itemtypes.split(',')
    return transactions.filter(itemtype__in=itemtypes)

@register.filter
def sum_amount(transactions):
    return transactions.aggregate(total=Sum('amount'))['total'] or 0 