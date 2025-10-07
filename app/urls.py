from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    
    
    # Admin URLs can be added here
    path('admin-home/', views.admin_home, name='admin-home'),
]
