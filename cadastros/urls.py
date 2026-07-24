from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    path('cidades/', views.lista_cidades, name='lista_cidades'),
    path('cidades/nova/', views.criar_cidade, name='criar_cidade'),
    path('cidades/<int:pk>/editar/', views.editar_cidade, name='editar_cidade'),
    path('cidades/<int:pk>/excluir/', views.excluir_cidade, name='excluir_cidade'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/novo/', views.criar_cliente, name='criar_cliente'),
    path('clientes/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:pk>/desativar/', views.desativar_cliente, name='desativar_cliente'),
]
