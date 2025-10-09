from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('userlogin/', views.userlogin, name='userlogin'),
    path('userlogout/', views.userlogout, name='userlogout'),
    
    # User URLs
    path('profile/', views.profile, name='profile'),
    path('address/', views.address, name='address'),
    path('order-details/', views.order_details, name='order-details'),
    path('payment-method/', views.payment_method, name='payment-method'),
    path('rewards/', views.rewards, name='rewards'),



    # Admin URLs can be added here
    path('admin-home/', views.admin_home, name='admin-home'),
    path('adminlogin/', views.admin_login, name='adminlogin'),
    path('adminlogout/', views.adminlogout, name='adminlogout'),
    path('categories/', views.categories, name='categories'),
    path('add-category/', views.add_category, name='add-category'),
    path('add-subcategory/', views.add_subcategory, name='add-subcategory'),
]
