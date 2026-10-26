# Segurança do Servidor — Hardening (20/10/2026)

Registro do que foi feito no VPS Hostinger KVM 4 (187.127.63.185, Ubuntu 24.04, Coolify v4.4.6).
Documentação privada — NÃO committada no repo público.

## ✅ Checklist aplicado

| Item | Detalhe |
|---|---|
| SECRET_KEY nova | Gerada no servidor via `openssl rand -base64 48`, colada direto no Coolify (env vars do app e-cobrancas). A antiga foi comprometida em conversa e descartada. |
| ALLOWED_HOSTS | `ecobrancas.187-127-63-185.sslip.io,localhost` (não usar `*`). Ao trocar domínio depois: atualizar aqui + CSRF_TRUSTED_ORIGINS. |
| CSRF_TRUSTED_ORIGINS | `https://ecobrancas.187-127-63-185.sslip.io` |
| SECURE_PROXY_SSL_HEADER | No código (setup/settings.py) — necessário pra login funcionar atrás do Traefik. |
| Domínio do app | `https://ecobrancas.187-127-63-185.sslip.io` (padrão: `<app>.187-127-63-185.sslip.io`; subdomínios do sslip.io funcionam). Domínio antigo (IP nu) removido. |
| Painel do Coolify | FQDN: `https://coolify.187-127-63-185.sslip.io` (Settings → Instance Domain). Acesso direto por IP:8000 BLOQUEADO (ver firewall). |
| 2FA | Ativado no perfil do usuário Coolify. Códigos de recuperação salvos pelo usuário. |
| Backup do .env do Coolify | `/data/coolify/source/.env` copiado para `/root/backups/coolify-env-<data>.txt` (chmod 600) + cópia fora do servidor. |
| Firewall | Regras abaixo (iptables + ip6tables, persistidas com iptables-persistent). |

## 🔥 Regras de firewall (atuais)

### IPv4 — chain DOCKER-USER (o Docker ignora ufw; estas são as regras que funcionam)

```bash
# Bloqueia mundo externo (eth0) de falar direto com portas internas 8080
# (pega painel: 8000->8080 E api do Traefik: 8080->8080 de uma vez)
iptables -I DOCKER-USER -i eth0 -p tcp --dport 8080 -j DROP

# Portas 1:1 do Coolify: bloqueia externo, libera rede interna Docker (172.16/12)
iptables -I DOCKER-USER -p tcp --dport 8000 -j DROP
iptables -I DOCKER-USER -p tcp --dport 6001 -j DROP
iptables -I DOCKER-USER -p tcp --dport 6002 -j DROP
iptables -I DOCKER-USER -p tcp -s 172.16.0.0/12 --dport 8000 -j RETURN
iptables -I DOCKER-USER -p tcp -s 172.16.0.0/12 --dport 6001 -j RETURN
iptables -I DOCKER-USER -p tcp -s 172.16.0.0/12 --dport 6002 -j RETURN
```

### IPv6 — chain INPUT (docker-proxy escuta IPv6 direto, não passa por DOCKER-USER)

```bash
ip6tables -I INPUT -p tcp --dport 8000 -j DROP
ip6tables -I INPUT -p tcp --dport 8080 -j DROP
ip6tables -I INPUT -p tcp --dport 6001 -j DROP
ip6tables -I INPUT -p tcp --dport 6002 -j DROP
```

### Persistir

```bash
netfilter-persistent save
```

### Superfície pública esperada

```
22 OPEN (SSH) | 80 OPEN | 443 OPEN | 8000/8080/6001/6002 FECHADAS
```

Verificar de qualquer máquina (PowerShell):
```powershell
foreach ($p in 22,80,443,8000,8080,6001,6002) { $r = Test-NetConnection 187.127.63.185 -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue; if ($r) { "$p ABERTA" } else { "$p fechada" } }
```

### Desfazer (salva-vidas)

Pelo console web da Hostinger (root):
```bash
iptables -F DOCKER-USER
ip6tables -F INPUT   # cuidado: zera todas as regras INPUT IPv6
```

## ⚠️ Notas importantes

- **Porta interna do painel:** o container `coolify` mapeia `8000 -> 8080` (porta interna 8080).
  Por isso o DROP que pega o tráfego externo usa `--dport 8080` (a porta DEPOIS da tradução do Docker).
- **Regras estáveis:** nada usa IP de container hardcoded → updates do Coolify não quebram as regras.
- **ufw foi removido** pelo iptables-persistent (estava instalado, nunca ativado). Não usar ufw pra portas Docker — não pega.
- **Recuperação total:** console web da Hostinger (hPanel → VPS → Web console), user root. Nunca dependa só do painel.
- **Próximos passos sugeridos:** token do GitHub no Coolify (evitar rate limit); quando sair do sslip.io pro domínio real, repetir a troca de domínio (app + ALLOWED_HOSTS + CSRF_TRUSTED_ORIGINS + FQDN do painel).

## 📱 Envio em massa WhatsApp (reforço de 20/10)

Após gafe de envio para todos os clientes (filtro não aplicado):

- `financeiro:enviar_lote_whatsapp` só envia para `parcelas_ids` marcadas (sem marcação = sem envio, avisando). Filtros da tela NUNCA baseiam envio.
- `cadastros:enviar_whatsapp_clientes` idem; suporta "selecionar todos (todas as páginas)" respeitando os MESMOS filtros da tela (`_filtrar_clientes`).
- Confirmações mostram quantidades (parcelas + clientes) e há contador em tempo real nas listas.
