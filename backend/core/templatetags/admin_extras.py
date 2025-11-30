from django import template

register = template.Library()

@register.filter
def getattr(obj, attr):
    """Получает атрибут объекта"""
    if hasattr(obj, attr):
        value = getattr(obj, attr)
        if isinstance(value, list):
            return ', '.join(map(str, value))
        return value
    return '-'