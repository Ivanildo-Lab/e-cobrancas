"""Context processor que disponibiliza a Empresa (logo/banner) em todos os templates.

Necessário para páginas sem usuário logado (ex.: login) exibirem o banner.
"""
from core.models import Empresa


def empresa(request):
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        emp = getattr(user, 'empresa', None)
        if emp:
            return {'empresa': emp}
    return {'empresa': Empresa.objects.first()}
