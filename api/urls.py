from django.urls import path
from . import views

urlpatterns = [
    path('day/<str:date_str>/', views.get_day_view, name='get_day'),
    path('tasks/<str:task_id>/', views.update_task_view, name='update_task'),
    path('day/<str:date_str>/tasks/', views.add_task_view, name='add_task'),
]
