from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')


def signup(request):
    return render(request, 'signup.html')  

def userlogin(request):
    return render(request, 'signin.html')

def userlogout(request):
    return render(request, 'index.html')


# user views
def profile(request):
    return render(request, 'user/account-settings.html')

def address(request):
    return render(request, 'user/account-address.html')

def order_details(request):
    return render(request, 'user/account-orders.html')

def payment_method(request):
    return render(request, 'user/account-payment-method.html')

def rewards(request):
    return render(request, 'user/account-notification.html')






# Admin views
def admin_home(request):
    return render(request, 'superadmin/adminhome.html')
