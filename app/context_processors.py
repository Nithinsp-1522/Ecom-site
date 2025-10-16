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
    if "admin_id" in request.session:
        admin = db.selectone("SELECT * FROM adminusers WHERE id=%s", (request.session["admin_id"],))
        return {"admin": admin}
    return {"admin": None}
    