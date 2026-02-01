from django.conf import settings
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class IssueType(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="issue_types")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        # กันซ้ำ: ชื่อเดียวกันแต่คนละหมวด = อนุญาตได้, แต่ชื่อเดียวกันในหมวดเดียว = ไม่ซ้ำ
        constraints = [
            models.UniqueConstraint(fields=["name", "category"], name="uniq_issue_per_category")
        ]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("open", "เปิดงาน"),
        ("in_progress", "กำลังดำเนินการ"),
        ("on_hold", "พักงาน"),
        ("closed", "เสร็จแล้ว"),
    ]

    # ✅ ให้ user เลือก Issue แทนการพิมพ์ Title
    issue_type = models.ForeignKey(
        IssueType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    contact = models.CharField("เบอร์โทรหรือ Line ID", max_length=100, blank=True)

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="requested_tickets"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_tickets"
    )

    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # 🔒 ล็อก Title และ Category ให้มาจาก IssueType เท่านั้น
        if self.issue_type_id:
            self.title = self.issue_type.name
            self.category = self.issue_type.category
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.pk} {self.title}"


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    internal = models.BooleanField(default=False, help_text="Visible to staff only")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.ticket}"


class TicketImage(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="ticket_images/%Y/%m/%d/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for #{self.ticket_id}"


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.ImageField(upload_to="ticket_attachments/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Attachment for #{self.ticket_id} - {self.file.name}"


# ✅ ย้ายออกมาเป็น model ของตัวเอง (ไม่อยู่ใน TicketAttachment)
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    contact = models.CharField(
        "เบอร์โทรหรือ Line ID",
        max_length=255,
        blank=True,
        default="",
    )

    def __str__(self):
        return self.user.username
