from django import template

register = template.Library()


@register.filter
def get_item(valor, chave):
    if isinstance(valor, dict):
        return valor.get(chave, "")
    return ""
