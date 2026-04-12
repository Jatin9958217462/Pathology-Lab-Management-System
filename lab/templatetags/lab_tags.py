from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_name):
    """Get attribute by name -- used in lab_settings template for dynamic sig fields."""
    return getattr(obj, attr_name, None)
