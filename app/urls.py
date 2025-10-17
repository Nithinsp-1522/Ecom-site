from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('userlogin/', views.userlogin, name='userlogin'),
    path('userlogout/', views.userlogout, name='userlogout'),
    path('user-categories', views.user_categories, name='user-categories'),
    path('category/<int:category_id>/', views.category_products, name='category-products'),
    path('category-products/', views.category_products, name='category-products'),
    
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
    
    # Category URLs
    path('categories/', views.categories, name='categories'),
    path('add-category/', views.add_category, name='add-category'),
    path('add-subcategory/', views.add_subcategory, name='add-subcategory'),
    path("edit-category/<int:id>/", views.edit_category, name="edit-category"),
    path("delete-category/<int:id>/", views.delete_category, name="delete-category"),
    path("edit-subcategory/<int:id>/", views.edit_subcategory, name="edit-subcategory"),
    path("delete-subcategory/<int:id>/", views.delete_subcategory, name="delete-subcategory"),

    # Product URLs
    path('products/', views.products, name='products'),
    path('add-productcategory/<int:category_id>/', views.add_productcategory, name='add-productcategory'),
    path('add-products/<int:category_id>/', views.add_products, name='add-products'),
    path("approve-product/", views.approve_product, name="approve-product"),
    path("approve-product-list/<int:admin_id>/", views.approve_product_list, name="approve-product-list"),
    path("approve-product-approve/<int:product_id>/", views.approve_product_action, name="approve-product-approve"),
    path("approve-product-disapprove/<int:product_id>/", views.disapprove_product_action, name="approve-product-disapprove"),
    # Approval list pages
    path("approval-list/", views.approval_list, name="approval-list"),
    path("approval-list-products/<int:admin_id>/", views.approval_list_products, name="approval-list-products"),
    path('edit-product/<int:id>/', views.edit_product, name='edit-product'),
    path('delete-product/<int:id>/', views.delete_product, name='delete-product'),

    
    
    path('order-list/', views.order_list, name='order-list'),
    path('sellers/', views.sellers, name='sellers'),
    path('add-sellers/', views.add_sellers, name='add-sellers'),
    path('edit-admin/<int:id>/', views.edit_admin, name='edit-admin'),
    path('delete-admin/<int:id>/', views.delete_admin, name='delete-admin'),
    
    # Carousel Image URLs
    path('carousel-images/', views.carousel_images, name='carousel-images'),
    path('add-carousel-image/', views.add_carousel_image, name='add-carousel-image'),
    path('edit-carousel/<int:id>/', views.edit_carousel, name='edit-carousel'),
    path('delete-carousel/<int:id>/', views.delete_carousel, name='delete-carousel'),

    

    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
