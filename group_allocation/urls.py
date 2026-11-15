from django.contrib import admin
from django.urls import path

from allocations import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('log_in/', views.log_in, name='log_in'),
    path('log_out/', views.log_out, name='log_out'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('runs/<int:run_id>/', views.run_detail, name='run_detail'),
    path('runs/<int:run_id>/export.csv', views.export_run_csv, name='export_run_csv'),
    path('profile/', views.profile, name='profile'),
    path('password/', views.password, name='password'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/update/', views.user_update, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
]
