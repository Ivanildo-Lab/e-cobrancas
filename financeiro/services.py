import requests
import json
import logging
import time
import random
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# ---- Controle de volume (evita bloqueio por excesso de mensagens) ----
# Limite por hora e por dia — ajuste conforme a "saúde" do número
MAX_POR_HORA = getattr(settings, 'WHATSAPP_MAX_POR_HORA', 30)
MAX_POR_DIA = getattr(settings, 'WHATSAPP_MAX_POR_DIA', 150)

# Histórico de envios neste processo (reseta ao reiniciar o worker)
_historico_envios = []


def _limpar_historico():
    """Remove registros antigos do histórico."""
    global _historico_envios
    agora = datetime.now()
    _historico_envios = [t for t in _historico_envios if t > agora - timedelta(hours=24)]


def _verificar_limites():
    """Verifica se atingiu limite horário ou diário. Retorna (ok, motivo)."""
    _limpar_historico()
    agora = datetime.now()

    ultima_hora = sum(1 for t in _historico_envios if t > agora - timedelta(hours=1))
    if ultima_hora >= MAX_POR_HORA:
        return False, f"Limite horário atingido ({MAX_POR_HORA}/h)"

    hoje = sum(1 for t in _historico_envios if t.date() == agora.date())
    if hoje >= MAX_POR_DIA:
        return False, f"Limite diário atingido ({MAX_POR_DIA}/dia)"

    return True, ""


def _rate_limit():
    """Aplica rate limiting para evitar banimento no WhatsApp.
    Delay aleatório configurável entre MIN e MAX segundos.
    """
    min_delay = getattr(settings, 'WHATSAPP_DELAY_MIN', 5)
    max_delay = getattr(settings, 'WHATSAPP_DELAY_MAX', 12)
    delay = random.uniform(min_delay, max_delay)
    logger.info(f"[RATE-LIMIT] Aguardando {delay:.2f}s antes de enviar...")
    time.sleep(delay)
    _historico_envios.append(datetime.now())


