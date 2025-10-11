from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from . import db
import re
from django.http import JsonResponse

# Normalize phone numbers
def normalize_phone(raw):
    """Keep only digits (works for +91, spaces, etc.)"""
    return re.sub(r"\D", "", raw or "")

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')


def signup(request):
    if request.method == "POST":
        fname = request.POST.get("formSignupfname")
        lname = request.POST.get("formSignuplname")
        email = request.POST.get("formSignupEmail")
        phone = normalize_phone(request.POST.get("formSignupPhone"))
        password = request.POST.get("formSignupPassword")

        if not (email or phone):
            messages.error(request, "Please provide an email or phone number.")
            return redirect("signup")

        # Check if user exists
        existing = db.selectone("SELECT * FROM users WHERE email=%s OR phone=%s", (email, phone))
        if existing:
            messages.error(request, "Email or Phone Number already exists.")
            return redirect("signup")

        hashed_pwd = make_password(password)
        db.insert(
            "INSERT INTO users (first_name, last_name, email, phone, password) VALUES (%s,%s,%s,%s,%s)",
            (fname, lname, email, phone, hashed_pwd)
        )
        messages.success(request, "Account created successfully! Please login.")
        return redirect("userlogin")

    return render(request, 'signup.html')  

from django.contrib import messages

def userlogin(request):
    if request.method == "POST":
        # Check if request is AJAX
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        identifier = request.POST.get("formSigninEmail", "").strip()
        password = request.POST.get("formSigninPassword", "").strip()
        phone = normalize_phone(identifier)

        user = None
        if "@" in identifier:
            user = db.selectone("SELECT * FROM users WHERE email=%s", (identifier,))
        elif phone.isdigit():
            user = db.selectone("SELECT * FROM users WHERE phone=%s", (phone,))
        else:
            if is_ajax:
                return JsonResponse({"status": "error", "message": "Please enter a valid email or phone number."})
            messages.error(request, "Please enter a valid email or phone number.")
            return redirect("userlogin")

        if user and check_password(password, user["password"]):
            request.session["user_id"] = user["id"]
            request.session["user_name"] = user["first_name"] + " " + user["last_name"]

            if is_ajax:
                return JsonResponse({"status": "success", "message": f"Welcome back, {user['first_name']}!"})
            
            messages.success(request, f"Welcome back, {user['first_name']}!")
            return redirect("index")
        else:
            if is_ajax:
                return JsonResponse({"status": "error", "message": "Invalid email/phone or password."})
            messages.error(request, "Invalid email/phone or password.")
            return redirect("userlogin")

    return render(request, "signin.html")


def userlogout(request):
    # clear old messages
    storage = messages.get_messages(request)
    storage.used = True

    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect("userlogin")



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
    return render(request, 'user/account-Rewards.html')






# Admin views
def admin_home(request):
    return render(request, 'superadmin/adminhome.html')

def admin_login(request):
    return render(request, 'superadmin/adminsignin.html')

def adminlogout(request):
    return render(request, 'index.html')

def categories(request):
    return render(request, 'superadmin/categories.html')

def add_category(request):
    return render(request, 'superadmin/add-category.html')

def add_subcategory(request):   
    return render(request, 'superadmin/add- Subcategory.html')

def products(request):
    return render(request, 'superadmin/products.html')

def add_productcategory(request):
    return render(request, 'superadmin/Addproductscat.html')

def add_products(request):
    return render(request, 'superadmin/add-product.html')

def approve_product(request):
    return render(request, 'superadmin/Approveproduct.html')

def approve_product_list(request):
    return render(request, 'superadmin/Approveproductlist.html')

def order_list(request):
    return render(request, 'superadmin/order-list.html')

def sellers(request):
    return render(request, 'superadmin/Sellers.html')

def add_sellers(request):
    return render(request, 'superadmin/Add-Sellers.html')