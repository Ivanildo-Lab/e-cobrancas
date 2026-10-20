from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('cadastros/', include('cadastros.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]

# Mídia (uploads: logo/banner) servida MESMO COM DEBUG=False.
# Em produção os arquivos vêm do volume persistente montado em MEDIA_ROOT
# (docker-compose.yml -> media_data:/app/media); sem esta rota, /media/* = 404.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
