from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import connection
from threading import Thread
from .models import Cidade, Cliente
from .forms import CidadeForm, ClienteForm


def _fetch_one(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None


def _fetch_all(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@login_required
def lista_cidades(request):
    page = request.GET.get('page', 1)
    busca = request.GET.get('q', '')
    queryset = Cidade.objects.all()
    if busca:
        queryset = queryset.filter(
            Q(nome__icontains=busca) | Q(uf__icontains=busca)
        )
    paginator = Paginator(queryset, 15)
    cidades = paginator.get_page(page)
    return render(request, 'cadastros/cidade_lista.html', {
        'cidades': cidades, 'busca': busca, 'titulo': 'Cidades'
    })


@login_required
def criar_cidade(request):
    if request.method == 'POST':
        form = CidadeForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            uf = form.cleaned_data['uf']
            with connection.cursor() as cur:
                cur.execute(
                    "INSERT INTO tbl_cidades (nome, uf, created_at) VALUES (%s, %s, NOW())",
                    [nome, uf]
                )
            messages.success(request, 'Cidade criada com sucesso!')
            return redirect('cadastros:lista_cidades')
    else:
        form = CidadeForm()
    return render(request, 'cadastros/cidade_form.html', {'form': form, 'titulo': 'Nova Cidade'})


@login_required
def editar_cidade(request, pk):
    cidade = get_object_or_404(Cidade, pk=pk)
    if request.method == 'POST':
        form = CidadeForm(request.POST, instance=cidade)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            uf = form.cleaned_data['uf']
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE tbl_cidades SET nome=%s, uf=%s WHERE id=%s",
                    [nome, uf, pk]
                )
            messages.success(request, f'Cidade "{nome}/{uf}" atualizada com sucesso!')
            return redirect('cadastros:lista_cidades')
    else:
        form = CidadeForm(instance=cidade)
    return render(request, 'cadastros/cidade_form.html', {
        'form': form, 'titulo': f'Editar: {cidade}'
    })


@login_required
def excluir_cidade(request, pk):
    cidade = get_object_or_404(Cidade, pk=pk)
    if request.method == 'POST':
        count = _fetch_one(
            "SELECT COUNT(*) as cnt FROM tbl_clientes WHERE cidade=%s", [pk]
        )
        if count and count['cnt'] > 0:
            messages.warning(request, f'Nao e possivel excluir "{cidade}" pois existem {count["cnt"]} cliente(s) cadastrados.')
        else:
            nome = str(cidade)
            with connection.cursor() as cur:
                cur.execute("DELETE FROM tbl_cidades WHERE id=%s", [pk])
            messages.success(request, f'Cidade "{nome}" excluida com sucesso!')
        return redirect('cadastros:lista_cidades')
    return redirect('cadastros:lista_cidades')


@login_required
def lista_clientes(request):
    page = request.GET.get('page', 1)
    busca = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'ativos')
    cidade_filter = request.GET.get('cidade', '')
    queryset = Cliente.objects.select_related('cidade').all()
    if status_filter == 'ativos':
        queryset = queryset.filter(ativo=True)
    elif status_filter == 'inativos':
        queryset = queryset.filter(ativo=False)
    if cidade_filter:
        queryset = queryset.filter(cidade_id=cidade_filter)
    if busca:
        queryset = queryset.filter(
            Q(nome__icontains=busca) | Q(contato__icontains=busca)
        )
    paginator = Paginator(queryset, 15)
    clientes = paginator.get_page(page)
    cidades = Cidade.objects.all().order_by('nome')
    total_geral = Cliente.objects.filter(ativo=True).count()
    return render(request, 'cadastros/cliente_lista.html', {
        'clientes': clientes, 'busca': busca, 'status_filter': status_filter,
        'cidade_filter': cidade_filter, 'cidades': cidades, 'titulo': 'Clientes',
        'total_geral': total_geral,
    })


