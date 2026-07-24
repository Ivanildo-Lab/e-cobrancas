from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect

def home(request):
    if request.user.is_authenticated:
        return redirect('financeiro:dashboard')
    return render(request, 'home.html')

urlpatterns = [
    path('', home, name='home'),
]
