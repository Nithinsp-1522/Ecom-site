def category_context(request):
    from . import db  # your existing db helper
    try:
        categories = db.selectall("SELECT * FROM categories ORDER BY id ASC")
    except Exception:
        categories = []

    # Split categories into groups of 10 for dropdowns
    def chunk_list(data, chunk_size):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    category_groups = chunk_list(categories, 10)
    return {"category_groups": category_groups, "categories_all": categories}
