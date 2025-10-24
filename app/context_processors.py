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





