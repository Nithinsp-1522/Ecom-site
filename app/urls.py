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
    path('admin-forgot-password/', views.admin_forgot_password, name='admin-forgot-password'),
    path('admin-reset-verify/', views.admin_reset_verify, name='admin-reset-verify'),
    path('categories/', views.categories, name='categories'),
    path('add-category/', views.add_category, name='add-category'),
    path('add-subcategory/', views.add_subcategory, name='add-subcategory'),
    path('products/', views.products, name='products'),
    path('add-productcategory/', views.add_productcategory, name='add-productcategory'),
    path('add-products/', views.add_products, name='add-products'),
    path('approve-product/', views.approve_product, name='approve-product'),
    path('approve-product-list/', views.approve_product_list, name='approve-product-list'),
    path('order-list/', views.order_list, name='order-list'),
    path('sellers/', views.sellers, name='sellers'),
    path('add-sellers/', views.add_sellers, name='add-sellers'),
    path('admin-register/', views.admin_register, name='admin-register'),
    path('carousel-images/', views.carousel_images, name='carousel-images'),
    path('add-carousel-image/', views.add_carousel_image, name='add-carousel-image'),
]
