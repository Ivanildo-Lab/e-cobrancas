import uuid
import random
import logging
from decimal import Decimal
from threading import Thread

from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db import connection
from django.http import HttpResponse
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import Parcela
from .forms import (
    GerarParcelasForm, EditarParcelaForm, RegistrarPagamentoForm,
    FiltroParcelasForm, BaixaLoteForm
)
from cadastros.models import Cliente, Cidade
from core.models import Empresa
from .services import enviar_mensagem_whatsapp, telefone_formatar, montar_mensagem_cobranca

logger = logging.getLogger(__name__)

# Mapeamento de situacao do banco -> filter values
SITUACAO_MAP = {
    'aberta': 'Aberta',
    'liquidada': 'Liquidada',
    'cancelada': 'Cancelada',
    'atrasada': 'Aberta',
}


def _construir_query_parcelas(filtros):
    status = filtros.get('status', 'aberta')

    query = Parcela.objects.select_related('cliente', 'cliente__cidade').filter(cliente__ativo=True)

    cliente_id = filtros.get('cliente')
    if cliente_id:
        query = query.filter(cliente_id=cliente_id)

    venc_inicio = filtros.get('venc_inicio')
    venc_fim = filtros.get('venc_fim')
    pag_inicio = filtros.get('pag_inicio')
    pag_fim = filtros.get('pag_fim')

    if venc_inicio:
        query = query.filter(vencimento__gte=venc_inicio)
    if venc_fim:
        query = query.filter(vencimento__lte=venc_fim)
    if pag_inicio:
        query = query.filter(pagamento__gte=pag_inicio, situacao='Liquidada')
    if pag_fim:
        query = query.filter(pagamento__lte=pag_fim, situacao='Liquidada')

    hoje = timezone.now().date()

    if status == 'aberta':
        query = query.filter(situacao='Aberta', vencimento__gte=hoje)
    elif status == 'atrasada':
        query = query.filter(situacao='Aberta', vencimento__lt=hoje)
    elif status == 'liquidada':
        query = query.filter(situacao='Liquidada')
    elif status == 'cancelada':
        query = query.filter(situacao__iexact='Cancelada')

    return query, status


def _enviar_whatsapp_background(telefone, mensagem):
    logger.info(f"[WHATSAPP] Iniciando envio para {telefone}")
    sucesso, detalhes = enviar_mensagem_whatsapp(telefone, mensagem)
    if sucesso:
        logger.info(f"[WHATSAPP] SUCESSO para {telefone}: {detalhes}")
    else:
        logger.error(f"[WHATSAPP] FALHA para {telefone}: {detalhes}")


