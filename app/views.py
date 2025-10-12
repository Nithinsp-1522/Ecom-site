from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from . import db
import re
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.core.mail import send_mail
from django.conf import settings
import random, string
from django.contrib.auth.hashers import make_password

# Normalize phone numbers
def normalize_phone(raw):
    """Keep only digits (works for +91, spaces, etc.)"""
    return re.sub(r"\D", "", raw or "")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def userlogout(request):
    # clear old messages
    storage = messages.get_messages(request)
    storage.used = True

    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect("userlogin")



# user views
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def profile(request):
    if "user_id" not in request.session:
        return redirect("userlogin")
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
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_home(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    return render(request, 'superadmin/adminhome.html')

def admin_register(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        # Validate
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect("admin-register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("admin-register")

        existing = db.selectone("SELECT * FROM adminusers WHERE username=%s OR email=%s", (username, email))
        if existing:
            messages.error(request, "Username or email already exists.")
            return redirect("admin-register")

        hashed_pwd = make_password(password)
        db.insert(
            "INSERT INTO adminusers (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_pwd, True)
        )

        messages.success(request, "Admin registered successfully! Please log in.")
        return redirect("adminlogin")

    return render(request, "superadmin/adminregister.html")

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        # Allow login by username OR email
        admin_user = db.selectone(
            "SELECT * FROM adminusers WHERE username=%s OR email=%s", (username, username)
        )

        # Clear any old messages
        storage = messages.get_messages(request)
        storage.used = True

        if admin_user and check_password(password, admin_user["password"]):
            request.session["admin_id"] = admin_user["id"]
            request.session["admin_username"] = admin_user["username"]
            messages.success(request, f"Welcome back, {admin_user['username']}!")
            return redirect("admin-home")
        else:
            messages.error(request, "Invalid username, email, or password.")
            return redirect("adminlogin")

    return render(request, "superadmin/adminsignin.html")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def adminlogout(request):
    storage = messages.get_messages(request)
    storage.used = True
    request.session.flush()
    messages.success(request, "Admin logged out successfully.")
    return render(request, 'index.html')

def admin_forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        admin = db.selectone("SELECT * FROM adminusers WHERE email=%s", (email,))

        if not admin:
            messages.error(request, "No admin found with that email.")
            return redirect("admin-forgot-password")

        # Generate OTP or temporary reset code
        otp = ''.join(random.choices(string.digits, k=6))
        request.session['admin_reset_email'] = email
        request.session['admin_reset_otp'] = otp

        # Send email (requires EMAIL settings configured)
        try:
            send_mail(
                subject="Admin Password Reset OTP",
                message=f"Your OTP for admin password reset is: {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, "OTP sent to your email. Please check your inbox.")
            return redirect("admin-reset-verify")
        except Exception as e:
            messages.error(request, "Error sending email. Check email settings.")
            print(e)
            return redirect("admin-forgot-password")

    return render(request, "superadmin/forgot-password.html")


def admin_reset_verify(request):
    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        session_otp = request.session.get("admin_reset_otp")
        email = request.session.get("admin_reset_email")

        if not session_otp or not email:
            messages.error(request, "Session expired. Please restart the reset process.")
            return redirect("admin-forgot-password")

        if otp != session_otp:
            messages.error(request, "Invalid OTP.")
            return redirect("admin-reset-verify")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("admin-reset-verify")

        hashed_pwd = make_password(new_password)
        db.update("UPDATE adminusers SET password=%s WHERE email=%s", (hashed_pwd, email))

        # Clean up session
        request.session.pop("admin_reset_email", None)
        request.session.pop("admin_reset_otp", None)

        messages.success(request, "Password reset successful! You can now log in.")
        return redirect("adminlogin")

    return render(request, "superadmin/admin_reset_verify.html")

def carousel_images(request):
    return render(request, 'superadmin/carousel-images.html')

def add_carousel_image(request):
    return render(request, 'superadmin/add-carousel-image.html')


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