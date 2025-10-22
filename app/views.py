from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from . import db
import re
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.core.mail import send_mail
from django.conf import settings
import random, string
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.core.files.storage import FileSystemStorage
from datetime import datetime
from django.shortcuts import get_object_or_404
from math import ceil
from django.core.paginator import Paginator
from django.utils.html import strip_tags
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


# Normalize phone numbers
def normalize_phone(raw):
    """Keep only digits (works for +91, spaces, etc.)"""
    return re.sub(r"\D", "", raw or "")

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def index(request):
    carousels = db.selectall("SELECT * FROM carousel_images ORDER BY id DESC")
    # ✅ Fetch all categories
    categories = db.selectall("SELECT * FROM categories ORDER BY id DESC")

    # ✅ Split categories into chunks of 10 for sections
    def chunk_list(data, chunk_size):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    category_groups = chunk_list(categories, 10)

    # ✅ Only first 10 categories shown on home
    first_10_categories = categories[:10]
    
    return render(request, "index.html", {"carousels": carousels,"categories": categories,
        "category_groups": category_groups,
        "first_10_categories": first_10_categories})

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def user_categories(request):
    categories = db.selectall("SELECT * FROM categories ORDER BY id DESC")
    return render(request, 'usercategories.html', {"categories": categories})

def category_products(request, category_id):
    # ✅ Get category
    category = db.selectone("SELECT * FROM categories WHERE id=%s", (category_id,))
    if not category:
        messages.error(request, "Category not found.")
        return redirect("index")

    # ✅ Fetch subcategories for sidebar filter
    subcategories = db.selectall("SELECT * FROM subcategories WHERE category_id=%s ORDER BY name ASC", (category_id,))

    # ✅ Sorting logic
    sort = request.GET.get("sort", "")
    order_by = "p.id DESC"
    if sort == "price_low":
        order_by = "p.price ASC"
    elif sort == "price_high":
        order_by = "p.price DESC"

    # ✅ Pagination setup
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 12))
    offset = (page - 1) * limit

    # ✅ Count total
    count_row = db.selectone("""
        SELECT COUNT(*) AS count 
        FROM products p 
        WHERE p.category_id=%s AND p.approved=1 AND p.pending_approval=0 AND p.disapproved=0
    """, (category_id,))
    total = count_row["count"] if count_row else 0

    # ✅ Fetch paginated products
    products = db.selectall(f"""
        SELECT p.*, 
               c.name AS category_name,
               s.name AS subcategory_name,
               (SELECT image FROM product_images WHERE product_id=p.id LIMIT 1) AS main_image
        FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        LEFT JOIN subcategories s ON p.subcategory_id=s.id
        WHERE p.category_id=%s AND p.approved=1 AND p.pending_approval=0 AND p.disapproved=0
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """, (category_id, limit, offset))

    total_pages = (total + limit - 1) // limit

    # ✅ Categories for navbar
    categories_all = db.selectall("SELECT * FROM categories ORDER BY name ASC")

    context = {
        "category": category,
        "categories_all": categories_all,
        "subcategories": subcategories,
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "sort": sort,
        "limit": limit,
    }
    return render(request, "shop-grid.html", context)

from django.http import JsonResponse

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


def search_products(request):
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    limit = 30
    offset = (page - 1) * limit

    products = []
    total = 0
    total_pages = 1
    page_numbers = []

    if query:
        # ✅ Count total
        count_row = db.selectone("""
            SELECT COUNT(*) AS count
            FROM products p
            WHERE p.title LIKE %s 
              AND p.approved = 1
              AND p.pending_approval = 0
              AND p.disapproved = 0
        """, [f'%{query}%'])
        total = count_row["count"] if count_row else 0
        total_pages = ceil(total / limit) if total > 0 else 1

        # ✅ Fetch paginated data
        products = db.selectall(f"""
            SELECT 
                p.id, 
                p.title AS name, 
                p.price, 
                p.sale_price,
                (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS image
            FROM products p
            WHERE p.title LIKE %s 
              AND p.approved = 1
              AND p.pending_approval = 0
              AND p.disapproved = 0
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """, [f'%{query}%', limit, offset])

        # ✅ Create range list for pagination
        page_numbers = list(range(1, total_pages + 1))

    return render(request, 'search_results.html', {
        'query': query,
        'products': products,
        'page': page,
        'total_pages': total_pages,
        'total': total,
        'page_numbers': page_numbers,
    })
    
    
# 🛒 ---------------------- CART SYSTEM ----------------------

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def cart(request):
    """Cart full page"""
    if "user_id" not in request.session:
        return redirect("userlogin")

    user_id = request.session["user_id"]
    items = db.selectall("""
        SELECT c.id, c.product_id, c.quantity, 
               p.title, p.price, p.sale_price, 
               (SELECT image FROM product_images WHERE product_id=p.id LIMIT 1) AS main_image
        FROM cart c 
        JOIN products p ON p.id=c.product_id
        WHERE c.user_id=%s
    """, (user_id,))
    total = sum([(i["sale_price"] or i["price"]) * i["quantity"] for i in items])

    context = {"items": items, "total": total}
    context.update(get_cart_context(request))
    return render(request, "cart.html", context)