@login_required
def dashboard(request):
    hoje = timezone.now().date()
    ano_atual = hoje.year
    mes_atual = hoje.month

    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Marco', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    nome_mes = meses_pt.get(mes_atual, str(mes_atual))

    base = Parcela.objects.filter(cliente__ativo=True)

    a_receber_mes = base.filter(
        situacao='Aberta',
        vencimento__year=ano_atual,
        vencimento__month=mes_atual,
    ).aggregate(total=Sum('valorconta'))['total'] or Decimal('0.00')

    recebido_mes = base.filter(
        situacao='Liquidada',
        pagamento__year=ano_atual,
        pagamento__month=mes_atual,
    ).aggregate(total=Sum('valorconta'))['total'] or Decimal('0.00')

    total_atrasado = base.filter(
        situacao='Aberta',
        vencimento__lt=hoje,
    ).aggregate(total=Sum('valorconta'))['total'] or Decimal('0.00')

    labels_chart = []
    data_recebido = []
    data_a_vencer = []

    for i in range(5, -1, -1):
        ref = hoje - relativedelta(months=i)
        labels_chart.append(ref.strftime("%m/%Y"))

        a_vencer = base.filter(
            situacao='Aberta',
            vencimento__year=ref.year,
            vencimento__month=ref.month,
        ).aggregate(total=Sum('valorconta'))['total'] or 0
        data_a_vencer.append(float(a_vencer))

        recebido = base.filter(
            situacao='Liquidada',
            pagamento__year=ref.year,
            pagamento__month=ref.month,
        ).aggregate(total=Sum('valorconta'))['total'] or 0
        data_recebido.append(float(recebido))

    chart_data = {
        'labels': labels_chart,
        'datasets': [
            {'label': 'Valor Recebido', 'backgroundColor': 'rgba(75, 192, 192, 0.5)', 'borderColor': 'rgb(75, 192, 192)', 'data': data_recebido, 'borderWidth': 1},
            {'label': 'Valor a Vencer', 'backgroundColor': 'rgba(255, 159, 64, 0.5)', 'borderColor': 'rgb(255, 159, 64)', 'data': data_a_vencer, 'borderWidth': 1},
        ]
    }

    total_clientes = Cliente.objects.filter(ativo=True).count()
    total_parcelas_abertas = base.filter(situacao='Aberta').count()

    return render(request, 'financeiro/dashboard.html', {
        'titulo': 'Dashboard',
        'a_receber_mes': a_receber_mes,
        'recebido_mes': recebido_mes,
        'total_atrasado': total_atrasado,
        'nome_mes_atual': f"{nome_mes}/{ano_atual}",
        'chart_data': chart_data,
        'total_clientes': total_clientes,
        'total_parcelas_abertas': total_parcelas_abertas,
    })


@login_required
def gerar_parcelas(request):
    if request.method == 'POST':
        form = GerarParcelasForm(request.POST)
        if form.is_valid():
            cliente = form.cleaned_data['cliente']
            valor = form.cleaned_data['valor_parcela']
            quantidade = form.cleaned_data['quantidade_parcelas']
            primeira_data = form.cleaned_data['primeiro_vencimento']
            periodicidade = form.cleaned_data['periodicidade']

            random_part = random.randint(100000, 999999)
            emissao = timezone.now().date()

            with connection.cursor() as cur:
                for i in range(quantidade):
                    num = i + 1
                    data_venc = primeira_data
                    if i > 0 and periodicidade == 'mensal':
                        data_venc = primeira_data + relativedelta(months=i)

                    numero_formatado = f"REC-{random_part}-{num}/{quantidade}"

                    cur.execute(
                        """INSERT INTO tbl_contasareceber
                           (cliente, parcela, emissao, vencimento, valorconta, situacao, created_at)
                           VALUES (%s, %s, %s, %s, %s, 'Aberta', NOW())""",
                        [cliente.id, numero_formatado, emissao, data_venc, valor]
                    )

            messages.success(request, f'{quantidade} parcelas geradas com sucesso para {cliente.nome}!')
            return redirect('financeiro:lista_parcelas')
    else:
        form = GerarParcelasForm()

    return render(request, 'financeiro/parcela_gerar.html', {
        'form': form, 'titulo': 'Gerar Parcelas'
    })


@login_required
def lista_parcelas(request):
    page = request.GET.get('page', 1)
    form = FiltroParcelasForm(request.GET)

    filtros = {k: v for k, v in request.GET.items() if v}
    filtros.setdefault('status', 'aberta')

    query, status_usado = _construir_query_parcelas(filtros)

    if status_usado == 'liquidada':
        query = query.order_by('-pagamento', '-vencimento')
    else:
        query = query.order_by('vencimento')

    totais = query.aggregate(
        valor_parcelas=Sum('valorconta'),
        quantidade=Count('id'),
    )
    for k in totais:
        if totais[k] is None:
            totais[k] = Decimal('0.00') if k != 'quantidade' else 0

    paginator = Paginator(query, 15)
    parcelas = paginator.get_page(page)

    return render(request, 'financeiro/parcela_lista.html', {
        'titulo': 'Lista de Parcelas',
        'form': form,
        'parcelas': parcelas,
        'totais': totais,
        'current_filters': filtros,
    })


