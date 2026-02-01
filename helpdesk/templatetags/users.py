from django import template

register = template.Library()

@register.filter
def display_name(user):
    """แสดงชื่อเต็มของผู้ใช้ ถ้าไม่มีให้ใช้ username แทน"""
    if not user:
        return "-"
    try:
        full = user.get_full_name().strip()
    except Exception:
        full = ""
    return full or getattr(user, "username", "-")

@register.filter(name="add_class")
def add_class(field, css):
    """ใส่ class เพิ่มให้ฟิลด์ฟอร์ม (เช่น form-control)"""
    existing_classes = field.field.widget.attrs.get("class", "")
    classes = (existing_classes + " " + css).strip()
    attrs = field.field.widget.attrs.copy()
    attrs["class"] = classes
    return field.as_widget(attrs=attrs)
