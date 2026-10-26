#!/usr/bin/env bash
# ------------------------------------------------------------------
# backup-mysql.sh
# Backups automáticos de TODOS os bancos MySQL do VPS (os 14 apps).
# Uso: configure no cron, ex. todo dia às 3h:
#   0 3 * * * /usr/local/bin/backup-mysql.sh
# ------------------------------------------------------------------

set -euo pipefail

# --- Configuração ---
BACKUP_DIR="/var/backups/mysql"      # Onde os dumps ficam
USER="appuser"                       # Usuário MySQL para dump
MYSQL_PASS_FILE="/root/.my.cnf"      # Arquivo com senha (mais seguro que -p na linha)
RETENTION_DAYS=30                    # Quantos dias de backup manter
DATE="$(date +%Y-%m-%d_%H-%M-%S)"

# --- Prepara ---
mkdir -p "$BACKUP_DIR"

# Se existir arquivo de senha do MySQL, usa ele (evita senha no histórico/shell)
MYSQL_OPTS=(--user="$USER")
if [ -f "$MYSQL_PASS_FILE" ]; then
    MYSQL_OPTS+=(--defaults-file="$MYSQL_PASS_FILE")
fi

# Lista todos os bancos, excluindo os de sistema do MySQL
DATABASES=$(mysql "${MYSQL_OPTS[@]}" -N -e \
    "SHOW DATABASES WHERE Database NOT IN ('information_schema','mysql','performance_schema','sys');")

echo "==> Iniciando backup em ${DATE}"

for DB in $DATABASES; do
    OUTFILE="${BACKUP_DIR}/${DB}_${DATE}.sql.gz"
    echo "    - Dump de ${DB}..."
    # --single-transaction: consistente sem bloquear tabelas (InnoDB)
    mysqldump "${MYSQL_OPTS[@]}" \
        --single-transaction \
        --quick \
        --routines \
        --triggers \
        --events \
        "$DB" | gzip > "$OUTFILE"
    echo "      OK -> ${OUTFILE} ($(du -h "$OUTFILE" | cut -f1))"
done

echo "==> Removendo backups com mais de ${RETENTION_DAYS} dias..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "==> Backup concluído."
echo "==> Total armazenado em ${BACKUP_DIR}:"
du -sh "$BACKUP_DIR"