@csrf_exempt
def add_to_cart(request, product_id):
    """Add product to cart"""
    if "user_id" not in request.session:
        return JsonResponse({"status": "login_required"})

    user_id = request.session["user_id"]
    qty = int(request.POST.get("quantity", 1))
    existing = db.selectone("SELECT * FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
    if existing:
        db.update("UPDATE cart SET quantity=quantity+%s WHERE id=%s", (qty, existing["id"]))
    else:
        db.insert("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)", (user_id, product_id, qty))
    return JsonResponse({"status": "success"})


@csrf_exempt
def update_cart_quantity(request):
    if "user_id" not in request.session:
        return JsonResponse({"status": "login_required"})

    cid = request.POST.get("cart_id")
    qty = request.POST.get("quantity")
    db.update("UPDATE cart SET quantity=%s WHERE id=%s", (qty, cid))
    return JsonResponse({"status": "updated"})


@csrf_exempt
def remove_cart_item(request, cart_id):
    if "user_id" not in request.session:
        return JsonResponse({"status": "login_required"})
    db.delete("DELETE FROM cart WHERE id=%s", (cart_id,))
    return JsonResponse({"status": "removed"})


def mini_cart_data(request):
    """Return JSON for offcanvas refresh"""
    data = get_cart_context(request)
    return JsonResponse(data)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def buy_now(request, product_id):
    """Direct purchase page (Buy Now button)"""
    if "user_id" not in request.session:
        return redirect("userlogin")

    product = db.selectone("""
        SELECT p.*, (SELECT image FROM product_images WHERE product_id=p.id LIMIT 1) AS main_image
        FROM products p WHERE p.id=%s
    """, (product_id,))
    if not product:
        messages.error(request, "Product not found.")
        return redirect("index")

    return render(request, "purchase.html", {"product": product})




# Admin views

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def admin_home(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    return render(request, 'superadmin/adminhome.html')


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
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")
    
    data = db.selectall("SELECT * FROM carousel_images ORDER BY id DESC")
    
    return render(request, "superadmin/carousel-images.html", {"images": data})


def add_carousel_image(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    if request.method == "POST":
        carousel_name = request.POST.get("carousel_name", "").strip()
        description = request.POST.get("description", "").strip()
        image_file = request.FILES.get("image")

        if not carousel_name or not image_file:
            messages.error(request, "Please fill all required fields.")
            return redirect("add-carousel-image")

        # Save the file inside /media/carousels/
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "carousels"))
        filename = get_random_string(8) + "_" + image_file.name
        saved_name = fs.save(filename, image_file)
        image_path = f"carousels/{saved_name}"

        # Save to DB (create table carousel_images if not exists)
        db.insert("""
            INSERT INTO carousel_images (title, description, image)
            VALUES (%s, %s, %s)
        """, (carousel_name, description, image_path))

        messages.success(request, f"Carousel image '{carousel_name}' added successfully!")
        return redirect("carousel-images")
    
    return render(request, "superadmin/add-carousel-image.html")

# ✅ Delete Carousel
def delete_carousel(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    item = db.selectone("SELECT * FROM carousel_images WHERE id=%s", (id,))
    if not item:
        messages.error(request, "Carousel not found.")
        return redirect("carousel-images")

    # Delete image file
    if item["image"]:
        photo_path = os.path.join(settings.MEDIA_ROOT, item["image"])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    db.delete("DELETE FROM carousel_images WHERE id=%s", (id,))
    messages.success(request, f"Carousel '{item['title']}' deleted successfully.")
    

    return redirect("carousel-images")


# ✅ Edit Carousel
def edit_carousel(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    carousel = db.selectone("SELECT * FROM carousel_images WHERE id=%s", (id,))
    if not carousel:
        messages.error(request, "Carousel not found.")
        return redirect("carousel-images")

    if request.method == "POST":
        title = request.POST.get("carousel_name", "").strip()
        description = request.POST.get("description", "").strip()
        image_file = request.FILES.get("image")

        image_path = carousel["image"]
        if image_file:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "carousels"))
            filename = get_random_string(8) + "_" + image_file.name
            saved_name = fs.save(filename, image_file)
            image_path = f"carousels/{saved_name}"

        db.update("""
            UPDATE carousel_images
            SET title=%s, description=%s, image=%s
            WHERE id=%s
        """, (title, description, image_path, id))

        messages.success(request, "Carousel updated successfully!")
        return redirect("carousel-images")

    return render(request, "superadmin/edit-carousel.html", {"carousel": carousel})



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def categories(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    categories = db.selectall("SELECT * FROM categories ORDER BY id DESC")
    subcategories = db.selectall("SELECT * FROM subcategories ORDER BY id DESC")

    # ✅ Count subcategories per category
    for cat in categories:
        cat["subcat_count"] = sum(1 for sub in subcategories if sub["category_id"] == cat["id"])

    return render(request, "superadmin/categories.html", {
        "categories": categories,
        "subcategories": subcategories,
    })



def add_category(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    if request.method == "POST":
        category_name = request.POST.get("category_name", "")
        slug = request.POST.get("slug", "")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        image_file = request.FILES.get("image")

        if not category_name or not image_file:
            messages.error(request, "Please fill all required fields.")
            return redirect("add-category")

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "categories"))
        filename = get_random_string(8) + "_" + image_file.name
        saved_name = fs.save(filename, image_file)
        image_path = f"categories/{saved_name}"

        db.insert("""
            INSERT INTO categories (name, slug, description, image, meta_title, meta_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (category_name, slug, description, image_path, meta_title, meta_description))

        messages.success(request, f"Category '{category_name}' added successfully!")
        return redirect("categories")

    return render(request, "superadmin/add-category.html")


def edit_category(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    category = db.selectone("SELECT * FROM categories WHERE id=%s", (id,))
    if not category:
        messages.error(request, "Category not found.")
        return redirect("categories")

    if request.method == "POST":
        category_name = request.POST.get("category_name", "")
        slug = request.POST.get("slug", "")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        image_file = request.FILES.get("image")

        image_path = category["image"]
        if image_file:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "categories"))
            filename = get_random_string(8) + "_" + image_file.name
            saved_name = fs.save(filename, image_file)
            image_path = f"categories/{saved_name}"

        db.update("""
            UPDATE categories
            SET name=%s, slug=%s, description=%s, image=%s, meta_title=%s, meta_description=%s
            WHERE id=%s
        """, (category_name, slug, description, image_path, meta_title, meta_description, id))

        messages.success(request, "Category updated successfully!")
        return redirect("categories")

    return render(request, "superadmin/edit-category.html", {"category": category})


def delete_category(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # Fetch category
    category = db.selectone("SELECT * FROM categories WHERE id=%s", (id,))
    if not category:
        messages.error(request, "Category not found.")
        return redirect("categories")

    # Delete image file
    if category["image"]:
        image_path = os.path.join(settings.MEDIA_ROOT, category["image"])
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete category (this automatically deletes subcategories because of ON DELETE CASCADE)
    db.delete("DELETE FROM categories WHERE id=%s", (id,))

    messages.success(request, f"Category '{category['name']}' and all its subcategories deleted successfully.")
    return redirect("categories")



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_subcategory(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # Fetch all parent categories
    categories = db.selectall("SELECT id, name FROM categories ORDER BY name ASC")

    # ✅ Capture ?parent=ID from URL
    parent_id = request.GET.get("parent")
    parent_category = None
    if parent_id:
        parent_category = db.selectone("SELECT * FROM categories WHERE id=%s", (parent_id,))

    if request.method == "POST":
        subcategory_name = request.POST.get("subcategory_name", "")
        slug = request.POST.get("slug", "")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        category_id = request.POST.get("category_id")

        if not subcategory_name or not category_id:
            messages.error(request, "Please fill all required fields.")
            return redirect("add-subcategory")

        db.insert("""
            INSERT INTO subcategories (category_id, name, slug, description, meta_title, meta_description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (category_id, subcategory_name, slug, description, meta_title, meta_description))

        messages.success(request, f"Subcategory '{subcategory_name}' added successfully!")
        return redirect("categories")

    # ✅ Pass parent category data to template
    return render(request, "superadmin/add- subcategory.html", {
        "categories": categories,
        "parent_category": parent_category,
    })


def edit_subcategory(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    sub = db.selectone("SELECT * FROM subcategories WHERE id=%s", (id,))
    if not sub:
        messages.error(request, "Subcategory not found.")
        return redirect("categories")

    categories = db.selectall("SELECT id, name FROM categories ORDER BY name ASC")

    if request.method == "POST":
        name = request.POST.get("subcategory_name", "")
        slug = request.POST.get("slug", "")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        category_id = request.POST.get("category_id")

        db.update("""
            UPDATE subcategories
            SET category_id=%s, name=%s, slug=%s, description=%s, meta_title=%s, meta_description=%s
            WHERE id=%s
        """, (category_id, name, slug, description, meta_title, meta_description, id))

        messages.success(request, "Subcategory updated successfully!")
        return redirect("categories")

    return render(request, "superadmin/edit-subcategory.html", {"subcategory": sub, "categories": categories})


def delete_subcategory(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    sub = db.selectone("SELECT * FROM subcategories WHERE id=%s", (id,))
    if not sub:
        messages.error(request, "Subcategory not found.")
        return redirect("categories")

    # 🧹 Delete related products first
    db.delete("DELETE FROM products WHERE subcategory_id=%s", (id,))

    # Now delete subcategory
    db.delete("DELETE FROM subcategories WHERE id=%s", (id,))

    messages.success(request, f"Subcategory '{sub['name']}' and its products deleted successfully.")
    return redirect("categories")




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def products(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    categories = db.selectall("SELECT * FROM categories ORDER BY name ASC")

    # ✅ Add this line to fetch active plan
    all_plans = db.selectall("SELECT * FROM plans WHERE is_active=1 ORDER BY price ASC")

    context = {
        "categories": categories,
        "admin": admin,
        "all_plans": all_plans,  # ✅ Added for your modal
    }
    return render(request, "superadmin/products.html", context)

    
  
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_productcategory(request, category_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    category = db.selectone("SELECT * FROM categories WHERE id=%s", (category_id,))

    if not category:
        messages.error(request, "Category not found.")
        return redirect("products")

    page = int(request.GET.get("page", "1") or 1)
    limit = 10
    offset = (page - 1) * limit

    
    total_row = db.selectone("""
         SELECT COUNT(*) AS count FROM products
        WHERE category_id=%s AND admin_id=%s
        """, (category_id, admin_id))

    products = db.selectall("""
            SELECT 
                p.id, p.title, p.price, p.sale_price, p.stock, p.description,
                p.approved, p.pending_approval, p.disapproved, p.disapprove_reason,
                p.created_at,
                c.name AS category_name,
                s.name AS subcategory_name,
                (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS main_image
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN subcategories s ON p.subcategory_id = s.id
            WHERE p.category_id=%s AND p.admin_id=%s
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """, (category_id, admin_id, limit, offset))


    total = total_row["count"] if total_row else 0
    total_pages = ceil(total / limit) if total > 0 else 1

    context = {
        "category": category,
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "admin": admin,
    }
    return render(request, "superadmin/Addproductscat.html", context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_products(request, category_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    category = db.selectone("SELECT * FROM categories WHERE id=%s", (category_id,))
    subcategories = db.selectall("SELECT * FROM subcategories WHERE category_id=%s ORDER BY name ASC", (category_id,))

    if not category:
        messages.error(request, "Invalid category.")
        return redirect("products")

        # ✅ Product limit check
    if admin["is_superadmin"]:
        plan_limit = 999999  # unlimited for superadmin
    else:
        plan_limit = admin.get("plan_limit", 25) or 25

    # ✅ Count how many products this admin already added
    product_count = db.selectone("SELECT COUNT(*) as count FROM products WHERE admin_id=%s", (admin_id,))
    current_count = product_count["count"] if product_count else 0

    # ✅ Check limit before allowing new product
    if not admin["is_superadmin"] and current_count >= plan_limit:
        messages.error(
            request,
            f"🚫 You’ve reached your product limit ({plan_limit}). Please upgrade your plan to add more products."
        )
        return redirect("products")


    # ✅ Handle product submission
    if request.method == "POST":
        title = request.POST.get("title", "")
        subcategory_id = request.POST.get("subcategory")
        if not subcategory_id or subcategory_id == "":
            subcategory_id = None

        price = request.POST.get("price", "0")
        sale_price = request.POST.get("sale_price", "0")
        stock = request.POST.get("stock", "0")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        is_vip = request.POST.get("is_vip") == "on"

        approved = admin["is_superadmin"]
        pending_approval = not admin["is_superadmin"]

        # ✅ Ensure subcategory is None if none exist
        if not subcategories:
            subcategory_id = None

        # ✅ Save product
        db.insert("""
            INSERT INTO products 
            (title, category_id, subcategory_id, price, sale_price, stock, description,
             meta_title, meta_description, admin_id, approved, pending_approval, is_vip)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            title, category_id, subcategory_id, price, sale_price, stock,
            description, meta_title, meta_description, admin_id,
            approved, pending_approval, is_vip
        ))

        product = db.selectone("SELECT * FROM products ORDER BY id DESC LIMIT 1")

        # ✅ Upload product images
        files = request.FILES.getlist("images")
        if files:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "products"))
            for img in files:
                filename = get_random_string(8) + "_" + img.name
                fs.save(filename, img)
                db.insert(
                    "INSERT INTO product_images (product_id, image) VALUES (%s,%s)",
                    (product["id"], f"products/{filename}")
                )

        # ✅ Save custom fields
        field_names = request.POST.getlist("field_name[]")
        field_values = request.POST.getlist("field_value[]")
        for name, value in zip(field_names, field_values):
            if name and value:
                db.insert(
                    "INSERT INTO product_attributes (product_id, field_name, field_value) VALUES (%s,%s,%s)",
                    (product["id"], name, value)
                )

        messages.success(request, f"✅ Product '{title}' added successfully to {category['name']}")
        return redirect("add-productcategory", category_id=category_id)

    context = {
        "category": category,
        "subcategories": subcategories,
        "admin": admin,
    }
    return render(request, "superadmin/add-product.html", context)


def delete_product(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    product = db.selectone("SELECT * FROM products WHERE id=%s", (id,))
    if not product:
        messages.error(request, "Product not found.")
        return redirect("products")

    # Delete images from media
    images = db.selectall("SELECT image FROM product_images WHERE product_id=%s", (id,))
    for img in images:
        path = os.path.join(settings.MEDIA_ROOT, img["image"])
        if os.path.exists(path):
            os.remove(path)

    db.delete("DELETE FROM products WHERE id=%s", (id,))
    messages.success(request, f"Product '{product['title']}' deleted successfully.")
    return redirect("add-productcategory", category_id=product["category_id"])

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def delete_selected_products(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    if request.method == "POST":
        selected = request.POST.getlist("selected_products")

        if not selected:
            messages.warning(request, "⚠️ No products selected for deletion.")
            return redirect(request.META.get("HTTP_REFERER", "products"))

        deleted_count = 0

        for pid in selected:
            # Fetch product
            product = db.selectone("SELECT * FROM products WHERE id=%s", (pid,))
            if not product:
                continue

            # Delete product images from media
            images = db.selectall("SELECT image FROM product_images WHERE product_id=%s", (pid,))
            for img in images:
                img_path = os.path.join(settings.MEDIA_ROOT, img["image"])
                if os.path.exists(img_path):
                    os.remove(img_path)

            # Delete related entries
            db.delete("DELETE FROM product_images WHERE product_id=%s", (pid,))
            db.delete("DELETE FROM product_attributes WHERE product_id=%s", (pid,))
            db.delete("DELETE FROM products WHERE id=%s", (pid,))
            deleted_count += 1

        messages.success(request, f"🗑️ {deleted_count} product(s) deleted successfully.")
        return redirect(request.META.get("HTTP_REFERER", "products"))

    return redirect("products")



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def edit_product(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    # ✅ Fetch the product
    product = db.selectone("SELECT * FROM products WHERE id=%s", (id,))
    if not product:
        messages.error(request, "Product not found.")
        return redirect("products")

    # ✅ Fetch category + subcategories for dropdowns
    category = db.selectone("SELECT * FROM categories WHERE id=%s", (product["category_id"],))
    subcategories = db.selectall("SELECT id, name FROM subcategories WHERE category_id=%s", (product["category_id"],))

    # ✅ Fetch custom fields (attributes)
    attributes = db.selectall("SELECT * FROM product_attributes WHERE product_id=%s", (id,))

    # ✅ Fetch product images
    images = db.selectall("SELECT * FROM product_images WHERE product_id=%s", (id,))

    if request.method == "POST":
        title = request.POST.get("title", "")
        subcategory_id = request.POST.get("subcategory")
        if not subcategory_id or subcategory_id == "":
            subcategory_id = None
        price = request.POST.get("price", "0")
        sale_price = request.POST.get("sale_price", "0")
        stock = request.POST.get("stock", "0")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")

        # ✅ Update product
        db.update("""
    UPDATE products
    SET title=%s, subcategory_id=%s, price=%s, sale_price=%s, stock=%s, description=%s, 
        meta_title=%s, meta_description=%s
    WHERE id=%s
""", (title, subcategory_id, price, sale_price, stock, description, meta_title, meta_description, id))


        # ✅ Delete old custom fields, then re-insert
        db.delete("DELETE FROM product_attributes WHERE product_id=%s", (id,))
        field_names = request.POST.getlist("field_name[]")
        field_values = request.POST.getlist("field_value[]")
        for name, value in zip(field_names, field_values):
            if name and value:
                db.insert("INSERT INTO product_attributes (product_id, field_name, field_value) VALUES (%s,%s,%s)", (id, name, value))

        # ✅ Handle new uploaded images
        new_images = request.FILES.getlist("images")
        if new_images:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "products"))
            for img in new_images:
                filename = get_random_string(8) + "_" + img.name
                fs.save(filename, img)
                db.insert("INSERT INTO product_images (product_id, image) VALUES (%s,%s)", (id, f"products/{filename}"))

        messages.success(request, f"Product '{title}' updated successfully!")
        return redirect("add-productcategory", category_id=product["category_id"])

    context = {
        "product": product,
        "category": category,
        "subcategories": subcategories,
        "attributes": attributes,
        "images": images,
    }
    return render(request, "superadmin/edit-product.html", context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def approve_product(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # ✅ Fetch all admins who have pending products
    pending_admins = db.selectall("""
        SELECT a.id AS admin_id,
               a.username,
               a.email,
               a.organization,
               a.phone,
               a.photo,
               COUNT(p.id) AS pending_count
        FROM adminusers a
        JOIN products p ON p.admin_id = a.id
        WHERE p.pending_approval=1 AND p.approved=0 AND p.disapproved=0
        GROUP BY a.id, a.username, a.email, a.organization, a.phone
        ORDER BY pending_count DESC
    """)

    return render(request, "superadmin/Approveproduct.html", {
        "pending_admins": pending_admins
    })

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def approve_product_list(request, admin_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # ✅ Fetch all products (pending + approved + disapproved) for this admin
    products = db.selectall("""
        SELECT p.*, 
               c.name AS category_name, 
               s.name AS subcategory_name,
               a.username AS admin_name,
               (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS main_image
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN subcategories s ON p.subcategory_id = s.id
        LEFT JOIN adminusers a ON p.admin_id = a.id
        WHERE p.admin_id=%s
        ORDER BY 
            CASE 
                WHEN p.pending_approval=1 THEN 1 
                WHEN p.approved=1 THEN 2 
                ELSE 3 
            END ASC, 
            p.id DESC
    """, (admin_id,))

    admin_user = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    return render(request, "superadmin/Approveproductlist.html", {
        "admin_user": admin_user,
        "products": products
    })

# ✅ Approve Product
def approve_product_action(request, product_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin["is_superadmin"]:
        messages.error(request, "Access denied.")
        return redirect("admin-home")

    product = db.selectone("SELECT * FROM products WHERE id=%s", (product_id,))
    if not product:
        messages.error(request, "Product not found.")
        return redirect("approve-product")

    # ✅ Approve
    db.update("""
        UPDATE products 
        SET approved=1, pending_approval=0, disapproved=0, disapprove_reason=NULL
        WHERE id=%s
    """, (product_id,))

    # Notify uploader
    db.insert("""
        INSERT INTO notifications (admin_id, message)
        VALUES (%s, %s)
    """, (product["admin_id"], f"✅ Your product '{product['title']}' has been approved and is now live."))

    messages.success(request, f"Product '{product['title']}' approved successfully.")
    return redirect("approve-product-list", admin_id=product["admin_id"])


# ❌ Disapprove Product
def disapprove_product_action(request, product_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    # must be superadmin
    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin.get("is_superadmin"):
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    product = db.selectone("SELECT * FROM products WHERE id=%s", (product_id,))
    if not product:
        messages.error(request, "Product not found.")
        return redirect("approve-product")

    if request.method == "POST":
        # optional reason from form
        reason = request.POST.get("disapprove_reason", "").strip()
        # basic sanitization: remove HTML tags
        reason_clean = strip_tags(reason) if reason else None

        db.update("""
            UPDATE products
            SET approved=0, pending_approval=0, disapproved=1, disapprove_reason=%s
            WHERE id=%s
        """, (reason_clean, product_id))

        # Insert notification for product owner (include reason if present)
        if reason_clean:
            notif_msg = f"❌ Your product '{product['title']}' was disapproved by Superadmin. Reason: {reason_clean}"
        else:
            notif_msg = f"❌ Your product '{product['title']}' was disapproved by Superadmin."

        db.insert("""
            INSERT INTO notifications (admin_id, message)
            VALUES (%s, %s)
        """, (product["admin_id"], notif_msg))

        messages.warning(request, f"Product '{product['title']}' disapproved.")
        return redirect("approve-product-list", admin_id=product["admin_id"])

    # If someone GETs this URL directly, redirect back
    return redirect("approve-product-list", admin_id=product["admin_id"])

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def approval_list(request):
    """Show all admins who have added any products (approved, pending, or disapproved)"""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # ✅ Fetch all admins who have at least one product
    admins_with_products = db.selectall("""
        SELECT a.id AS admin_id,
               a.username,
               a.email,
               a.organization,
               a.phone,
               a.photo,
               COUNT(p.id) AS total_products
        FROM adminusers a
        JOIN products p ON p.admin_id = a.id
        GROUP BY a.id, a.username, a.email, a.organization, a.phone, a.photo
        ORDER BY a.username ASC
    """)

    return render(request, "superadmin/ApprovalList.html", {
        "admins_with_products": admins_with_products
    })

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def approval_list_products(request, admin_id):
    """Show all products (any status) by this admin"""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    superadmin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not superadmin or not superadmin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    products = db.selectall("""
        SELECT p.*, 
               c.name AS category_name, 
               s.name AS subcategory_name,
               a.username AS admin_name,
               (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS main_image
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN subcategories s ON p.subcategory_id = s.id
        LEFT JOIN adminusers a ON p.admin_id = a.id
        WHERE p.admin_id=%s
        ORDER BY p.id DESC
    """, (admin_id,))

    admin_user = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    return render(request, "superadmin/ApprovalListProducts.html", {
        "admin_user": admin_user,
        "products": products
    })

# ✅ Download Excel format (global)
def download_product_template_global(request):
    import pandas as pd
    from io import BytesIO
    from django.http import HttpResponse
    import xlsxwriter

    # Fetch categories and subcategories
    categories = db.selectall("SELECT id, name FROM categories ORDER BY name ASC")
    subcategories = db.selectall("SELECT id, name, category_id FROM subcategories ORDER BY name ASC")

    # Custom fields
    custom_fields = db.selectall("SELECT DISTINCT field_name FROM product_attributes")

    # Core columns
    columns = [
        "title", "category", "subcategory", "price", "sale_price",
        "stock", "description", "meta_title", "meta_description", "is_vip"
    ]

    for field in custom_fields:
        columns.append(field["field_name"])

    # Create Excel workbook in memory
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Products")

    # ✅ Header format
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
    for col, name in enumerate(columns):
        worksheet.write(0, col, name, header_fmt)
        worksheet.set_column(col, col, 20)

    # Write empty data rows (for user to fill)
    for i in range(1, 100):
        for j in range(len(columns)):
            worksheet.write(i, j, "")

    # --- Create a hidden sheet for dropdown data ---
    hidden = workbook.add_worksheet("Lists")
    hidden.hide()

    # Category dropdown list
    cat_names = [c["name"] for c in categories]
    for idx, name in enumerate(cat_names):
        hidden.write(idx, 0, name)

    # Subcategory lists per category (for indirect dropdowns)
    col_offset = 1
    cat_map = {}  # e.g. { 'Men': 'B2:B5' }
    for cat in categories:
        sub_names = [s["name"] for s in subcategories if s["category_id"] == cat["id"]]
        if not sub_names:
            continue
        start_row = 0
        for r, name in enumerate(sub_names):
            hidden.write(r, col_offset, name)
        end_row = len(sub_names)
        col_letter = xlsxwriter.utility.xl_col_to_name(col_offset)
        cat_map[cat["name"]] = f"{col_letter}$1:{col_letter}${end_row}"
        col_offset += 1

    # --- Named ranges for subcategories ---
    for cat_name, ref in cat_map.items():
        safe_name = cat_name.replace(" ", "_")
        workbook.define_name(safe_name, f"=Lists!{ref}")

    # --- Add dropdown for Category ---
    worksheet.data_validation(
        "B2:B100",
        {"validate": "list", "source": f"=Lists!$A$1:$A${len(cat_names)}"}
    )

    # --- Add dependent dropdown for Subcategory ---
    # Excel INDIRECT formula
    for row in range(2, 102):
        worksheet.data_validation(
            f"C{row}",
            {"validate": "list", "source": f"=INDIRECT(SUBSTITUTE($B{row},\" \",\"_\"))"}
        )

    workbook.close()
    output.seek(0)

    # Send response
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="bulk_product_upload_template.xlsx"'
    return response



# ✅ Upload Excel (global)
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def upload_product_excel_global(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    import io
    import pandas as pd
    from django.utils.safestring import mark_safe

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))

    # ✅ Use the admin’s personal plan limit instead of global plan
    if admin["is_superadmin"]:
        plan_limit = 999999  # unlimited
    else:
        plan_limit = admin.get("plan_limit", 25) or 25

    # ✅ Count how many products the admin already added
    product_count = db.selectone("SELECT COUNT(*) AS count FROM products WHERE admin_id=%s", (admin_id,))
    current_count = product_count["count"] if product_count else 0

    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            messages.error(request, f"Error reading Excel file: {str(e)}")
            return redirect("products")

        required_columns = ["title", "category", "price", "stock"]
        for col in required_columns:
            if col not in df.columns:
                messages.error(request, f"Missing required column: {col}")
                return redirect("products")

        total_rows = len(df)

        # ✅ Reject if this upload exceeds remaining plan limit
        if not admin["is_superadmin"] and (current_count + total_rows) > plan_limit:
            remaining = plan_limit - current_count
            preview_html = (
                df.head(5)
                .to_html(index=False, border=0, classes="table table-bordered table-sm mb-0")
            )
            msg = mark_safe(
                f"""
                🚫 <strong>Upload rejected:</strong> You already have {current_count} products.<br>
                Your plan allows {plan_limit} total products, so you can only add {remaining} more.<br><br>
                <strong>Preview of your file:</strong><br>{preview_html}
                """
            )
            messages.error(request, msg)
            return redirect("products")

        # ✅ Proceed with normal insert
        added_count = 0
        for _, row in df.iterrows():
            title = str(row.get("title", "")).strip()
            category_name = str(row.get("category", "")).strip()
            subcategory_name = str(row.get("subcategory", "")).strip()

            if not title or not category_name:
                continue

            category = db.selectone("SELECT id FROM categories WHERE name=%s", (category_name,))
            if not category:
                messages.error(request, f"❌ Category '{category_name}' not found in DB.")
                return redirect("products")

            category_id = category["id"]
            subcategory_id = None
            if subcategory_name:
                sub = db.selectone(
                    "SELECT id FROM subcategories WHERE name=%s AND category_id=%s",
                    (subcategory_name, category_id),
                )
                if sub:
                    subcategory_id = sub["id"]

            price = float(row.get("price", 0) or 0)
            sale_price = float(row.get("sale_price", 0) or 0)
            stock = int(row.get("stock", 0) or 0)
            description = str(row.get("description", "") or "")
            meta_title = str(row.get("meta_title", "") or "")
            meta_description = str(row.get("meta_description", "") or "")
            is_vip = str(row.get("is_vip", "")).lower() in ["true", "1", "yes"]

            db.insert("""
                INSERT INTO products
                (title, category_id, subcategory_id, price, sale_price, stock, description,
                 meta_title, meta_description, admin_id, approved, pending_approval, is_vip)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                title, category_id, subcategory_id, price, sale_price, stock,
                description, meta_title, meta_description, admin_id,
                admin["is_superadmin"], not admin["is_superadmin"], is_vip
            ))

            product = db.selectone("SELECT id FROM products ORDER BY id DESC LIMIT 1")

            # Custom fields
            standard_cols = [
                "title", "category", "subcategory", "price", "sale_price",
                "stock", "description", "meta_title", "meta_description", "is_vip"
            ]
            for col in df.columns:
                if col not in standard_cols and pd.notna(row.get(col)):
                    db.insert(
                        "INSERT INTO product_attributes (product_id, field_name, field_value) VALUES (%s,%s,%s)",
                        (product["id"], col, str(row[col]))
                    )

            added_count += 1

        messages.success(request, f"✅ {added_count} products added successfully.")
        return redirect("products")

    return redirect("products")



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def manage_plans(request):
    """Superadmin view: list all plans."""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin["is_superadmin"]:
        messages.error(request, "Access denied.")
        return redirect("admin-home")

    plans = db.selectall("SELECT * FROM plans ORDER BY id DESC")
    return render(request, "superadmin/manage_plans.html", {"plans": plans})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_plan(request):
    """Superadmin: Add new monthly plan."""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin["is_superadmin"]:
        messages.error(request, "Access denied.")
        return redirect("admin-home")

    if request.method == "POST":
        plan_name = request.POST.get("plan_name", "")
        price = request.POST.get("price", 0)
        product_limit = request.POST.get("product_limit", 25)
        description = request.POST.get("description", "")
        is_active = "is_active" in request.POST

        db.insert("""
            INSERT INTO plans (plan_name, price, product_limit, description, is_active)
            VALUES (%s,%s,%s,%s,%s)
        """, (plan_name, price, product_limit, description, is_active))

        messages.success(request, f"✅ Plan '{plan_name}' added successfully.")
        return redirect("manage-plans")

    return render(request, "superadmin/add_plan.html")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def edit_plan(request, plan_id):
    """Edit existing monthly plan"""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin["is_superadmin"]:
        messages.error(request, "Access denied.")
        return redirect("admin-home")

    plan = db.selectone("SELECT * FROM plans WHERE id=%s", (plan_id,))
    if not plan:
        messages.error(request, "Plan not found.")
        return redirect("manage-plans")

    if request.method == "POST":
        plan_name = request.POST.get("plan_name", "")
        price = request.POST.get("price", 0)
        product_limit = request.POST.get("product_limit", 0)
        description = request.POST.get("description", "")
        is_active = "is_active" in request.POST

        db.update("""
            UPDATE plans 
            SET plan_name=%s, price=%s, product_limit=%s, description=%s, is_active=%s 
            WHERE id=%s
        """, (plan_name, price, product_limit, description, is_active, plan_id))

        messages.success(request, f"✅ Plan '{plan_name}' updated successfully.")
        return redirect("manage-plans")

    return render(request, "superadmin/edit_plan.html", {"plan": plan})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def delete_plan(request, plan_id):
    """Delete a plan (superadmin only)"""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin["is_superadmin"]:
        messages.error(request, "Access denied.")
        return redirect("admin-home")

    # 🔹 Fetch the plan
    plan = db.selectone("SELECT * FROM plans WHERE id=%s", (plan_id,))

    if not plan:
        messages.error(request, "Plan not found.")
        return redirect("manage-plans")

    # 🔹 Prevent deleting an active plan
    if plan["is_active"]:
        messages.error(
            request,
            f"⚠️ Cannot delete active plan '{plan['plan_name']}'. Please deactivate it first."
        )
        return redirect("manage-plans")

    # 🔹 Safe to delete now
    db.delete("DELETE FROM plans WHERE id=%s", (plan_id,))
    messages.success(request, f" Plan '{plan['plan_name']}' deleted successfully.")
    return redirect("manage-plans")




# ✅ Toggle Active / Inactive
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def toggle_plan_status(request, plan_id):
    """AJAX toggle plan active/inactive"""
    if "admin_id" not in request.session:
        return JsonResponse({"status": "error", "message": "Login required."})

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin["is_superadmin"]:
        return JsonResponse({"status": "error", "message": "Access denied."})

    plan = db.selectone("SELECT * FROM plans WHERE id=%s", (plan_id,))
    if not plan:
        return JsonResponse({"status": "error", "message": "Plan not found."})

    new_status = not bool(plan["is_active"])  # ensure it's boolean toggle
    db.update("UPDATE plans SET is_active=%s WHERE id=%s", (new_status, plan_id))

    return JsonResponse({
        "status": "success",
        "is_active": new_status,
        "message": f"Plan '{plan['plan_name']}' is now {'Active' if new_status else 'Inactive'}."
    })


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def payment(request):
    """Payment page showing all available plans."""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))

    # Get all active plans
    all_plans = db.selectall("SELECT * FROM plans WHERE is_active=1 ORDER BY price ASC")

    return render(request, "superadmin/payment.html", {
        "all_plans": all_plans,
        "admin": admin,
    })
    
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def payment_success(request, plan_id):
    """Simulate payment success and upgrade normal admin plan limit."""
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (admin_id,))
    if not admin:
        messages.error(request, "Admin not found.")
        return redirect("adminlogin")

    # Superadmin skip
    if admin["is_superadmin"]:
        messages.info(request, "Superadmin has unlimited products.")
        return redirect("products")

    # Fetch selected plan
    plan = db.selectone("SELECT * FROM plans WHERE id=%s", (plan_id,))
    if not plan:
        messages.error(request, "Invalid plan selected.")
        return redirect("payment")

    # Get current plan limit
    current_limit = admin.get("plan_limit", 25) or 25

    # Add new plan’s limit to the old total
    new_total_limit = current_limit + plan["product_limit"]

    # Update admin’s plan info
    db.update("""
        UPDATE adminusers
        SET current_plan=%s,
            plan_limit=%s,
            plan_start=NOW(),
            plan_active=1
        WHERE id=%s
    """, (plan["plan_name"], new_total_limit, admin_id))

    # Record payment
    db.insert("""
        INSERT INTO payments (admin_id, plan_id, amount, status, created_at)
        VALUES (%s, %s, %s, %s, NOW())
    """, (admin_id, plan_id, plan["price"], "success"))

    messages.success(request, f"✅ {plan['plan_name']} plan activated. You can now add up to {new_total_limit} products!")
    return redirect("products")



def admin_notifications(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    notes = db.selectall("""
        SELECT * FROM notifications
        WHERE admin_id=%s ORDER BY created_at DESC
    """, (admin_id,))
    return render(request, "superadmin/admin-notifications.html", {"notifications": notes})

def mark_all_read(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    admin_id = request.session["admin_id"]
    db.update("UPDATE notifications SET is_read=1 WHERE admin_id=%s", (admin_id,))
    messages.success(request, "All notifications marked as read.")
    return redirect("admin-home")

def delete_notification(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    db.update("DELETE FROM notifications WHERE id=%s", (id,))
    return redirect("admin-notifications")


def delete_selected_notifications(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    if request.method == "POST":
        selected = request.POST.getlist("selected[]")
        if selected:
            ids = ",".join(selected)
            db.update(f"DELETE FROM notifications WHERE id IN ({ids})")
    return redirect("admin-notifications")


def delete_all_notifications(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    admin_id = request.session["admin_id"]
    db.update("DELETE FROM notifications WHERE admin_id=%s", (admin_id,))
    return redirect("admin-notifications")


def view_product(request, id):
    product = db.selectone("""
    SELECT p.*, 
           c.name AS category_name, 
           s.name AS subcategory_name,
           a.username AS admin_name,
           a.organization AS admin_org,        -- ✅ added line
           (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS main_image
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    LEFT JOIN subcategories s ON p.subcategory_id = s.id
    LEFT JOIN adminusers a ON p.admin_id = a.id
    WHERE p.id=%s
""", (id,))


    images = db.selectall("SELECT * FROM product_images WHERE product_id=%s", (id,))
    attributes = db.selectall("SELECT * FROM product_attributes WHERE product_id=%s", (id,))
    # ✅ Group attributes in pairs for display (2 per row)
    grouped_attrs = []
    for i in range(0, len(attributes), 2):
        pair = attributes[i:i+2]
        grouped_attrs.append(pair)
    

    # ✅ Related products (same category, exclude this one)
    related_products = db.selectall("""
        SELECT p.*, 
               (SELECT image FROM product_images WHERE product_id=p.id LIMIT 1) AS main_image,
               c.name AS category_name,
               s.name AS subcategory_name
        FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        LEFT JOIN subcategories s ON p.subcategory_id=s.id
        WHERE p.category_id=%s AND p.id != %s AND p.approved=1
        LIMIT 4
    """, (product["category_id"], id))

    return render(request, "shop-single.html", {
        "product": product,
        "images": images,
        "attributes": attributes,
        "grouped_attrs": grouped_attrs,
        "related_products": related_products,
    })

def order_list(request):
    return render(request, 'superadmin/order-list.html')

def sellers(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # Fetch all admins (you can later filter by is_admin if you have sellers too)
    data = db.selectall("SELECT * FROM adminusers ORDER BY id DESC")

    return render(request, "superadmin/Sellers.html", {"admins": data})

def add_sellers(request):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

 # ✅ clear old messages before rendering this form
    storage = messages.get_messages(request)
    storage.used = True
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")
    
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "").strip()
        organization = request.POST.get("organization", "").strip()
        address = request.POST.get("address", "").strip()
        joining_date = request.POST.get("joining_date", "").strip()
        photo_file = request.FILES.get("photo")

        if not name or not email or not password:
            messages.error(request, "Please fill all required fields.")
            return redirect("add-sellers")

        existing = db.selectone("SELECT * FROM adminusers WHERE email=%s", (email,))
        if existing:
            messages.error(request, "Email already exists.")
            return redirect("add-sellers")
        
        # Convert joining date
        try:
            formatted_date = datetime.strptime(joining_date, "%d/%m/%Y").date() if joining_date else None
        except ValueError:
            formatted_date = None

        photo_path = None
        if photo_file:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "admins"))
            filename = get_random_string(8) + "_" + photo_file.name
            saved_name = fs.save(filename, photo_file)
            photo_path = f"admins/{saved_name}"

        hashed_pwd = make_password(password)

        db.insert("""
            INSERT INTO adminusers (username, email, phone, password, organization, address, photo, joining_date, is_superadmin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, email, phone, hashed_pwd, organization, address, photo_path, formatted_date, False))

        messages.success(request, f"{name.capitalize()} created successfully!")
        return redirect("sellers")

    return render(request, "superadmin/Add-Sellers.html")

# ✅ DELETE ADMIN
def delete_admin(request, id):
    

    if "admin_id" not in request.session:
        return redirect("adminlogin")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # Check admin exists
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (id,))
    if not admin:
        messages.error(request, "Admin not found.")
        return redirect("sellers")

    # Delete the photo file if it exists
    if admin["photo"]:
        photo_path = os.path.join(settings.MEDIA_ROOT, admin["photo"])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    # Delete the admin record
    db.delete("DELETE FROM adminusers WHERE id=%s", (id,))
    messages.success(request, f"Admin '{admin['username']}' deleted successfully.")
    response = redirect("sellers")

    # ✅ Immediately clear message storage (prevents showing again later)
    storage = messages.get_messages(request)
    storage.used = True

    return response



# ✅ EDIT ADMIN
def edit_admin(request, id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    # ✅ Get the logged-in admin (superadmin check)
    logged_admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not logged_admin or not logged_admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    # ✅ Get the admin record to edit
    admin_to_edit = db.selectone("SELECT * FROM adminusers WHERE id=%s", (id,))
    if not admin_to_edit:
        messages.error(request, "Admin not found.")
        return redirect("sellers")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        organization = request.POST.get("organization", "").strip()
        address = request.POST.get("address", "").strip()
        joining_date = request.POST.get("joining_date", "").strip()
        photo_file = request.FILES.get("photo")

        # Convert date (dd/mm/yyyy → yyyy-mm-dd)
        try:
            formatted_date = datetime.strptime(joining_date, "%d/%m/%Y").date() if joining_date else None
        except ValueError:
            formatted_date = None

        # ✅ Handle photo update
        photo_path = admin_to_edit["photo"]
        if photo_file:
            # Delete old photo if exists
            if photo_path:
                old_photo_path = os.path.join(settings.MEDIA_ROOT, photo_path)
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)

            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "admins"))
            filename = get_random_string(8) + "_" + photo_file.name
            saved_name = fs.save(filename, photo_file)
            photo_path = f"admins/{saved_name}"

        # ✅ Update DB
        db.update("""
            UPDATE adminusers 
            SET username=%s, email=%s, phone=%s, organization=%s, address=%s, photo=%s, joining_date=%s
            WHERE id=%s
        """, (name, email, phone, organization, address, photo_path, formatted_date, id))

        messages.success(request, "Admin updated successfully!")
        return redirect("sellers")

    return render(request, "superadmin/edit-admin.html", {"admin": admin_to_edit})
