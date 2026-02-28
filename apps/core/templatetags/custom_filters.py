from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a dynamic key.
    Usage: {{ dictionary|get_item:key_variable }}
    """
    if dictionary:
        return dictionary.get(key)
    return None


@register.filter
def make_key(day_code, slot_number):
    """
    Build a timetable grid key from day code and slot number.
    Usage: {{ day_code|make_key:slot.slot_number }}
    Returns: "MON_1", "TUE_2", etc.
    """
    return f"{day_code}_{slot_number}"


@register.simple_tag
def get_entry(entry_dict, day_code, slot_number):
    """
    Get a timetable entry from the dictionary.
    Usage: {% get_entry entry_dict day_code slot.slot_number as entry %}
    """
    if entry_dict:
        key = f"{day_code}_{slot_number}"
        return entry_dict.get(key)
    return None
