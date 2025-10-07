from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return render(request, 'user/index.html')

def about(request):
    return render(request, 'user/about.html')

def signup(request):
    return render(request, 'user/signup.html')  

def login(request):
    return render(request, 'user/signin.html')





# Admin views
def admin_home(request):
    return render(request, 'admin/adminhome.html')
