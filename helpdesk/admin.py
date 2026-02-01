from django.contrib import admin
from .models import (
    Category,
    IssueType,
    Ticket,
    TicketComment,
    TicketImage,
    TicketAttachment,
)

# ======================
# Category
# ======================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)


# ======================
# IssueType  ⭐ สำคัญที่สุด (Dropdown งานที่แจ้ง)
# ======================
@admin.register(IssueType)
class IssueTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("category__name", "name")

    # ป้องกันลบ Issue ที่ถูกใช้งานแล้ว (ทำแบบปลอดภัย ไม่ผูกชื่อ ticket_set)
    def has_delete_permission(self, request, obj=None):
        if not obj:
            return super().has_delete_permission(request, obj)

        # เช็คทุกความเป็นไปได้แบบปลอดภัย
        # 1) ถ้า Ticket มี FK ไป IssueType และไม่ได้ตั้ง related_name => ticket_set
        rel = getattr(obj, "ticket_set", None)
        if rel is not None and rel.exists():
            return False

        # 2) ถ้า Ticket ตั้ง related_name ไว้ (เช่น related_name="tickets")
        rel = getattr(obj, "tickets", None)
        if rel is not None and rel.exists():
            return False

        return super().has_delete_permission(request, obj)


# ======================
# Ticket
# ======================
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "issue_type",
        "status",
        "category",
        "requester",
        "assignee",
        "created_at",
        "due_at",
    )
    list_filter = ("status", "category", "assignee")
    search_fields = ("title", "description")
    autocomplete_fields = ("category", "requester", "assignee", "issue_type")
    ordering = ("-created_at",)


# ======================
# Ticket Comment
# ======================
@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "internal", "created_at")
    list_filter = ("internal",)
    search_fields = ("body",)
    ordering = ("-created_at",)


# ======================
# Images / Attachments (แสดงง่าย ๆ)
# ======================
@admin.register(TicketImage)
class TicketImageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "uploaded_at")
    ordering = ("-uploaded_at",)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "file", "uploaded_at")
    ordering = ("-uploaded_at",)
