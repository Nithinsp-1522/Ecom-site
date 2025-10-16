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
        WHERE p.category_id=%s
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
        WHERE p.category_id=%s
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

def product_quickview(request, product_id):
    """Return product details + images + attributes for Quick View modal"""
    product = db.selectone("""
        SELECT p.*, 
               c.name AS category_name, 
               s.name AS subcategory_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN subcategories s ON p.subcategory_id = s.id
        WHERE p.id=%s
    """, (product_id,))

    if not product:
        return JsonResponse({"error": "Product not found"}, status=404)

    images = db.selectall("SELECT image FROM product_images WHERE product_id=%s", (product_id,))
    attributes = db.selectall("SELECT field_name, field_value FROM product_attributes WHERE product_id=%s", (product_id,))

    return JsonResponse({
        "product": product,
        "images": images,
        "attributes": attributes
    })

   


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




def products(request):
    
    categories = db.selectall("SELECT * FROM categories ORDER BY id ASC")

    return render(request, 'superadmin/products.html', {"categories": categories})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_productcategory(request, category_id):
    if "admin_id" not in request.session:
        return redirect("adminlogin")

    category = db.selectone("SELECT * FROM categories WHERE id=%s", (category_id,))
    if not category:
        messages.error(request, "Category not found.")
        return redirect("products")

    # ✅ Fix: request.GET is always available here
    page_str = request.GET.get("page", "1") or "1"
    try:
        page = int(page_str)
    except ValueError:
        page = 1

    limit = 10
    offset = (page - 1) * limit

    total_row = db.selectone("SELECT COUNT(*) AS count FROM products WHERE category_id=%s", (category_id,))
    total = total_row["count"] if total_row else 0
    total_pages = ceil(total / limit) if total > 0 else 1

    products = db.selectall("""
        SELECT p.*, 
               c.name AS category_name, 
               s.name AS subcategory_name,
               (SELECT image FROM product_images WHERE product_id = p.id LIMIT 1) AS main_image
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN subcategories s ON p.subcategory_id = s.id
        WHERE p.category_id=%s
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
    """, (category_id, limit, offset))

    context = {
        "category": category,
        "products": products,
        "page": page,
        "total_pages": total_pages,
        "total": total,
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

    # Product limit check
    product_count = db.selectone("SELECT COUNT(*) as count FROM products WHERE admin_id=%s", (admin_id,))
    if not admin["is_superadmin"] and product_count["count"] >= 25:
        messages.warning(request, "You’ve reached your product limit. Please request upgrade or approval.")
        return redirect("products")

    if request.method == "POST":
        title = request.POST.get("title", "")
        subcategory_id = request.POST.get("subcategory", "")
        price = request.POST.get("price", "0")
        sale_price = request.POST.get("sale_price", "0")
        stock = request.POST.get("stock", "0")
        description = request.POST.get("description", "")
        meta_title = request.POST.get("meta_title", "")
        meta_description = request.POST.get("meta_description", "")
        is_vip = request.POST.get("is_vip") == "on"

        approved = admin["is_superadmin"]
        pending_approval = not admin["is_superadmin"]
        
         # ✅ Ensure subcategory is None if there are no subcategories
        if not subcategories:
            subcategory_id = None

        db.insert("""
            INSERT INTO products 
            (title, category_id, subcategory_id, price, sale_price, stock, description, meta_title, meta_description, admin_id, approved, pending_approval)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            title, category_id, subcategory_id, price, sale_price, stock,
            description, meta_title, meta_description, admin_id, approved, pending_approval
        ))

        product = db.selectone("SELECT * FROM products ORDER BY id DESC LIMIT 1")

        files = request.FILES.getlist("images")
        if files:
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "products"))
            for img in files:
                filename = get_random_string(8) + "_" + img.name
                fs.save(filename, img)
                db.insert("INSERT INTO product_images (product_id, image) VALUES (%s,%s)", (product["id"], f"products/{filename}"))

        # Save custom fields
        field_names = request.POST.getlist("field_name[]")
        field_values = request.POST.getlist("field_value[]")
        for name, value in zip(field_names, field_values):
            if name and value:
                db.insert("INSERT INTO product_attributes (product_id, field_name, field_value) VALUES (%s,%s,%s)", (product["id"], name, value))

        messages.success(request, f"Product '{title}' added successfully to {category['name']}")
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
        subcategory_id = request.POST.get("subcategory", "")
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




def approve_product(request):
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")
    
    return render(request, 'superadmin/Approveproduct.html')

def approve_product_list(request):
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")
    
    return render(request, 'superadmin/Approveproductlist.html')

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

    # Get existing admin data
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (id,))
    if not admin:
        messages.error(request, "Admin not found.")
        return redirect("sellers")
    
    admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
    if not admin or not admin["is_superadmin"]:
        messages.error(request, "Access denied. Super admin only.")
        return redirect("admin-home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        organization = request.POST.get("organization", "").strip()
        address = request.POST.get("address", "").strip()
        joining_date = request.POST.get("joining_date", "").strip()
        photo_file = request.FILES.get("photo")

        # Convert date (dd/mm/yyyy → yyyy-mm-dd)
        from datetime import datetime
        try:
            formatted_date = datetime.strptime(joining_date, "%d/%m/%Y").date() if joining_date else None
        except ValueError:
            formatted_date = None

        # Update photo if a new one is uploaded
        photo_path = admin["photo"]
        if photo_file:
            # Delete old photo
            if photo_path:
                old_photo_path = os.path.join(settings.MEDIA_ROOT, photo_path)
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)

            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "admins"))
            filename = get_random_string(8) + "_" + photo_file.name
            saved_name = fs.save(filename, photo_file)
            photo_path = f"admins/{saved_name}"

        # Update DB record
        db.update("""
            UPDATE adminusers 
            SET username=%s, email=%s, phone=%s, organization=%s, address=%s, photo=%s, joining_date=%s
            WHERE id=%s
        """, (name, email, phone, organization, address, photo_path, formatted_date, id))

        messages.success(request, "Admin updated successfully!")
        response = redirect("sellers")

    # ✅ Immediately clear message storage (prevents showing again later)
        storage = messages.get_messages(request)
        storage.used = True

        return response

    return render(request, "superadmin/edit-admin.html", {"admin": admin})