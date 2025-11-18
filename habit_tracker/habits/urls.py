from django.urls import path
from . import views

urlpatterns = [
    path('', views.habit_list, name='habit_list'),
    path('habit/create/', views.habit_create, name='habit_create'),
    path('habit/<int:pk>/edit/', views.habit_edit, name='habit_edit'),
    path('habit/<int:pk>/delete/', views.habit_delete, name='habit_delete'),
    path('log/<int:habit_id>/', views.log_habit, name='log_habit'),
    path('exclude/<int:habit_id>/', views.exclude_day, name='exclude_day'),
    path('statistics/', views.statistics, name='statistics'),
    # Nuevas URLs para el temporizador
    path('timer/<int:habit_id>/action/', views.timer_action, name='timer_action'),
    path('timer/<int:habit_id>/status/', views.timer_status, name='timer_status'),
]