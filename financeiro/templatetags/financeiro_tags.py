from django import template

register = template.Library()

@register.filter
def moeda_brl(valor):
    try:
        valor = float(valor)
        inteiro = int(valor)
        centavos = round((valor - inteiro) * 100)
        s = f"{inteiro:,}".replace(",", ".")
        return f"R$ {s},{centavos:02d}"
    except (ValueError, TypeError):
        return f"R$ {valor}"