@login_required
def editar_parcela(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    if parcela.situacao.lower() != 'aberta':
        messages.warning(request, 'Apenas parcelas abertas podem ser editadas.')
        return redirect('financeiro:lista_parcelas')

    if request.method == 'POST':
        form = EditarParcelaForm(request.POST, instance=parcela)
        if form.is_valid():
            d = form.cleaned_data
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE tbl_contasareceber SET valorconta=%s, vencimento=%s WHERE id=%s",
                    [d['valorconta'], d['vencimento'], pk]
                )
            messages.success(request, f'Parcela {parcela.parcela} atualizada com sucesso!')
            return redirect('financeiro:lista_parcelas')
    else:
        form = EditarParcelaForm(instance=parcela)

    return render(request, 'financeiro/parcela_editar.html', {
        'form': form, 'parcela': parcela, 'titulo': 'Editar Parcela'
    })


def _verificar_ultima_parcela(request, cliente_id):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as cnt FROM tbl_contasareceber WHERE cliente=%s AND situacao='Aberta'",
            [cliente_id]
        )
        row = cur.fetchone()
        abertas = row[0] if row else 0
    if abertas == 0:
        cliente_nome = None
        with connection.cursor() as cur:
            cur.execute("SELECT nome FROM tbl_clientes WHERE id=%s", [cliente_id])
            r = cur.fetchone()
            if r:
                cliente_nome = r[0]
        nome = cliente_nome or "este cliente"
        messages.warning(
            request,
            f'Atencao: {nome} nao possui mais parcelas em aberto! '
            f'<a href="{resolve_url("financeiro:gerar_parcelas")}" class="font-bold underline">Gerar novas parcelas</a>.'
        )


@login_required
def registrar_pagamento(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    if parcela.situacao.lower() != 'aberta':
        messages.warning(request, 'Esta parcela nao esta aberta para pagamento.')
        return redirect('financeiro:lista_parcelas')

    if request.method == 'POST':
        form = RegistrarPagamentoForm(request.POST)
        if form.is_valid():
            data_pag = form.cleaned_data['data_pagamento']
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE tbl_contasareceber SET pagamento=%s, situacao='Liquidada' WHERE id=%s",
                    [data_pag, pk]
                )
            request.session['recibo_data'] = {
                'data_pagamento': data_pag.strftime('%d/%m/%Y') if hasattr(data_pag, 'strftime') else str(data_pag),
                'parcelas': [{
                    'id': parcela.id,
                    'parcela': parcela.parcela,
                    'cliente_nome': parcela.cliente.nome,
                    'valor': parcela.valorconta,
                }],
                'total': float(parcela.valorconta or 0),
            }
            _verificar_ultima_parcela(request, parcela.cliente_id)
            return redirect('financeiro:recibo_lote')
        else:
            messages.error(request, 'Dados invalidos. Verifique data e valor.')
    return redirect('financeiro:lista_parcelas')


@login_required
def cancelar_parcela(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    if parcela.situacao.lower() != 'aberta':
        messages.warning(request, 'Apenas parcelas abertas podem ser canceladas.')
        return redirect('financeiro:lista_parcelas')

    if request.method == 'POST':
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE tbl_contasareceber SET situacao='Cancelada' WHERE id=%s", [pk]
            )
        messages.success(request, f'Parcela {parcela.parcela} cancelada com sucesso!')
        _verificar_ultima_parcela(request, parcela.cliente_id)
    return redirect('financeiro:lista_parcelas')


