from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_name):
    """Get attribute by name -- used in lab_settings template."""
    return getattr(obj, attr_name, None)


@register.filter
def abs_val(value):
    """Return absolute value."""
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return value
