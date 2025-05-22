from django import template
from django.db.models import Sum
from django.template.defaultfilters import stringfilter, floatformat

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    辞書からキーを指定して値を取得するフィルター
    文字列の場合はそのまま返す
    """
    if isinstance(dictionary, str):
        return dictionary
    return dictionary.get(key)

@register.filter
def sum_attr(items, attr):
    """
    オブジェクトのリストから指定した属性の合計を計算するフィルター
    辞書の場合はget、オブジェクトの場合はgetattrを使用
    """
    total = 0
    for item in items:
        if isinstance(item, dict):
            # 辞書の場合
            value = item.get(attr, 0)
        else:
            # オブジェクトの場合
            value = getattr(item, attr, 0)
        if isinstance(value, (int, float)):
            total += value
    return total

@register.filter
def dict_get(d, key):
    return d.get(key, {})

@register.filter
def add(value, arg):
    try:
        return value + arg
    except (ValueError, TypeError):
        return value

@register.filter
def sub(value, arg):
    try:
        return value - arg
    except (ValueError, TypeError):
        return value

@register.filter
def mul(value, arg):
    try:
        return value * arg
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    try:
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return value

@register.filter
def intcomma(value):
    try:
        if isinstance(value, (int, float)):
            return f"{value:,}"
        return value
    except (ValueError, TypeError):
        return value

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

@register.filter
def format_number(value):
    """数値を3桁区切りの文字列に変換するフィルタ"""
    if value is None:
        return '-'
    try:
        return '{:,}'.format(int(value))
    except (ValueError, TypeError):
        return value

@register.filter
def filter_connected(items, connected):
    """
    連結状態でフィルタリングするフィルター
    辞書とオブジェクトの両方に対応
    """
    filtered_items = []
    for item in items:
        if isinstance(item, dict):
            # 辞書の場合
            has_connected = bool(item.get('connected_number'))
        else:
            # オブジェクトの場合
            has_connected = bool(getattr(item, 'connected_number', None))
        
        if has_connected == connected:
            filtered_items.append(item)
    return filtered_items

@register.filter
def sum_amount(items):
    """
    オブジェクトのリストからamount属性の合計を計算するフィルター
    辞書の場合はget、オブジェクトの場合はgetattrを使用
    """
    total = 0
    for item in items:
        if isinstance(item, dict):
            # 辞書の場合
            value = item.get('amount', 0)
        else:
            # オブジェクトの場合
            value = getattr(item, 'amount', 0)
        if isinstance(value, (int, float)):
            total += value
    return total 