@login_required
def desfazer_liquidacao(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    if parcela.situacao.lower() != 'liquidada':
        messages.warning(request, 'Apenas parcelas liquidadas podem ter a liquidacao desfeita.')
        return redirect('financeiro:lista_parcelas')

    if request.method == 'POST':
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE tbl_contasareceber SET situacao='Aberta', pagamento=NULL WHERE id=%s",
                [pk]
            )
        messages.success(request, f'Liquidacao da parcela {parcela.parcela} desfeita!')
    return redirect('financeiro:lista_parcelas')


@login_required
def enviar_whatsapp_individual(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    cliente = parcela.cliente

    if not cliente.telefone:
        messages.warning(request, f'Cliente {cliente.nome} nao possui telefone cadastrado.')
        return redirect('financeiro:lista_parcelas')

    parcelas_abertas = Parcela.objects.filter(
        cliente=cliente, situacao='Aberta'
    ).order_by('vencimento')

    if not parcelas_abertas.exists():
        messages.warning(request, f'Cliente {cliente.nome} nao possui parcelas em aberto.')
        return redirect('financeiro:lista_parcelas')

    telefone = telefone_formatar(cliente.telefone)
    if len(telefone) < 12:
        messages.warning(request, f'Telefone do cliente {cliente.nome} esta em formato invalido.')
        return redirect('financeiro:lista_parcelas')

    empresa = Empresa.objects.first()
    mensagem = montar_mensagem_cobranca(cliente, parcelas_abertas, empresa)

    thread = Thread(target=_enviar_whatsapp_background, args=(telefone, mensagem))
    thread.start()

    messages.success(request, f'Mensagem de cobranca programada para envio para {cliente.nome}.')
    return redirect('financeiro:lista_parcelas')


@login_required
def enviar_lote_whatsapp(request):
    if request.method != 'POST':
        return redirect('financeiro:lista_parcelas')

    filtros = {k: v for k, v in request.POST.items() if v}
    query, _ = _construir_query_parcelas(filtros)
    parcelas_filtradas = query.filter(situacao='Aberta').order_by('cliente_id', 'vencimento')

    if not parcelas_filtradas.exists():
        messages.info(request, 'Nenhuma parcela aberta encontrada com os filtros aplicados.')
        return redirect('financeiro:lista_parcelas')

    clientes_notificar = {}
    for p in parcelas_filtradas:
        c = p.cliente
        if c not in clientes_notificar:
            clientes_notificar[c] = {'parcelas': [], 'total': Decimal('0.00')}
        clientes_notificar[c]['parcelas'].append(p)
        clientes_notificar[c]['total'] += p.valorconta

    enviados = 0
    erros = 0
    empresa = Empresa.objects.first()

    for cliente, dados in clientes_notificar.items():
        if not cliente.telefone:
            erros += 1
            continue

        telefone = telefone_formatar(cliente.telefone)
        if len(telefone) < 12:
            erros += 1
            continue

        msg = montar_mensagem_cobranca(cliente, dados['parcelas'], empresa)
        thread = Thread(target=_enviar_whatsapp_background, args=(telefone, msg))
        thread.start()
        enviados += 1

    texto = f'Lembretes WhatsApp programados para {enviados} cliente(s).'
    if erros:
        texto += f' {erros} cliente(s) sem telefone valido.'
    messages.info(request, texto)

    return redirect('financeiro:lista_parcelas')


@login_required
def gerar_pdf(request):
    filtros = {k: v for k, v in request.GET.items() if v}
    query, status_usado = _construir_query_parcelas(filtros)

    if status_usado == 'liquidada':
        query = query.order_by('-pagamento')
    else:
        query = query.order_by('vencimento')

    parcelas = query.all()

    totais = {'aberto': Decimal('0.00'), 'pago': Decimal('0.00'), 'cancelado': Decimal('0.00'), 'total_geral': Decimal('0.00')}
    for p in parcelas:
        sit = (p.situacao or '').lower()
        valor = p.valorconta or Decimal('0.00')
        if sit == 'liquidada':
            totais['pago'] += valor
        elif sit == 'aberta':
            totais['aberto'] += valor
        elif 'cancel' in sit:
            totais['cancelado'] += valor
        totais['total_geral'] += valor

    try:
        from weasyprint import HTML
        response_html = render(request, 'financeiro/parcela_pdf.html', {
            'parcelas': parcelas, 'totais': totais, 'titulo': 'Relatorio de Parcelas'
        })
        html_string = response_html.content.decode('utf-8')
        pdf_bytes = HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=parcelas_{timezone.now().strftime("%Y%m%d")}.pdf'
        return response
    except ImportError:
        messages.warning(request, 'WeasyPrint nao instalado. Usando impressao do navegador.')
        return render(request, 'financeiro/parcela_pdf.html', {
            'parcelas': parcelas, 'totais': totais, 'titulo': 'Relatorio de Parcelas'
        })


@login_required
def baixa_lote(request):
    if request.method != 'POST':
        return redirect('financeiro:lista_parcelas')

    ids_selecionados = request.POST.getlist('parcelas_ids')
    data_pagamento = request.POST.get('data_pagamento')

    if not ids_selecionados:
        messages.warning(request, 'Nenhuma parcela selecionada.')
        return redirect('financeiro:lista_parcelas')

    if not data_pagamento:
        messages.warning(request, 'Informe a data de pagamento.')
        return redirect('financeiro:lista_parcelas')

    parcelas_baixadas = []
    with connection.cursor() as cur:
        for pid in ids_selecionados:
            cur.execute(
                "UPDATE tbl_contasareceber SET pagamento=%s, situacao='Liquidada' WHERE id=%s AND situacao='Aberta'",
                [data_pagamento, pid]
            )
            if cur.rowcount > 0:
                cur.execute(
                    "SELECT p.parcela, c.nome, p.valorconta FROM tbl_contasareceber p JOIN tbl_clientes c ON p.cliente=c.id WHERE p.id=%s",
                    [pid]
                )
                row = cur.fetchone()
                if row:
                    parcelas_baixadas.append({
                        'id': pid, 'parcela': row[0], 'cliente_nome': row[1], 'valor': row[2]
                    })

    if parcelas_baixadas:
        messages.success(request, f'{len(parcelas_baixadas)} parcela(s) baixada(s) com sucesso!')
        request.session['recibo_data'] = {
            'data_pagamento': data_pagamento,
            'parcelas': parcelas_baixadas,
            'total': sum(float(p['valor']) for p in parcelas_baixadas),
        }
        return redirect('financeiro:recibo_lote')
    else:
        messages.warning(request, 'Nenhuma parcela aberta encontrada para baixar.')

    return redirect('financeiro:lista_parcelas')


@login_required
def recibo_lote(request):
    recibo_data = request.session.pop('recibo_data', None)
    if not recibo_data:
        messages.warning(request, 'Nenhum dado de recibo disponivel.')
        return redirect('financeiro:lista_parcelas')
    return render(request, 'financeiro/recibo_lote.html', {
        'recibo': recibo_data, 'titulo': 'Recibo de Pagamento'
    })


@login_required
def recibo_individual(request, pk):
    parcela = get_object_or_404(Parcela, pk=pk)
    if parcela.situacao.lower() != 'liquidada':
        messages.warning(request, 'Apenas parcelas liquidadas podem gerar recibo.')
        return redirect('financeiro:lista_parcelas')

    recibo_data = {
        'data_pagamento': parcela.pagamento.strftime('%d/%m/%Y') if parcela.pagamento else '-',
        'parcelas': [{
            'id': parcela.id,
            'parcela': parcela.parcela,
            'cliente_nome': parcela.cliente.nome,
            'valor': parcela.valorconta,
        }],
        'total': float(parcela.valorconta or 0),
    }
    return render(request, 'financeiro/recibo_lote.html', {
        'recibo': recibo_data, 'titulo': 'Recibo de Pagamento'
    })
