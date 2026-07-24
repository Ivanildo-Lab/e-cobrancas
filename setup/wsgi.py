import os
import sys
from django.core.wsgi import get_wsgi_application

project = '/home/geficogestor/e-cobrancas'
sys.path.insert(0, project)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

application = get_wsgi_application()