def enviar_mensagem_whatsapp(telefone_destino, mensagem_texto):
    api_url = settings.EVOLUTION_API_URL
    api_key_value = settings.EVOLUTION_API_KEY_VALUE
    api_key_header_name = settings.EVOLUTION_API_KEY_HEADER_NAME

    if not api_url:
        logger.error("EVOLUTION_API_URL nao configurada.")
        return False, {"error": "URL da API de WhatsApp nao configurada."}

    # Verifica limites de volume antes de qualquer coisa
    ok, motivo = _verificar_limites()
    if not ok:
        logger.warning(f"[RATE-LIMIT] Envio BLOQUEADO: {motivo}")
        return False, {"error": motivo}

    headers = {"Content-Type": "application/json"}

    if api_key_header_name and api_key_value:
        headers[api_key_header_name] = api_key_value
    else:
        logger.error("API Key nao configurada para Evolution API.")
        return False, {"error": "Configuracao de autenticacao da API de WhatsApp ausente."}

    payload = {
        "number": telefone_destino,
        "text": mensagem_texto
    }

    try:
        # Rate limiting para evitar banimento
        _rate_limit()

        logger.info(f"[EVOLUTION] POST {api_url}")
        logger.info(f"[EVOLUTION] Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        logger.info(f"[EVOLUTION] Response status: {response.status_code}")
        logger.info(f"[EVOLUTION] Response body: {response.text[:500]}")

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            if response.status_code < 300:
                return True, {"raw_response": response.text, "status_code": response.status_code}
            response_data = {"error": response.text}

        if response.status_code in [200, 201]:
            return True, response_data
        else:
            logger.error(f"[EVOLUTION] Erro ({response.status_code}): {response_data}")
            return False, response_data

    except requests.exceptions.ConnectionError as e:
        logger.error(f"[EVOLUTION] Connection error: {e}")
        return False, {"error": f"Nao foi possivel conectar a API: {str(e)}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"[EVOLUTION] Request error: {e}")
        return False, {"error": str(e)}
    except Exception as e:
        logger.error(f"[EVOLUTION] Erro inesperado: {e}")
        return False, {"error": str(e)}


def telefone_formatar(telefone):
    numeros = ''.join(filter(str.isdigit, telefone or ''))
    if not numeros.startswith('55'):
        numeros = "55" + numeros
    return numeros


def _saudacao_aleatoria():
    """Retorna uma saudação aleatória para variar o conteúdo das mensagens.
    Evita bloqueio por mensagem idêntica em massa.
    """
    saudacoes = [
        "Olá",
        "Oi",
        "Bom dia",
        "Boa tarde",
        "Boa noite",
        "Oi, tudo bem?",
        "Olá, tudo bem?",
        "Prezado cliente",
    ]
    return random.choice(saudacoes)


def montar_mensagem_recibo(cliente_nome, parcelas_info, total_pago, data_pagamento, empresa=None):
    """Monta texto do recibo/comprovante de pagamento para envio via WhatsApp.

    parcelas_info: lista de dicts ou objetos com chaves/atributos
        'parcela' (numero) e 'valor' (float/Decimal).
    """
    partes = [f"{_saudacao_aleatoria()}, *{cliente_nome}!*"]
    partes.append("Segue o comprovante do seu pagamento:")
    partes.append("")
    partes.append("*RECIBO DE PAGAMENTO*")
    partes.append(f"Data do pagamento: *{data_pagamento}*")
    for p in parcelas_info:
        numero = p.get('parcela') if isinstance(p, dict) else getattr(p, 'parcela', '')
        valor = p.get('valor') if isinstance(p, dict) else getattr(p, 'valorconta', 0)
        venc = p.get('vencimento') if isinstance(p, dict) else getattr(p, 'vencimento', '')
        if hasattr(venc, 'strftime'):
            try:
                venc_txt = venc.strftime('%d/%m/%Y')
            except Exception:
                venc_txt = str(venc)
        else:
            venc_txt = str(venc) if venc else '-'
        try:
            valor_txt = f"{float(valor):.2f}"
        except (TypeError, ValueError):
            valor_txt = str(valor)
        partes.append(f"  - Parcela *{numero}* | Venc: {venc_txt} | Valor: R$ {valor_txt}")
    try:
        total_txt = f"{float(total_pago):.2f}"
    except (TypeError, ValueError):
        total_txt = str(total_pago)
    partes.append(f"\n*Valor total pago: R$ {total_txt}*")
    partes.append("\nReferente a manutenção do sistema comercial instalado em sua empresa, conforme contrato vigente.")
    if empresa is not None and getattr(empresa, 'nome', None):
        partes.append(f"\nRecebedor: {empresa.nome}")
        if getattr(empresa, 'responsavel', None):
            partes.append(f"Responsavel: {empresa.responsavel}")
    partes.append("\nObrigado pelo pagamento!")
    partes.append("Em caso de duvida, responda esta mensagem.")
    partes.append("\nVisite o nosso site ivcsofthouse.com.br para conhecer nossos produtos.")
    return "\n".join(partes)


def montar_mensagem_cobranca(cliente, parcelas, empresa=None):
    total_devido = sum(p.valorconta or 0 for p in parcelas)
    partes = [f"{_saudacao_aleatoria()}, *{cliente.nome}!*"]
    partes.append("Verificamos que constam as seguintes parcelas em aberto em seu nome:")
    partes.append("\nReferente a manutenção do sistema comercial instalado em sua empresa, conforme contrato vigente.")
    for p in parcelas:
        partes.append(f"  - Venc.: *{p.vencimento.strftime('%d/%m/%Y')}* | Valor: R$ {p.valorconta:.2f}")
    partes.append(f"\n*Valor total pendente: R$ {total_devido:.2f}*")

    if empresa and empresa.pix_chave:
        partes.append("\n*DADOS PARA PAGAMENTO:*")
        partes.append(f"Chave PIX: *{empresa.pix_chave}*")
        if empresa.pix_titular:
            partes.append(f"Titular: {empresa.pix_titular}")
        if empresa.pix_banco:
            partes.append(f"Banco: {empresa.pix_banco}")
        if empresa.pix_agencia and empresa.pix_conta:
            tipo = empresa.pix_tipo_conta or 'CC'
            partes.append(f"Agencia: {empresa.pix_agencia} | Conta: {empresa.pix_conta} ({tipo})")

    partes.append("\nPara regularizar ou obter mais detalhes, por favor, entre em contato.")
    partes.append("\n\n*IGNORAR CASO O DEBITO JA TENHA SIDO PAGO, E O COMPROVANTE ENVIADO.*")
    partes.append("\nVisite o nosso site ivcsofthouse.com.br para conhecer nossos produtos.")
    partes.append("\nObrigado!")
    return "\n".join(partes)
