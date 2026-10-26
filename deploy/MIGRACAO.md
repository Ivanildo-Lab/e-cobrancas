# Guia de Migração: PythonAnywhere → Hostinger VPS (Coolify + Docker)

> Contexto: 15 apps Python/Django/Flask.
> - **e-cobrança** → usa Supabase (Postgres externo). **Não migra o banco**, fica como está.
> - **Outros 14 apps** → usam MySQL no PythonAnywhere (gerenciado via Workbench). Migram para MySQL no VPS.
> Custo atual PA: **$52/mês** (~R$ 286). Meta: **KVM 4 da Hostinger** (R$ 149,99 na renovação).

---

## 0. Visão geral do que vamos fazer

1. Subir o VPS (Hostinger KVM 4, Ubuntu 24.04).
2. Instalar o **Coolify** (painel que gerencia Docker, deploys e SSL).
3. Instalar e proteger o **MySQL** no VPS (porta 3306 NÃO exposta).
4. Configurar o **Workbench** para conectar via **túnel SSH**.
5. Migrar os 14 bancos MySQL (dump no PA → restore no VPS).
6. Publicar os 15 apps no Coolify (um por repo do GitHub).
7. Configurar **backups automáticos** dos 14 bancos + mídia.
8. Só então desligar o PythonAnywhere.

---

## 1. Subir o VPS na Hostinger

1. Compre o plano **KVM 4** (16 GB RAM — folga pros 15 apps + MySQL).
   - Na primeira compra o valor promocional exige contrato de 2 anos à vista.
   - Se preferir pagar mensal, o valor de renovação (R$ 149,99) já é vantajoso.
2. Escolha o sistema operacional: **Ubuntu 24.04 LTS**.
3. Escolha a localização do datacenter mais perto do seu público (ex.: **São Paulo** se tiver, senão **Miami**).
4. Anote: **IP do servidor**, **usuário root** e a **senha** (ou configure chave SSH).

### Acesso inicial por SSH
```bash
ssh root@SEU_IP
```

### Primeiras configurações de segurança
```bash
# Atualiza o sistema
apt update && apt upgrade -y

# Cria um usuário não-root (substitua "seuusuario")
adduser seuusuario
usermod -aG sudo seuusuario

# Copia sua chave SSH pro usuário (mais seguro que senha)
ssh-keygen -t ed25519        # no SEU computador, se ainda não tiver chave
ssh-copy-id seuusuario@SEU_IP # no SEU computador

# Desativa login por senha (só chave SSH) — faz DEPOIS de testar a chave!
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

---

## 2. Instalar o Coolify

O Coolify é um painel open-source (tipo "Vercel self-hosted") que cuida de Docker, deploys, SSL e proxy.

```bash
# Com o script oficial (roda como root)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

1. Abra `http://SEU_IP:8000` no navegador e crie a conta de admin.
2. No painel, vá em **Servers** → servidor local → marque **Use as "Production Server"**.
3. O Coolify instala Docker, Traefik (proxy/SSL) e o resto automaticamente.

> **Dica:** depois de apontar seu domínio pro IP do VPS, acesse pelo domínio
> `https://SEU_IP.sslip.io` ou configure um subdomínio (ex.: `coolify.seudominio.com`)
> pra ter o painel com HTTPS.

---

## 3. Subir o MySQL (como serviço do Coolify)

O MySQL roda como **container na mesma rede do Coolify** — mais seguro (não fica
exposto na rede pública) e mais limpo. Detalhes completos em **`GESTAO-BANCO.md`**.

1. No projeto do Coolify, adicione um serviço **MySQL** (one-click).
2. Defina usuário/root/senha (senha forte e única). Anote a senha.
3. Dentro dele, crie os 14 databases (um por app).

### ⚠️ `DB_HOST` = nome do serviço, NÃO `127.0.0.1`
Dentro de um container, `127.0.0.1` é o próprio container. Nos apps, use
`DB_HOST = mysql` (o nome do serviço no Coolify), que é resolvido na rede interna.

### Proteção da porta 3306 no host
Como o MySQL é um container interno, a 3306 **não precisa** (e não deve) ser
aberta no firewall do VPS. Só libere SSH, HTTP e HTTPS:
```bash
sudo apt install ufw -y
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status   # confirme que 3306 NÃO aparece
```

---

## 4. Gerenciar o banco pela web (Adminer — no lugar do Workbench)

Em vez do Workbench local (que depende de túnel SSH e é mais trabalhoso), use o
**Adminer**: um gerenciador web leve e seguro, rodando no Coolify com HTTPS.
Guia completo e arquivo `adminer-compose.yml` em **`GESTAO-BANCO.md`**.

Resumo:
- Adicione o `adminer-compose.yml` como serviço do Coolify, na mesma rede do MySQL.
- Aponte um domínio privado (ex.: `https://db.seudominio.com`) — SSL automático.
- Conecte com host `mysql`, porta 3306, usuário/senha do MySQL.
- **Antes de expor na internet**, aplique as medidas de segurança do `GESTAO-BANCO.md`
  (senha forte, restrição de acesso, fail2ban, ligar só quando usar).

---

## 5. Migrar os 14 bancos MySQL

Para **cada app** que usa MySQL:

### 5.1 Dump no PythonAnywhere
No console do PA (ou via Workbench conectado ao MySQL do PA):
```bash
mysqldump -u USUARIO_PA -p --single-transaction NOME_DO_BANCO > nome_do_banco.sql
```

### 5.2 Copiar o dump pro VPS
```bash
# Do seu computador (com o arquivo baixado do PA):
scp nome_do_banco.sql seuusuario@SEU_IP:/tmp/
```

### 5.3 Restore no VPS
Via **Adminer**: abra o banco de destino → aba **Importar** → envie o `.sql`.
Ou via CLI no container MySQL:
```bash
docker exec -i NOME_CONTAINER_MYSQL mysql -u appuser -p NOME_DO_BANCO < /tmp/nome_do_banco.sql
```

> Repita pra cada um dos 14 bancos, **um app por vez** (dump individual por app,
> como você planejou). Confira, depois do restore, se as contas de usuário do
> banco batem (alguns apps criam usuários específicos no banco).

---

## 6. Publicar os apps no Coolify

Para **cada app**, no painel do Coolify:

1. **New Resource** → **Public Git Repository** → cole a URL do repo GitHub.
2. Escolha o **Build Pack: Dockerfile** (o Coolify acha o `Dockerfile` na raiz).
3. Na aba **Environment**, configure as variáveis:
   - **e-cobrança (Supabase):** `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`,
     e `DATABASE_URL` = a URL do Supabase (postgres://...)
   - **Apps Django com MySQL (ex.: e-metalurgicaservicos):** eles leem `DB_*`:
     `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`,
     `DB_HOST=mysql`, `DB_PORT=3306`, `DB_NAME=<banco_do_app>`,
     `DB_USER`, `DB_PASSWORD`
     *(Apps que usem `DATABASE_URL` de um jeito só: `mysql://user:senha@mysql:3306/banco`)*
   - Variáveis extras de cada app (chaves de API etc.)
4. Na aba **Ports** / **Networks**, exponha a porta `8000`.
5. Na aba **Domains**, adicione o domínio do app (ex.: `app.seudominio.com`).
   O Coolify configura o SSL (Let's Encrypt) automaticamente.
6. Clique em **Deploy**.

> Para apps **Flask**, o `Dockerfile` é igual — só muda o comando final
> (gunicorn apontando pro módulo WSGI do Flask em vez de `setup.wsgi`).
> Para apps Django com **MySQL**, o `requirements.txt` deve ter `mysqlclient`
> em vez de `psycopg2-binary` (e o Dockerfile com estágio de build, como o de
> `e-metalurgicaservicos`).

### ⚠️ Arquivos estáticos em apps Django SEM Whitenoise
No PythonAnywhere, o static era servido pelo próprio PA. Em Docker, o gunicorn
**não** serve `/static/` sozinho. O e-cobrança já tem Whitenoise (funciona direto).
Para os apps Django que **não** têm Whitenoise (ex.: e-metalurgicaservicos), sem
isso o Django Admin e as páginas aparecem **sem CSS/JS**. Solução (uma vez por app):
1. `requirements.txt`: adicione `whitenoise`.
2. `settings.py`: adicione após SecurityMiddleware:
   `'whitenoise.middleware.WhiteNoiseMiddleware',`
3. `settings.py`: adicione `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`

> Alternativa sem tocar no código: servir `/static/` e `/media/` via proxy do Coolify,
> mas o Whitenoise é mais simples e é o padrão que o e-cobrança já usa.

### Persistência de mídia
O `docker-compose.yml` já declara o volume `media_data` montado em `/app/media`.
Garanta que cada app com uploads tenha esse volume, senão os uploads somem no redeploy.

---

## 7. Backups automáticos

### 7.1 Backup dos 14 bancos MySQL
Use o script `deploy/backup-mysql.sh`. Copie pro VPS e agende no cron:

```bash
sudo cp backup-mysql.sh /usr/local/bin/backup-mysql.sh
sudo chmod +x /usr/local/bin/backup-mysql.sh
```

Edite o crontab (`crontab -e`) e adicione (ex.: todo dia às 3h):
```
0 3 * * * /usr/local/bin/backup-mysql.sh
```

### 7.2 Backup da mídia
A mídia fica no volume Docker. Copie para fora do VPS regularmente:
```bash
# Exemplo: copia a mídia dos apps pra um backup offsite
rsync -av /var/lib/docker/volumes/ SEU_USUARIO@OUTRO_SERVIDOR:/backups/midia/
```

> **Regra de ouro:** backup que não está em outro lugar não é backup.
> Combine o dump do banco + a pasta de mídia num destino fora do VPS
> (outro servidor, storage, etc.).

---

## 8. Checklist final antes de desligar o PythonAnywhere

- [ ] Todos os 15 apps no ar via Coolify, com domínio e SSL funcionando.
- [ ] Login e CRUD testados em cada app.
- [ ] e-cobrança conectando no Supabase normalmente.
- [ ] Os 14 apps conectando no MySQL do VPS (via Workbench e via app).
- [ ] Mídia/uploads aparecendo corretamente (volume persistente ok).
- [ ] Backup automático dos 14 bancos rodando (confira os arquivos gerados).
- [ ] Backup de mídia configurado.
- [ ] Porta 3306 fechada no firewall (acesso só via túnel SSH).
- [ ] Workbench conectando via túnel SSH.

Só depois de tudo isso marcado, cancele o PythonAnywhere.

---

## Notas importantes

- **RAM:** 15 apps Django/Flask com 2 workers cada + MySQL cabe no KVM 4 (16 GB)
  com folga. Se algum app ficar pesado, ajuste `GUNICORN_WORKERS` no Coolify.
- **e-cobrança:** o `ssl_require=True` no `settings.py` continua correto, porque
  o Supabase tem SSL. Não precisa mudar nada neste repo pra rodar no VPS.
- **Câmbio:** com o VPS você passa a pagar em real (Hostinger BR), eliminando a
  exposição ao dólar que estava encarecendo seu custo no PythonAnywhere.

## Migracao com PRODUCAO ATIVA (e-metalurgicaservicos - regra de 21/10/2026)

App em uso real (2 empresas) no PythonAnywhere. Regras de ouro:

1. **Subir app + MySQL no Coolify com banco VAZIO**: pode ser em horario comercial. Zero impacto na producao (ambiente novo e isolado).
2. **Ensaio de restore**: mysqldump --single-transaction (leitura consistente, SEM travar o sistema legado) pode ser feito em horario comercial mesmo -> import no MySQL do VPS -> validar o sistema novo com a COPIA dos dados reais enquanto o legado segue atendendo.
3. **Corte final**: SOMENTE em janela acordada (fim de semana / apos expediente). Dump minutos antes -> import -> usuarios passam a usar o novo dominio. Manter PythonAnywhere ligado como backup por alguns dias antes de cancelar a assinatura.

## Li��es do app 2 (e-metalurgicaservicos - 21/10/2026)

- **Banco MySQL one-click do Coolify pode nascer 'Exited'** (nao sobe sozinho na primeira). SEMPRE conferir que o servico de banco esta RUNNING antes do Deploy do app. Sintoma se esquecer: app log com "django.db.utils.OperationalError: (2005, Unknown server host ...)". Solucao: Start no banco + Restart/Deploy no app.
- **Coolify v4.4.6**: opcao de colar env vars em lote se chama "Developer view" (nao "Raw Editor"). Domains fica em "Manage Domains".
- **Campo "Port" do Manage Domains = porta do CONTAINER (upstream)**, igual ao "Exposed ports" do app (8000) — NAO e a 443 publica (80/443 sao entrypoints automaticos do proxy). Domain SEM barra no final: "host/" + ":443" gera PathPrefix(/:443) + stripprefix errados -> 503 mesmo com app de pe.
- **DNS do MySQL entre containers = apelido (alias) de rede**: sintoma "Unknown server host 'mysql' (-3)" com banco RUNNING e mesma rede = alias ausente. Criar: `docker network disconnect coolify <container-db>` + `docker network connect --alias mysql coolify <container-db>`. Caveat: se o servico de banco for RECREADO no Coolify, conferir/aplicar de novo.
- **Migrations "Generated manually" sao suspeitas**: declarar TODAS as dependencias cross-app. financeiro/0006 faltava dep de servicos/0003_formapagamento -> "Related model cannot be resolved" so em banco NOVO (no antigo nunca estourou). Testar migrate do zero antes de subir app novo.
- **Ladder de erros do app no Coolify**: (2005) Unknown host -> rede/alias do banco. (1044) Access denied to database -> rodar CREATE DATABASE + GRANT como root (init do MySQL nao completou no primeiro boot 'Exited'). App DE PE mas 503 externo -> `docker inspect <container> --format '{{json .Config.Labels}}'` e comparar regra/upstream com um app funcional.
- **Pendencia de higiene**: http:// responde 200 sem redirect pra https nos 2 apps (sslip.io) — reavaliar toggle "Redirect HTTP to HTTPS".
- **CHECKLIST OBRIGATORIO por app antes do deploy**: (1) volume de /app/media, (2) rota /media/ INCONDICIONAL no urls.py (fora de `if settings.DEBUG` — o helper static() do Django retorna [] com DEBUG=False e o logo/banner da 404 mesmo com arquivo no disco; metalurgica caiu nisso, fix commit 7d9aa25 igual ao 8802332 do e-cobrancas), (3) pasta media copiada do PA (dump NAO leva arquivos, so caminhos).
- **Herodc do Coolify (Developer view)**: o placeholder COLE_AQUI_A_SENHA_DO_MYSQL precisa ser TROCADO antes de copiar a saida pro Coolify. Sintoma se esquecer: erro 1045 "Access denied ... using password: YES". Correcao: env var DB_PASSWORD + Deploy (restart NAO recarrega env var - embutida na criacao do container).
- **1045 mesmo com usuario existindo (SELECT user,host mostra appuser@'%')**: senha do app nao bate - causas: bloco heredoc colado 2x no Developer view (DUPLA entrada de DB_PASSWORD, placeholder sendo a ultima e "vencendo"), copia suja (espaco/aspas), ou env nova salva mas so deu Restart (env antiga ainda no container). Conserto à prova de bala (hotelaria,22/10): no mysql root: CREATE DATABASE IF NOT EXISTS <db> + ALTER USER 'appuser'@'%' IDENTIFIED BY '<senha nova>' + GRANT ALL + FLUSH PRIVILEGES; no app: apagar TODAS as entradas DB_PASSWORD duplicadas, colar UNICA senha nova, DEPLOY (nao Restart). Prevencao: colar bloco uma so vez + conferir duplicatas/placeholder antes do Save.
- **Painel Credentials do MySQL (Coolify UI) e so ROTULO**: o proprio aviso amarelo la diz "Changing values here does not update MySQL" - mexer ali nao altera a senha do banco. Fontes de verdade = (1) senha DENTRO do MySQL (ALTER USER via root) e (2) env DB_PASSWORD do app. As duas precisam BATER; o painel e so marcacao pra backups (boa pratica: sincronizar o painel apos o ALTER USER, como o usuario fez). Sintoma de desalinhamento: 1045 persistente mesmo apos "mexer em tudo".
- **Botao "Update Variable" do Coolify fica CINZA se o valor digitado == atual** (nao e bloqueio! so indica "nada mudou" - campo mascarado engana, parece readonly). E se a env ja contem a senha certa, o problema e o BANCO estar divergente.
- **Sincronizar senha DB := app ENV SEM nunca digitar/mostrar a senha** (funciona mesmo com caractere especial, zero erro de pareamento): `APP=$(docker ps -a --format '{{.Names}}' | grep <UUID-do-app>); DBPW=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' $APP | grep '^DB_PASSWORD=' | cut -d= -f2-); DB=<container-do-db>; docker exec -i -e MYSQL_PWD="$(docker exec $DB printenv MYSQL_ROOT_PASSWORD)" $DB mysql -uroot -e "ALTER USER 'appuser'@'%' IDENTIFIED BY '$DBPW'; GRANT ALL PRIVILEGES ON <db>.* TO 'appuser'@'%'; FLUSH PRIVILEGES;"` - depois so esperar o auto-restart do app (ou Restart). Hotelaria: a env ja tinha a senha nova (24 chars = openssl base64 18) e o ALTER USER original NUNCA tinha rodado - 1045 persistente ate esta sincronizacao.
- **COLISAO DE ALIAS = causa raiz do 1045 infinito do hotelaria (22/10)**: ontem foi criado o alias manual `mysql` no DB do metalurgica (fix do 1044); hoje o app do hotelaria com DB_HOST=mysql resolveu na rede `coolify` pro BANCO DO METALURGICA -> senha do hotelaria nunca bate la -> 1045 eterno MESMO com senha igual nos dois lados (o sync "SENHA SINCRONIZADA" acertou o banco certo, mas o app nunca chega nele). Verificar quem responde pelo apelido: `docker network inspect coolify -f '{{range .Containers}}{{println .Name "->" .Aliases}}{{end}}'`. CONCERTO: DB_HOST = NOME DO CONTAINER do proprio DB (estavel; ex. liwwuter3juvactjgyngjnpb). REGRA pra todos os apps: NUNCA hostname generico (`mysql`, `db`) na rede Coolify com + de 1 banco - usar nome de container ou apelido UNICO por app. Como a autenticao falha ANTES de qualquer query, o banco alheio nunca e tocado (metalurgica ilesa).
- **Dump PA antigo (utf8mb3) x schema VPS (utf8mb4) = erro3780 "FK incompatible"** (e-hotelaria,22/10): no PA tudo e utf8mb3 (dump e migrate la); no VPS o DB default e utf8mb4 e o migrate (boot do app) cria o schema em utf8mb4; o dump importa em ordem alfabetica e o PRIMEIRO FK pra tabela referenciada encontra ainda a versao do migrate (utf8mb4) -> charset cruzado =3780 no CREATE (o SET FOREIGN_KEY_CHECKS=0 do dump NAO burla -3780 e DDL). Sintoma: `Referencing column 'X' and referenced column 'Y' ... are incompatible`. CONSERTO: (1) `sed -i 's/DEFAULT CHARSET=utf8mb3/DEFAULT CHARSET=utf8mb4/g' dump.sql` (inventario: `grep -o 'DEFAULT CHARSET=[a-z0-9_]*' dump.sql | sort | uniq -c`; mb3->mb4 = zero perda), (2) DROP DATABASE + CREATE ... CHARACTER SET utf8mb4 (mata schema parcial do migrate e do import), (3) re-import. Apps da mesma era (PocosManut, e-clubecampestre, e-oficinas...) provavelmente vao passar por isso. (metalurgica nao caiu: dump dela ja era utf8mb4.)
- **Corte de app24/7 (hotelaria22/10, modelo pra PocosManut/clube etc.)**: janela REAL = ~5 min (dump321K ~1s, mídia2MB, import segundos) - nao exige "noite sem uso", so menor movimento (04h) + aviso pro time. SEQUENCIA: (0) recado (modelo: sistema INDISPONIVEL ~5min + novo endereço); (1) PA aba Web -> **Stop web app** = trava real anti-escrita (nao depende da disciplina de ninguem; o console continua funcionando); (2) PA: dump fresco (host geficogestor.mysql.pythonanywhere-services.com) + `tail -1` = "-- Dump completed" + scp dump + scp -r media; (3) VPS: sed utf8mb3->utf8mb4 (SEMPRE - dump do PA nasce mb3) + DROP/CREATE utf8mb4 + import + docker cp media; (4) validacao login + registro de teste; (5) time passa a usar a URL nova; PA fica PARADO como backup (reverter = Start no PA + volta pra URL antiga = perda zero; unico risco de reverter = registros ja criados na URL nova). PA parado ANTES do dump = impossivel registro perdido entre dump e troca.
- **AGENDA FIXADA (22/10)**: (a) **corte METALURGICA = sabado 24/10 a tarde (~14h)** - runbook: PA Stop web -> dump `geficogestor$emetalurgicaservico_db` (host geficogestor.mysql.pythonanywhere-services.com) -> scp dump+media -> VPS: sed preventivo + DROP/CREATE emetalurgicaservico_db utf8mb4 + import + docker cp (DB d6ybnxm8sknmy9nspqdca4gp, app grep jw3tgji9u5btglde0nhijxxn) -> validacao -> URL nova -> PA parado como backup; (b) **corte HOTELARIA = janela a negociar com o hotel** (usuario vai pedir; acessam hoje por https://ehospedaria-geficogestor.pythonanywhere.com/ = troca simples de URL, mensagem pronta); se o hotel fechar sabado, juntar os 2 cortes no mesmo dia (~5-10 min cada). PENDENTE p/ metalurgica: confirmar qual URL os users usam hoje (PA subdomain vs ivcsofthouse.com bloqueado no registrador).
- **DOMINIO REAL ivcsofthouse.com - diagnostico (22/10, via RDAP verisign)**: status `client hold` desde **09/04/2026 = exatos15 dias apos registro em25/03/2026 = classico ICANN WHOIS contact verification nunca confirmada** (NAO e pagamento - valido ate25/03/2027). Registrador: **Squarespace Domains II LLC**. Nameservers ainda `NS-CLOUD-A*.GOOGLEDOMAINS.COM` (legado Google Domains - provavel trocar pros do Squarespace apos liberacao). PROCEDIMENTO: (1) account.squarespace.com -> Domains -> banner "Verify your contact information", (2) e-mail+SPAM de marco/2026 -> link de confirmacao ICANN, (3) se nada: Live Chat squarespace.com/contact com script: "My domain IVCSOFTHOUSE.COM has shown clientHold status in WHOIS since April 9, 2026 and does not resolve. Could you check the reason and lift the hold? I see no pending actions in my dashboard." Prazo: minutos a48h. APOS liberar: conferir whois sem hold -> trocar NS pros do Squarespace (se googledomains mortos) -> A record -> 187.127.63.185 (apex+subdominios) -> Coolify Manage Domains -> cert automatico. **Corte de sabado USA o sslip.io (nao bloqueia - domínio real = upgrade posterior de5min sem tocar em dados).**
- **ESTRATEGIA DE DOMINIO v2 (23/10)**: usuario PERDEU acesso ao ivcsofthouse.com (registrado via conta Google ligada a assinatura Google Empresas cancelada; e-mail do registrador inacessivel -> clientHold eterno; recuperacao = chamado Squarespace com comprovantes, OPCIONAL/baixa prioridade). NOVO: **ivcsofthouse.com.br via Hostinger** (https://cart.hostinger.com/pay/e384cc82-c567-4979-aeea-424a89bb2554) - funciona igual pro proposito (LE suporta .com.br; Hostinger tem editor DNS; .br = mais confianca p/ clientes BR). **GOTCHA .br: Registro.br manda e-mail de VALIDACAO do titular pos-registro; sem confirmar = SUSPENSO (igual clientHold!) - checar inbox+SPAM.** REGRA DE OURO (licao da perda): registrar sempre com e-mail PESSOAL controlado + senha em gerenciador de senhas. PLANO: sabado corte via sslip (dominio novo nao estara pronto); semana seguinte: hPanel DNS (A: metalurgica/hotelaria -> 187.127.63.185) -> Coolify Manage Domains ADICIONA dominio real MANTENDO sslip (paralelo = troca sem risco) -> cert automatico -> so entao comunicar time -> remover sslip depois de confianca. **STATUS23/10: COMPRADO na Hostinger - ainda processando no Registro.br (NXDOMAIN ~1h pos-compra = normal); pendencias imediatas: (1) validar e-mail do Registro.br (inbox+SPAM), (2) criar registros A no hPanel DNS Zone (pode criar ja - ficam dormindo ate ativar); checar ativacao via rdap.registro.br/domain/ivcsofthouse.com.br + dns.google/resolve?name=ivcsofthouse.com.br&type=NS.** **NOME ESCOLHIDO (23/10): `gservicos`** (generico p/ gestão de serviços - metalurgica, oficinas, graficas etc.). Endereços: gservicos.187-127-63-185.sslip.io (provisorio, adicionar no Coolify MANTENDO metalurgica.* ate confianca) e gservicos.ivcsofthouse.com.br (definitivo). Registros DNS (Hostinger): A gservicos/hotelaria/ecobrancas -> 187.127.63.185. SABADO: de manha checar se o definitivo esta 100% (ativo+DNS+cert) -> se sim, time recebe direto o definitivo; senao sslip e definitivo sai na semana seguinte. Renomear = SO o subdominio (projeto/banco/repo do Coolify ficam - mudar = risco sem beneficio).
- **Nomes de container no Coolify**: app = <UUID-32chars>-<timestamp> (o timestamp SOBE a cada Deploy = prova visual de que o deploy rodo; o UUID e estavel, entao `grep <UUID>` funciona antes/depois); DB = UUID puro sem timestamp (imagem aparece como "mysql:8"). Descobrir tudo: `docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'`. NAO usar `grep mysql` cego pra achar o DB quando ha mais de um MySQL na maquina (o do metalurgica aparece so como hash de imagem e nao casa - deu sorte de dar certo no app certo; usar sempre o container exato do projeto).

## Rename + diagnostico de dominio (23/10/2026 - tarde)

- **RENOME `metalurgica` -> `gservicos` (23/10)**: usuario pediu nome generico (sistema serve metalurgica, oficina, grafica...). Renomear = SO o ENDERECO: subdominio no Coolify Manage Domains + env vars + registro A do Hostinger; projeto/banco/repo/containers do Coolify NUNCA mudam (mudar = risco sem beneficio, ninguem digita isso). **ENDERECO DO CORTE DE SABADO CONFIRMADO (23/10 15h37): `https://gservicos.187-127-63-185.sslip.io` = 200 com `<title>e-Metalurgica SaaS</title>`** (cert ok + app certo atras). Entrada antiga `metalurgica.187-...` ficou ORFA = 503 "no available server" -> APAGAR do Manage Domains (o sslip aceita qualquer subdominio, e so criar o novo e remover o velho).
- **Hostname novo no Coolify != Django aceita (400 DisallowedHost)**: sintoma = **HTTP 400 "Bad Request (400)" com `Server: gunicorn`** (HTML simples do Django) em TODO caminho - NAO e erro de servidor/proxy, e o Django rejeitando o Host. Fix: env `DJANGO_ALLOWED_HOSTS` (hosts separados por VIRGULA, sem espaco) E `DJANGO_CSRF_TRUSTED_ORIGINS` (URL completa `https://...` por virgula) no proprio app + **Deploy** (settings.py do metalurgica/hotelaria le as duas do ambiente). Valores usados (23/10): `DJANGO_ALLOWED_HOSTS=gservicos.187-127-63-185.sslip.io,localhost` e `DJANGO_CSRF_TRUSTED_ORIGINS=https://gservicos.187-127-63-185.sslip.io`. **REGRA: TODO hostname novo (sslip E dominio real) entra nas DUAS vars ANTES de divulgar a URL** - pendencia: acrescentar `gservicos.ivcsofthouse.com.br` (+ `https://...` no CSRF) quando o DNS virar, e o par equivalente no app do hotelaria.
- **Escada de diagnostico HTTP (body diz quem respondeu)**: 400 + `Server: gunicorn` = Django de pe rejeitando Host (ALLOWED_HOSTS). 503 texto puro `no available server` = Traefik acha o router mas NAO o upstream (porta errada no Manage Domains ou entrada orfa apontando pra container morto). 404 texto simples = host sem router nenhum. Erro de TLS `unable to verify the first certificate` = cert ainda nao emitido pra aquele hostname. Imprimindo sempre `status + server + body[:300]` da pra diagnosticar tudo de fora sem SSH.
- **Cert sslip na 1a emissao leva ~1-3 min**; se passar >10 min ainda com erro de TLS -> apagar e READICIONAR a entrada do dominio no Coolify (forca pedido novo; edicao fina pode nao re disparar o ACME) e conferir grafia exata (plural, sem barra, sem https:// dentro do campo, porta 8000). Falha de validacao do LE tem backoff (~1h) - ja vi o cert so firmar depois de re-save. Typos de grafia (gservico vs gservicos) criam entrada errada: sempre re-conferir a lista do Manage Domains apos salvar.
- **STATUS DOMINIO ivcsofthouse.com.br (23/10 ~15h15)**: Hostinger painel mostra "Ativo" + NS `hermes/artemis.dns-parking.com` + usuario validou e-mail da PROPRIA Hostinger; **MAS o Registro.br ainda NAO tem o dominio**: RDAP404 (metodo validado com controle `rdap.registro.br/domain/uol.com.br` = responde JSON) + `dns.google/resolve` NS/A = Status3 NXDOMAIN no `.br`. Print de pagina de estacionamento no navegador do usuario = provavel cache/ISP (nao bate com o registry). Resolucao: espera + se a noite de 23/10 sem progresso -> suporte Hostinger: "Meu domínio ivcsofthouse.com.br consta como Ativo no painel, mas ainda não aparece no whois do Registro.br e não resolve. Podem verificar o andamento da ordem de registro e se há pendência de validação de titular?". NAO bloqueia sabado (sslip e o plano A garantido). Checagem periodica: rdap + dns.google NS + A de gservicos.ivcsofthouse.com.br; negcache do `.br` = TTL15min (paciente entre consultas).
- **CHECKLIST dominio real (quando DNS virar)**: (1) registros A `gservicos/hotelaria/ecobrancas` -> 187.127.63.185 no hPanel, (2) dominios ja estao no Coolify Manage Domains (gservicos + hotelaria), (3) acrescentar os `.com.br` nas env ALLOWED_HOSTS/CSRF dos 2 apps + Deploy, (4) cert emite sozinho (Traefik re-tenta periodico), (5) testar os 3 URLs reais, (6) so ENTAO comunicar endereco final ao time.
- **REBRANDING EXECUTADO (24/10, 3 commits)**: troca de titulos/marca no e-metalurgicaservicos para "Gestão de Serviços SaaS" - `0e425b8` (5 textos: base.html title + home.html title/footer + login.html title/footer), `66512e8` (marca do topo home.html "GESTÃO DE SERVIÇOS SaaS" + icone fa-tools->fa-briefcase), `50d795d` (banner estatico `static/img/fundo-login.jpg` substituido por imagem neutra - aparece so pra NAO-logados; empresa logada usa o banner dela). LICAO: o 1o grep case-sensitive deixou passar "e-METALURGICA" em MAIUSCULAS - SEMPRE re-grep com -i quando trocar marca; e lembrete/boas praticas: imagem de fundo = ARQUIVO, substituir o jenome mantem zero mudanca de codigo. Validado24/10 15h36: ambas URLs gservicos 200 + title novo + marca nova. FALTA: hotelaria/ecobrancas `.com.br` sem cert ainda (re-save do domain entry dispara).
- **CORTE METALURGICA EXECUTADO COM SUCESSO (24/10, 17:30-17:40 ≈10min de janela): banco+media reais importados no VPS e time validou com login real** ("site no ar lindo e maravilhoso"). Sequencia roda da rodada: (1) dump ja previo + media mapeados; (2) PA Web -> Stop (trava anti-escrita PROVADA por sonda: PA URL virou 404 "Coming Soon: PythonAnywhere" = web app parado, nao 200); (3) dump `geficogestor$emetalurgicaservico_db` (host geficogestor.mysql.pythonanywhere-services.com) = 905K, `tail -1` = "Dump completed on 2026-10-24 17:32:40" (media 7.3M -> tar 2.8M); (4) scp pro VPS `/root/` (root@srv2077367 - senha do root, ~1s cada arquivo); (5) VPS: sed mb3->mb4 (grep -c = 0 sobras) + DROP/CREATE `emetalurgicaservico_db` utf8mb4 em `d6ybnxm8sknmy9nspqdca4gp` + import LIMPO (zero erro = silencio) + placar **27 tabelas** (hotelaria tinha 28); (6) media: tar xzf no host + `docker cp /root/media/. "$APP:/app/media/"` para `jw3tgji9u5btglde0nhijxxn-20261024T153421` + **check contagem 7/7 arquivos nos dois lados** (find | wc -l = conferencia de integridade barata e falsa-positiva zero... na real: garante que docker cp copiou TUDO); (7) validacao pelo usuario com login REAL + navegacao sem 500 (sem restart necessario - conexao por request; restart so se 500 pontual). **PA metalurgica FICA PARADO = backup** (reverter = Start no PA painel + avisar time; risco unico = cadastros feitos na URL nova perdidos na reversao). APP do container metalurgico `jw3tgji9u5btglde0nhijxxn-20261024T153421` (build 15:34 = deploy do rebranding); DB `d6ybnxm8sknmy9nspqdca4gp`.
- **PA-REVELACAO: NOMES REAIS DAS PASTAS NA HOME DO GEFIGOGESTOR (mapeados 17:28, `ls ~`)**: `e-metalurgicaservico` (SEM "s"!), `pocomanut` (nao PocosManut!), `efinanceiro` (sem hifen!), `e-locarro` (sem s!), `e-restaurantes`, `e-cadempresas`, `e-clubecampestre-multi` (sufixo "-multi"!), `e-gerenteservicos`, `e-oficinas`, `e-hospedaria`, `e-cobrancas`, `e-cobranca_mysql`, `logs`. LICAO: SEMPRE `ls ~` no PA antes de montar comandos de dump/media - nomes difere do repositorio local/UML mental, e um s errado no caminho faz comandos falharem em silencio (o `du` do metalurgico com nome errado so~ nao imprimiu nada). Idem em cada app futuro.
- **URL antiga do time da metalurgica (pro aviso/historico): `https://emetalurgicaservico-geficogestor.pythonanywhere.com/`** - de PARADA (404 Coming Soon). Comunicacao pro time: novo endereco = `https://gservicos.ivcsofthouse.com.br/` (backup: gservicos.187-127-63-185.sslip.io). PENDENCIAS pos-corte: (a) re-save domain entries p/ cert de hotelaria+ecobrancas `.com.br`; (b) PA metalurgico parado alguns dias antes de se mexer nele; (c) limpar dumps velhos do /root do VPS quando confianca estabelecida; (d) hotelaria = mesmo runbook prontinho (dump 321K/28 tabelas/media 2.07M; URL do time: https://ehospedaria-geficogestor.pythonanywhere.com/, anunciado pra janela com o hotel).
- **CORTE HOTELARIA EXECUTADO COM SUCESSO (24/10, 18:04-18:17, mesma noite do metalurgico - aula de repeticao: Fase A->6 rodou de primeira sem improviso)**: (A) Manage Domains conferido + env `DJANGO_ALLOWED_HOSTS`/`DJANGO_CSRF_TRUSTED_ORIGINS` do app hoteleria corrigidos (tava faltando os `.com.br`) + Deploy; (1) PA Web -> Stop em `ehospedaria` (trava PROVADA: 404 "Coming Soon" as 18:13 via sonda); (2) dump `geficogestor$ehotelaria_db` = **326K** (ensaio 321K = uso real normal), `tail -1` = completed 18:11:47; media tar 1.9M; (3) scp; (4) sed mb3->mb4 (grep-c = 0) + DROP/CREATE `ehotelaria_db` utf8mb4 no DB `liwwuter3juvactjgyngjnpb` + import limpo + **28 tabelas = bateu EXATAMENTE o ensaio**; (5) media: JEITO SEGURO desta vez: `rm -rf /root/media` antes do extract (evita mistura com a media do metalurgico copiada antes no mesmo dia - MUITO IMPORTANTE quando 2 cortes no mesmo dia usam o mesmo `/root/media` como caminho-temp!) + `docker cp` com `rm -rf /app/media/*` dentro do container antes + conferencia **10/10 arquivos** (2.07MB ✓) no `2ghnhyqbfpbql0n6m56i9gon-20261023T160530`; (6) validacao pendente do login real pelo hotel. ESTADO POS-CORTE: PA hotelaria parado = backup; time usa `https://hotelaria.187-127-63-185.sslip.io` por ora; cert de `hotelaria.ivcsofthouse.com.br` AINDA nao firmou apos re-save >20min (delete+re-add da entry = proxima tentativa - as entradas do gservicos/metalurgica nasceram limpas e firmaram; a do hotelaria pode ter grafia/estado estranho salvado). **RESOLVIDO 18:27 - AUDITORIA DO USUARIO: as env vars tinham sido SALVAS mas SEM Deploy (regra de ouro de novo: env var so vira real com DEPLOY!) - apos o Deploy, cert+Django alinharam -> 200 "Bem-vindo | e-Hotelaria SaaS". ENDERECO DEFINITIVO DO HOTEL ATIVO desde 24/10 (18:27): https://hotelaria.ivcsofthouse.com.br/. ecobrancas .com.br segue pendente (opcional - nunca ajustamos o app dele)**. **PLANO PS-CORTES CONFIRMADO (24/10, relato do usuario): pocalmantut = PROXIMO (pre-voo local ja); e-clubecampestre-multi = CORTE NA SEGUNDA-FEIRA (27/10) pois o clube trabalha nos FIMES DE SEMANA (mondrama nessa - janela tranquila segunda, cliente off); hotel cliete ja trabalha no endereco novo.**

## Prioridades de migracao definidas (21/10/2026 - para os proximos apps)

Ordem: um por dia/app, com os pre-voos da auditoria ANTES do primeiro deploy.

**Producao (prioridade maxima):**
1. **e-hotelaria** — pre-voos: rota media incondicional (setup/urls.py:19), DEBUG=not ON_PYTHONANYWHERE vira True no Docker (setup/settings.py:21) -> env DJANGO_DEBUG, credencial DB hardcoded (setup/settings.py:84-87) -> env.
2. **PocosManut** — pre-voos: rota media (pocomanut/urls.py:34), local_settings.py:2 força DEBUG=True (anula env) -> remover do container/condicionar, volume+env padrao.
3. **e-clubecampestre** — pre-voos: rota media (clube_manager/urls.py:32), DEBUG default True (settings.py:27/.env) -> env, volume+env padrao.

**Depois (sem pressa, tentando achar clientes):** e-oficinas, e-locarros, e-gerenteservicos, e-financeiro, e-restaurantes.

**PENDENTE do app 2:** cortar e-metalurgicaservicos (Fase 3) — janela acordada (fim de semana/apos expediente): dump fresco + re-sync da pasta media + usuarios pro novo dominio; PA fica de backup uns dias.

## Auditoria de uploads/media — 8 apps pendentes (21/10/2026)

**Boas noticias gerais:** todos usam disco LOCAL (FileSystemStorage, sem S3/storages), MEDIA_ROOT relativo a BASE_DIR (encaixa no volume /app/media), sem URLs absolutas de arquivos apontando pro PA, sem limites de upload custom (Django default; Traefik nao limita corpo) — ou seja, **a receita volume + rota + docker cp serve pra todos**.

**Problemas recorrentes a corrigir ANTES do deploy de cada app:**

1. **Rota /media/ condicional a `if settings.DEBUG` nos TODOS os 8**: PocosManut (pocomanut/urls.py:34), e-oficinas (core/urls.py:17), e-locarros (core/urls.py:24), e-hotelaria (setup/urls.py:19), e-gerenteservicos (core/urls.py:27), e-financeiro (core/urls.py:23), e-clubecampestre (clube_manager/urls.py:32), e-restaurantes (setup/urls.py:23) -> tornar incondicional (fix identico aos commits 8802332 e 7d9aa25).
2. **DEBUG=True por omissao/hardcoded** (risco de tracebacks em producao): e-locarros (core/settings.py:33) e e-gerenteservicos (core/settings.py:30) e e-financeiro (core/settings.py:30) = True hardcoded; e-hotelaria (setup/settings.py:21) e e-restaurantes (setup/settings.py:9) = `DEBUG = not ON_PYTHONANYWHERE` (vira **True** no Docker!); PocosManut (local_settings.py:2) força True; e-oficinas (.env:2) e e-clubecampestre (settings.py:27) default True -> padrao env-driven `DJANGO_DEBUG=False` igual metalurgica.
3. **Credencial DB PA hardcoded no repo**: e-hotelaria (setup/settings.py:84-87) e e-restaurantes (setup/settings.py:64-66) -> mover pra env vars no estilo metalurgica + rotacionar senha pos-corte.
4. **Escala de uploads (FileField/ImageField)**: e-gerenteservicos 6, PocosManut 4, e-locarros 5, e-clubecampestre 5, demais 3 cada — nada fora do padrao.
5. **Regra de corte pra app com upload**: no dia do corte re-sincronizar a pasta media DE NOVO (novos arquivos sobem no legado entre o ensaio e o corte) junto com o dump fresco.
- **Volume mount**: nome sem espacos invisiveis (o vilao classico); usar nome curto tipo 'media'.
- Deploy Dockerfile+mysqlclient compilado: ~1 min no VPS (cache ajuda).

## Lições do app e-clubecampestre-multi (26/10/2026) — o mais complexo até agora

**Status: MIGRADO — CONCLUÍDO (26/10/2026).** https://eclubecampestre.ivcsofthouse.com.br (HTTPS ok, cert automatico) + sslip.io reserva. PA parado como backup. Validacoes finais pelo cliente: login OK, PDF/WeasyPrint OK, cardapio+QR OK, midia 128 arquivos servindo (HTTP 200) via volume `eclubecampestre-media` montado em `/app/media`.

### 1. Branch main x master = armadilha classica (custou caro aqui)
- Repo `Ivanildo-Lab/e-clubecampestre-multi` tinha DUAS branches divergentes: `main` (features do cliente: cardapio QR, ficha socio) e `master` (correcoes de infra Docker que eu fiz).
- O Coolify buildava `master` -> deploy OK mas SEM as features (app "desatualizado"). O usuario pushava pra `main` -> "nada a fazer".
- **Resolucao:** merge `master` -> `main`, resolver conflitos, e **empurrar o MESMO commit pras duas branches** (`git push origin main` + `git push origin main:master`). Ambas iguais = zero confusao.
- **Regra pra proximos apps:** decidir UMA branch (a default do repo) e o Coolify sempre nela. Melhor ainda: repo com uma branch so.

### 2. Coolify faz deploy AUTOMATICO no git push (webhook)
- Usuario nao clicou em nada: o push pro GitHub disparou o deploy sozinho. Bom (fluxo = git push e pronto) mas perigoso se a branch estiver errada.
- **Consequencia pratica:** o container novo substitui o antigo, e o antigo e APAGADO junto com tudo que estava em /app/media.

### 3. /app/media DENTRO do container = temporario (sumiu tudo no redeploy)
- A midia copiada com `docker cp` morre no proximo deploy. E aconteceu: app no ar, imagens zeradas, container novo vazio.
- Backup no VPS: `/root/media/eclubecampestre` (**sem hifeno** — o nome com hifeno nao existe, foi o que causou "No such file" no primeiro repair).
- **Correcao definitiva:** Persistent Storage no Coolify -> volume `eclubecampestre-media` montado em `/app/media`. Ai a midia sobrevive a qualquer deploy. Depois de montar o volume, refazer o `docker cp` (volume novo nasce vazio).

### 4. WeasyPrint precisa das libs RUNTIME no estagio final do Dockerfile
- Build passa sem elas (so da erro em runtime ao gerar PDF). Adicionar no estagio final (alem das builder):
  `libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 libfreetype6` (+ `libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info` que ja la estavam).

### 5. Whitenoise: CompressedStaticFilesStorage, NUNCA CompressedManifest
- `CompressedManifestStaticFilesStorage` falha no collectstatic por causa de source maps ausentes no adminlte (bootstrap-datepicker `.map`).
- `WHITENOISE_MANIFEST_STRICT=False` NAO resolve -> trocar a classe do storage.

### 6. ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS: strip + fallback hardcoded
- Env CSV com espacos ("a, b") quebra Django (DisallowedHost silencioso) -> helper `_csv()` que split(',') e strip() em tudo.
- Fallback hardcoded dos dominios reais quando a env vem vazia -> app nunca fica 400 por env esquecida.
- Healthcheck do Traefik bate no IP do container sem Host header -> 400/Django. `0.0.0.0` em ALLOWED_HOSTS resolve (Django aceita como wildcard).

### 7. ACME/LetsEncrypt: um dominio sem DNS ABORTA o cert de todos
- `www.eclubecampestre.ivcsofthouse.com.br` sem registro -> erro no issuance e o cert principal nao saia.
- **Fix:** so cadastrar no Coolify os dominios que TEM registro DNS apontando pro VPS.

### 8. Coolify v4 nao tem botao "Generate SSL" por dominio
- SSL e automatico: dominio com protocolo `https` no campo Domains + resolver `letsencrypt` na instancia. Trocar o protocolo de http pra https (sem redeploy, so Save) ja dispara a emissao.
- Dominio real ja funciona: `eclubecampestre.ivcsofthouse.com.br` -> A record -> 187.127.63.185.

### 9. SEGURANCA: .env.example com segredos REAIS commitado
- No meio da briga das branches, um commit antigo (`a335276`) subiu `.env.example` com SECRET_KEY e DB_PASSWORD de verdade. Repo privado, risco baixo, MAS consta do historico.
- **PENDENTE (pos-migracao, sem pressa):** rotacionar SECRET_KEY (Coolify env) + senha do MySQL (ALTER USER + atualizar env) — ver GESTAO-BANCO.md.

### 10. Ordem de reparo de midia perdida (receita reaproveitavel)
1. `docker ps -a | grep <app>` -> ver se o container antigo ainda existe (Exited) -> se sim, `docker cp` de la.
2. Se nao: achar backup no disco (`ls /root/media/`, `find /root /tmp -iname "*<app>*"`).
3. Se nao achar nada: re-extrair do PA (web parado mas filesystem intacto).
4. `docker cp /root/media/<app>/. "$APP:/app/media/"` e conferir com `find /app/media -type f | wc -l`.
5. Volume permanente no Coolify + re-copia (o volume nasce vazio).

## DECISAO FINAL — encerrar conta PythonAnywhere (26/10/2026)

**Decisao do Ivanildo:** os 7 apps migrados (e-cobrancas, gservicos, e-hotelaria, pocomanut, e-gerenteservicos, e-clubecampestre, e-cadempresas) sao os UNICOS em producao. **Os demais projetos NAO serao migrados** — ficam no GitHub + local, sem uso, ate decidir o que fazer. Depois de **1 semana de margem de observacao** (a partir de 26/10 -> corte por volta de 02/11/2026), eliminar os projetos do PA e **fechar a conta**.

**Checklist de encerramento (ordem importa):**
1. **Semana de observacao:** monitorar os 7 apps no VPS (logs do Coolify, erros, PDFs, uploads).
2. **Agendar backups automaticos ANTES de fechar** (cron no VPS): `backup-mysql.sh` (os 6 bancos MySQL) + **backup do SQLite do e-cadempresas** (`cp /var/lib/docker/volumes/<vol>-data/_data/db.sqlite3` ou tar do mountpoint — 7o banco!) + tar da media -> copia offsite (rclone/scp pro PC ou nuvem). O VPS sozinho NAO e backup (se o VPS morrer, perde tudo — production + backup juntos).
3. **Exportar tudo que existe no PA uma ultima vez:** `/home/geficogestor` inteiro (tar) — inclui os projetos NAO migrados (codigo, media, configs) + dumps frescos dos bancos MySQL (6) + o db.sqlite3 original (7o, mas ja copiado no corte). Baixar pro PC e guardar (HD + nuvem).
4. **Conferir GitHub:** todos os projetos (migrados e nao) com o codigo la. O PA e o ultimo lugar com possivel codigo inpushado — por isso o passo 3.
5. **Cancelar assinatura** no PA (Account -> Cancel subscription) e depois **excluir a conta** (Account settings -> Delete account).
6. Apos o fecho: sobram os pendentes pos-migracao (rotacionar SECRET_KEY/DB_PASSWORD do e-clubecampestre, redirect HTTP->HTTPS dos dominios reais, Adminer por app).

**Risco aceito:** os dumps do PA dos 6 apps de producao viram historia apos o corte (dados frescos vivem no VPS). Por isso o backup offsite do VPS e OBRIGATORIO antes de fechar a conta.

## Lições do app e-cadempresas (26/10/2026) — o mais simples (7º app no ar)

**Status: MIGRADO — CONCLUÍDO (26/10/2026).** https://ecadempresas.ivcsofthouse.com.br (HTTPS/cert automatico) + sslip.io (variante com PONTOS). PA no ar como backup (corte dos dados feito; ver lista "encerrar PA" acima). Validacoes: login OK, lista 678 empresas/970 socios/465 tabelas, PDF xhtml2pdf OK, CRUD OK. Codigo: repo `Ivanildo-Lab/e-cadempresas`, branch `main` (commit pre-voo 9a330b6 + fix 7bdee22).

**Perfil do app:** Django 6 + **SQLite** (arquivo, sem MySQL!), sem uploads/midia, PDF via xhtml2pdf/reportlab (NAO WeasyPrint). O mais rapido da fila.

### 1. SQLite em Docker = VOLUME obrigatorio (banco = arquivo dentro do container)
- Sem volume, qualquer deploy zera o banco inteiro (clientes perdidos). MySQL dos outros apps tinha servico proprio; aqui o "banco" e um arquivo.
- Solucao: `ENV SQLITE_PATH=/app/data/db.sqlite3` no Dockerfile + settings le `os.environ.get('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3'))` (fallback = comportamento legado no PA/local) + volume Coolify em `/app/data`.

### 2. Coolify Stop REMOVE o container (nao fica nem Exited)
- `docker ps -a` nao mostra nada apos Stop -> `docker cp` falha ("must specify at least one container source") e comandos com $APP vazio quebram de formas confusas (ex: `docker exec ls` -> "No such container: ls").
- **Fix sem container:** copiar DIRETO no volume: `docker volume ls | grep <uuid>` -> `docker volume inspect <vol> --format '{{.Mountpoint}}'` -> `cp arquivo <mountpoint>/db.sqlite3`. App parado = arquivo fechado = zero risco.

### 3. Nomes de pacote Debian mudam entre versoes (2º caso na migracao!)
- Build falhou: `E: Unable to locate package libfreetype1-dev` no Debian 13/trixie -> nome correto e **`libfreetype-dev`**.
- **Diagnostico definitivo (reuso para qualquer erro de pacote):** `docker run --rm python:3.13-slim sh -c 'apt-get update -qq >/dev/null 2>&1; apt-cache search --names-only "NOME.*-dev"'` — testa no ambiente EXATO do build, sem chute.

### 4. sslip.io: a MESMA IP tem duas grafias (pontos E hifens) = hosts diferentes
- `ecadempresas.187.127.63.185.sslip.io` e `ecadempresas.187-127-63-185.sslip.io` sao legais igual, mas Host header diferente -> se ALLOWED_HOSTS tem uma e o usuario acessa a outra => **400 Bad Request** (log: `GET / 400` com referer da grafia errada).
- **Fix:** cadastrar AMBAS as variantes em DJANGO_ALLOWED_HOSTS e DJANGO_CSRF_TRUSTED_ORIGINS (e o dominio real). O cert sai do Coolify conforme os dominios cadastrados.

### 5. Regra de ouro do commit: NUNCA `git add -A` em repo com db/binarios
- `db.sqlite3` rastreado no git aparece como ` M` (dados locais de teste). Commit seletivo: `git add Dockerfile .env.example settings.py ...` so nos arquivos do pre-voo. `__pycache__` igual.

### 6. Settings env-driven mantendo compat com PA durante a margem
- SECRET_KEY/DEBUG/ALLOWED_HOSTS/CSRF via `os.environ` com fallback = valores atuais -> PA continua funcionando ate o fecho, e o Coolify ganha os overrides. DEBUG padrao **False** (o PA antigo vivia com DEBUG=True hardcoded — nenhum codigo dependia de DEBUG, confirmado por grep).
- STATICFILES_STORAGE (legado) trocado por dict STORAGES + `CompressedStaticFilesStorage` + proxy SSL/cookies secure — mesmo padrao vencedor dos apps anteriores.

**PENDENTE pos-migracao:** rotacionar SECRET_KEY do e-cadempresas (hardcoded antigo no historico do git).