@login_required
def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            cidade_id = d['cidade'].id if d.get('cidade') else None
            with connection.cursor() as cur:
                cur.execute(
                    """INSERT INTO tbl_clientes
                       (nome, contato, cidade, telefone, valormensalidade, diacobranca, obs, conexao, ativo, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                    [
                        d['nome'], d.get('contato', ''), cidade_id,
                        d.get('telefone', ''), d.get('valormensalidade'),
                        d.get('diacobranca'), d.get('obs', ''),
                        d.get('conexao', ''), d.get('ativo', True),
                    ]
                )
            messages.success(request, f'Cliente "{d["nome"]}" criado com sucesso!')
            return redirect('cadastros:lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'cadastros/cliente_form.html', {'form': form, 'titulo': 'Novo Cliente'})


@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            d = form.cleaned_data
            cidade_id = d['cidade'].id if d.get('cidade') else None
            with connection.cursor() as cur:
                cur.execute(
                    """UPDATE tbl_clientes
                       SET nome=%s, contato=%s, cidade=%s, telefone=%s,
                           valormensalidade=%s, diacobranca=%s, obs=%s, conexao=%s, ativo=%s
                       WHERE id=%s""",
                    [
                        d['nome'], d.get('contato', ''), cidade_id,
                        d.get('telefone', ''), d.get('valormensalidade'),
                        d.get('diacobranca'), d.get('obs', ''),
                        d.get('conexao', ''), d.get('ativo', True),
                        pk,
                    ]
                )
            messages.success(request, f'Cliente "{d["nome"]}" atualizado com sucesso!')
            return redirect('cadastros:lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'cadastros/cliente_form.html', {
        'form': form, 'titulo': f'Editando: {cliente.nome}'
    })


@login_required
def desativar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        current = _fetch_one("SELECT ativo FROM tbl_clientes WHERE id=%s", [pk])
        novo = not (current['ativo'] if current else True)
        with connection.cursor() as cur:
            cur.execute("UPDATE tbl_clientes SET ativo=%s WHERE id=%s", [novo, pk])
        status = "ativado" if novo else "desativado"
        messages.success(request, f'Cliente "{cliente.nome}" {status} com sucesso!')
    return redirect('cadastros:lista_clientes')


def _enviar_whatsapp(telefone, mensagem):
    import requests
    import logging
    logger = logging.getLogger('cadastros')
    try:
        from decouple import config
        url = config('EVOLUTION_API_URL')
        api_key = config('EVOLUTION_API_KEY')
        payload = {'number': telefone, 'text': mensagem}
        headers = {'apikey': api_key, 'Content-Type': 'application/json'}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            logger.info(f"[WHATSAPP] Enviado para {telefone}: OK")
        else:
            logger.error(f"[WHATSAPP] Falha para {telefone}: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"[WHATSAPP] Erro para {telefone}: {e}")


@login_required
def enviar_whatsapp_clientes(request):
    if request.method != 'POST':
        return redirect('cadastros:lista_clientes')

    ids_str = request.POST.get('clientes_ids', '')
    mensagem = request.POST.get('mensagem', '').strip()

    if not ids_str:
        messages.warning(request, 'Nenhum cliente selecionado.')
        return redirect('cadastros:lista_clientes')

    if not mensagem:
        messages.warning(request, 'Digite uma mensagem para enviar.')
        return redirect('cadastros:lista_clientes')

    ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
    clientes = Cliente.objects.filter(pk__in=ids, ativo=True)

    enviados = 0
    erros = 0
    sem_telefone = 0

    for cliente in clientes:
        if not cliente.telefone:
            sem_telefone += 1
            continue
        telefone = cliente.telefone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').strip()
        if not telefone.startswith('55'):
            telefone = '55' + telefone
        if len(telefone) < 12:
            sem_telefone += 1
            continue
        thread = Thread(target=_enviar_whatsapp, args=(telefone, mensagem))
        thread.start()
        enviados += 1

    if enviados > 0:
        messages.success(request, f'Mensagem programada para envio para {enviados} cliente(s).')
    if sem_telefone > 0:
        messages.warning(request, f'{sem_telefone} cliente(s) sem telefone valido.')
    if erros > 0:
        messages.error(request, f'{erros} erro(s) no envio.')

    return redirect('cadastros:lista_clientes')
