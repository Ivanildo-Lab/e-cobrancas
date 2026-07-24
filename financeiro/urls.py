from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('parcelas/gerar/', views.gerar_parcelas, name='gerar_parcelas'),
    path('parcelas/', views.lista_parcelas, name='lista_parcelas'),
    path('parcelas/<int:pk>/editar/', views.editar_parcela, name='editar_parcela'),
    path('parcelas/<int:pk>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),
    path('parcelas/<int:pk>/cancelar/', views.cancelar_parcela, name='cancelar_parcela'),
    path('parcelas/<int:pk>/desfazer/', views.desfazer_liquidacao, name='desfazer_liquidacao'),
    path('parcelas/whatsapp/<int:pk>/', views.enviar_whatsapp_individual, name='enviar_whatsapp_individual'),
    path('parcelas/whatsapp/lote/', views.enviar_lote_whatsapp, name='enviar_lote_whatsapp'),
    path('parcelas/pdf/', views.gerar_pdf, name='gerar_pdf'),
]
