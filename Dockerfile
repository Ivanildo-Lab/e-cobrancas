# ---- Dockerfile para Django (padrão para todos os 15 apps) ----
FROM python:3.12-slim

# Variáveis de ambiente do Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Diretório de trabalho dentro do container
WORKDIR /app

# Instala as dependências primeiro (camada de cache do Docker).
# requirements.txt com psycopg2-binary / mysqlclient já vem com binários,
# então não precisa de libs de compilação no slim.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o código do projeto
COPY . .

# Cria os diretórios de mídia e estáticos.
# media/ será sobrescrito por volume persistente em produção.
RUN mkdir -p media staticfiles

# Porta que o Gunicorn vai escutar
EXPOSE 8000

# Comando de inicialização:
# 1) aplica as migrations do banco
# 2) gera os arquivos estáticos (whitenoise/manifest)
# 3) sobe o Gunicorn servindo o setup.wsgi
# Workers configuráveis por variável (padrão 2, por serem 15 apps num VPS só)
CMD ["sh", "-c", "\
    python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn setup.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers ${GUNICORN_WORKERS:-2} \
      --timeout ${GUNICORN_TIMEOUT:-60} \
      --access-logfile - \
      --error-logfile -"]
