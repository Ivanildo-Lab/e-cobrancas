# Gestão do Banco MySQL no VPS (Coolify + Docker)

> Complementa o `MIGRACAO.md`. Foca em: **onde roda o MySQL**, **como acessar
> com segurança via web (Adminer)** e **como fazer dumps individuais por app**.

---

## 1. Onde roda o MySQL — e por que isso muda o `DB_HOST`

No PythonAnywhere, o MySQL era um serviço gerenciado que seus apps acessavam por
um hostname tipo `seuusuario.mysql.pythonanywhere-services.com` (o genérico
`mysql.pythonanywhere.com` só funciona de dentro do próprio PythonAnywhere —
de fora use o formato com `-services`, sujeito ao seu usuário).

No VPS com Coolify, o MySQL roda como **outro container na mesma rede Docker**.
Isso é mais seguro (o MySQL não fica exposto na rede pública) e mais limpo.

### ⚠️ A pegadinha do `127.0.0.1` — e do hostname genérico `mysql`
Dentro de um container, `127.0.0.1` aponta para o **próprio container**, não pro
MySQL. E o nome genérico do serviço (`mysql`) **também é armadilha**: se QUALQUER
outro container da rede Coolify tiver um alias `mysql` (ex.: conserto manual
feito pra outro app), o DNS resolve pro **banco ERRADO** e o sintoma é um `1045`
eterno **mesmo com a senha certa nos dois lados** (colisão de alias — e-hotelaria,
22/10/2026).

**Regra:** no `DB_HOST` use o **NOME DO CONTAINER do SEU MySQL** (estável; aparece
em `docker ps`) ou um apelido **único por app**:
`docker network connect --alias <unico> coolify <container>`.

Exemplo de `DATABASE_URL`/`DB_HOST` por app:

| App | DB_HOST | DB_NAME |
|---|---|---|
| e-metalurgicaservicos | `mysql` | `emetalurgicaservico_db` |
| outro-app | `mysql` | `outro_banco` |

> Todos os 14 bancos podem morar no **mesmo container MySQL** (uma instância,
> 14 databases). Cada app aponta pro mesmo host, com seu próprio `DB_NAME`.

### Como criar o MySQL no Coolify
1. No projeto do Coolify, adicione um serviço **MySQL** (one-click).
2. Defina usuário/senha/root. Anote a senha.
3. Dentro dele, crie os 14 databases (pelo Adminer ou `CREATE DATABASE`).

---

## 2. Gerenciador web: Adminer (recomendado no lugar do Workbench)

Você perguntou sobre phpMyAdmin. A recomendação é o **Adminer**: faz tudo igual
(mais navegar nos bancos, queries, importar/exportar SQL), mas é **muito menor e
com superfície de ataque bem menor** que o phpMyAdmin, além de oficial e ativo.

Setup: veja `deploy/adminer-compose.yml`. Rode como serviço do Coolify, na mesma
rede do MySQL, com domínio privado (ex.: `https://db.seudominio.com`).

Conexão no Adminer:
- **Servidor:** `mysql` (o serviço do Coolify)
- **Usuário / senha:** os do MySQL
- **Banco:** escolhe o que quer gerenciar (um dos 14)

### 🔒 Segurança — NÃO exponha o Adminer sem isso
Um gerenciador web de banco exposto na internet é alvo número 1 de bots. Ao menos
faça **todos** estes itens:

1. **HTTPS obrigatório** — o Coolify já faz via Let's Encrypt no domínio.
2. **Senha de banco forte e única** (nunca reutilize a do PA).
3. **Restrinja o acesso** (escolha UMA):
   - **Cloudflare Access** (grátis até 50 usuários) — só você loga antes de ver o Adminer.
   - **IP allowlist** — no firewall ou no proxy, libere só seu IP/fixo.
   - **Basic auth extra** — uma camada de senha antes do Adminer.
4. **fail2ban** — bloqueia IPs após tentativas de login falhadas:
   ```bash
   sudo apt install fail2ban -y
   # configuring filtro para o Adminer/PHP e ativando (veja docs do fail2ban)
   sudo systemctl enable --now fail2ban
   ```
5. **Ligue só quando usar** — se não vai mexer no banco hoje, desative o serviço/domínio
   do Adminer no Coolify. Menos tempo exposto = menos risco.
6. (Alternativa máxima de segurança) Mantenha o Adminer **só em localhost** no VPS e
   acesse via túnel SSH — aí ele nunca fica público. Mais seguro, porém menos "web".

---

## 3. Dumps individuais por app (confirmando sua abordagem)

Como cada app atende uma área diferente e tem estrutura própria, vamos migrar **um
app por vez, com dump individual**. Isso é o mais seguro — você valida cada app
antes de partir pro próximo.

### Exportar no PythonAnywhere (por app)
```bash
mysqldump -u USUARIO_PA -p --single-transaction NOME_DO_BANCO > nome_app.sql
```

### Importar no VPS (por app)
Com o Adminer: abra o banco de destino → aba **Importar** → cole/envie o `.sql`.
Ou via CLI dentro do container MySQL:
```bash
docker exec -i NOME_CONTAINER_MYSQL mysql -u appuser -p NOME_DO_BANCO < nome_app.sql
```

### Checklist por app na migração
- [ ] Dump gerado no PA.
- [ ] Banco criado no MySQL do Coolify.
- [ ] Dump importado (Adminer ou CLI).
- [ ] `DB_NAME/DB_USER/DB_PASSWORD` configurados no Coolify pro app.
- [ ] App no ar, login testado, dados conferidos.
- [ ] Só então migra pro próximo app.

---

## 4. Backup automático dos 14 bancos

Use o `deploy/backup-mysql.sh`. Como agora o MySQL é um **container**, o dump é
feito de dentro dele. Ajuste o script para rodar via `docker exec`:

```bash
# Exemplo: dump de todos os bancos do container MySQL
docker exec NOME_CONTAINER_MYSQL sh -c 'exec mysqldump -u appuser -p"SENHA" --single-transaction --all-databases' | gzip > /var/backups/mysql_$(date +%F).sql.gz
```

Agende no cron do VPS e **guarde o backup fora do VPS** (outro servidor/storage).
Regra de ouro: backup que não está em outro lugar não é backup.
