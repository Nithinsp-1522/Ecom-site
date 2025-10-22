def category_context(request):
    from . import db
    try:
        categories = db.selectall("SELECT * FROM categories ORDER BY id ASC")
        subcategories = db.selectall("SELECT * FROM subcategories ORDER BY id ASC")
    except Exception:
        categories, subcategories = [], []

    return {
        "categories_all": categories,
        "subcategories": subcategories,
    }

def admin_context(request):
    from . import db
    context = {"admin": None, "pending_approvals": 0, "notifications": [], "unread_notifications": 0}

    if "admin_id" in request.session:
        admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
        context["admin"] = admin

        # ✅ Superadmin pending approval count
        if admin and admin.get("is_superadmin"):
            pending_count_row = db.selectone("""
                SELECT COUNT(*) AS count
                FROM products
                WHERE pending_approval=1 AND approved=0 AND disapproved=0
            """)
            context["pending_approvals"] = pending_count_row["count"] if pending_count_row else 0

        # ✅ Fetch latest notifications (5 most recent)
        notes = db.selectall("""
            SELECT * FROM notifications
            WHERE admin_id=%s
            ORDER BY created_at DESC
            LIMIT 5
        """, (request.session["admin_id"],))

        context["notifications"] = notes

        # ✅ Count unread notifications
        unread_row = db.selectone("""
            SELECT COUNT(*) AS count FROM notifications WHERE admin_id=%s AND is_read=0
        """, (request.session["admin_id"],))
        context["unread_notifications"] = unread_row["count"] if unread_row else 0

    return context

def get_cart_context(request):
    """Return cart count and item details for offcanvas"""
    cart_count = 0
    cart_items = []
    total_amount = 0

    if "user_id" in request.session:
        user_id = request.session["user_id"]
        cart_items = db.selectall("""
            SELECT c.id, c.product_id, c.quantity, 
                   p.title, p.price, p.sale_price,
                   (SELECT image FROM product_images WHERE product_id=p.id LIMIT 1) AS main_image
            FROM cart c
            JOIN products p ON p.id=c.product_id
            WHERE c.user_id=%s
        """, (user_id,))

        for item in cart_items:
            item["final_price"] = (item["sale_price"] or item["price"]) * item["quantity"]
            total_amount += item["final_price"]

        cart_count = sum([i["quantity"] for i in cart_items])

    return {"cart_items": cart_items, "cart_count": cart_count, "cart_total": total_amount}