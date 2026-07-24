import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def enviar_mensagem_whatsapp(telefone_destino, mensagem_texto):
    api_url = settings.EVOLUTION_API_URL
    api_key_value = settings.EVOLUTION_API_KEY_VALUE
    api_key_header_name = settings.EVOLUTION_API_KEY_HEADER_NAME

    if not api_url:
        logger.error("EVOLUTION_API_URL nao configurada.")
        return False, {"error": "URL da API de WhatsApp nao configurada."}

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


def montar_mensagem_cobranca(cliente, parcelas, empresa=None):
    total_devido = sum(p.valorconta or 0 for p in parcelas)
    partes = [f"Ola, *{cliente.nome}*!"]
    partes.append("Verificamos que constam as seguintes parcelas em aberto em seu nome:")
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
    return "\n".join(partes)
