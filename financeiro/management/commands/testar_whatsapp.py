"""
Diagnostico da integracao com a Evolution API.

Uso (no servidor, dentro do container):
    python manage.py testar_whatsapp
    python manage.py testar_whatsapp --numero 5599999999999
    python manage.py testar_whatsapp --numero 5599999999999 --dry-run

Sem --numero apenas valida a configuracao e o status da instancia.
"""
import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


def _mascarar(valor):
    if not valor:
        return '(vazio)'
    if len(valor) <= 8:
        return '*' * len(valor)
    return f'{valor[:4]}...{valor[-4:]} (len={len(valor)})'


class Command(BaseCommand):
    help = 'Testa a configuracao e o envio de mensagens pela Evolution API'

    def add_arguments(self, parser):
        parser.add_argument('--numero', help='Numero destino com DDI, apenas digitos. Ex: 5599999999999')
        parser.add_argument('--mensagem', default='Teste de integracao - e-Cobrancas')
        parser.add_argument('--url', help='Sobrescreve EVOLUTION_API_URL')
        parser.add_argument('--key', help='Sobrescreve EVOLUTION_API_KEY_VALUE')
        parser.add_argument('--dry-run', action='store_true', help='So mostra a configuracao e o payload')

    def handle(self, *args, **options):
        url = options.get('url') or settings.EVOLUTION_API_URL
        key = options.get('key') or settings.EVOLUTION_API_KEY_VALUE
        header = settings.EVOLUTION_API_KEY_HEADER_NAME

        self.stdout.write('--- CONFIGURACAO ---')
        self.stdout.write(f'EVOLUTION_API_URL              : {url or "(vazio)"}')
        self.stdout.write(f'EVOLUTION_API_KEY_HEADER_NAME  : {header or "(vazio)"}')
        self.stdout.write(f'EVOLUTION_API_KEY_VALUE        : {_mascarar(key)}')

        if not url:
            self.stderr.write(self.style.ERROR(
                '\nEVOLUTION_API_URL nao configurada neste ambiente. '
                'No Coolify: aba Environment -> adicione a variavel -> clique em Deploy.'
            ))
            return

        if not key:
            self.stderr.write(self.style.ERROR('\nEVOLUTION_API_KEY_VALUE nao configurada neste ambiente.'))
            return

        headers = {'Content-Type': 'application/json', header or 'apikey': key}

        # Status da instancia (deriva a base a partir da URL de envio)
        base = url.split('/message/sendText/')[0].rstrip('/')
        if base and base != url:
            try:
                r = requests.get(f'{base}/instance/fetchInstances', headers=headers, timeout=20)
                self.stdout.write('\n--- INSTANCIA ---')
                self.stdout.write(f'GET {base}/instance/fetchInstances -> HTTP {r.status_code}')
                if r.status_code == 200:
                    dados = r.json()
                    for inst in dados if isinstance(dados, list) else [dados]:
                        self.stdout.write(
                            f"  nome={inst.get('name')} status={inst.get('connectionStatus')} "
                            f"numero={inst.get('ownerJid') or inst.get('number')}"
                        )
                else:
                    self.stdout.write(f'  corpo: {r.text[:300]}')
            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'\nFalha ao consultar a instancia: {e}'))

        numero = options.get('numero')
        payload = {'number': numero, 'text': options['mensagem']}

        self.stdout.write('\n--- PAYLOAD ---')
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n[dry-run] Nada foi enviado.'))
            return

        if not numero:
            self.stdout.write(self.style.WARNING(
                '\nSem --numero: nenhuma mensagem enviada. '
                'Use --numero 5599999999999 para testar o envio real.'
            ))
            return

        self.stdout.write('\n--- ENVIO ---')
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro de conexao: {type(e).__name__}: {e}'))
            return

        self.stdout.write(f'POST {url} -> HTTP {r.status_code}')
        self.stdout.write(f'Resposta: {r.text[:800]}')

        if r.status_code in (200, 201):
            self.stdout.write(self.style.SUCCESS('\nOK: mensagem aceita pela Evolution API.'))
        else:
            self.stderr.write(self.style.ERROR(
                '\nFALHOU. Dicas: confira se a instancia existe/esta conectada, '
                'se a API key e do mesmo servidor e se o numero tem WhatsApp.'
            ))
