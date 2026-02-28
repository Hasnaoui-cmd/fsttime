from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get dictionary item by key.
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary:
        return dictionary.get(key)
    return None


@register.filter
def add_str(value, arg):
    """
    Concatenate two strings.
    Usage: {{ value|add_str:arg }}
    """
    return f"{value}{arg}"


@register.filter
def format_time(value, format_string='%H:%M'):
    """
    Format a time value.
    Usage: {{ time_value|format_time:"%H:%M" }}
    """
    if value:
        return value.strftime(format_string)
    return ""


@register.simple_tag
def get_entry(entry_dict, day_code, slot_number):
    """
    Get a timetable entry from the dictionary.
    Usage: {% get_entry entry_dict day_code slot.slot_number as entries %}
    """
    if entry_dict:
        key = f"{day_code}_{slot_number}"
        return entry_dict.get(key)
    return None
