# helpdesk/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Ticket, TicketComment, IssueType, UserProfile

HIDE_STATUS = {"closed"}
User = get_user_model()


def _display_name(user):
    full = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    return full or getattr(user, "username", "") or str(user)


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["issue_type", "contact", "description"]   # ✅ ไม่ใช้ title/category แล้ว
        widgets = {
            "issue_type": forms.Select(attrs={"class": "form-select"}),
            "contact": forms.TextInput(attrs={"class": "form-control", "placeholder": "เบอร์โทรหรือ Line ID"}),
            "description": forms.Textarea(attrs={"rows": 6, "class": "form-control", "placeholder": "ใส่รายละเอียด"}),
        }
        labels = {
            "issue_type": "งานที่แจ้ง",
            "contact": "เบอร์โทรหรือ Line ID",
            "description": "รายละเอียดปัญหา",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["issue_type"].queryset = IssueType.objects.filter(is_active=True).select_related("category")
        self.fields["issue_type"].empty_label = "— เลือกงานที่ต้องการแจ้ง —"

class TicketUpdateForm(forms.ModelForm):
    """ฟอร์มแก้ไข Ticket (ใช้โดย IT) + เพิ่มคอมเมนต์ในฟอร์มเดียว"""

    # ✅ ฟิลด์เพิ่มคอมเมนต์ (ไม่ได้อยู่ใน Model Ticket)
    comment = forms.CharField(
        required=False,
        label="คอมเมนต์",
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "class": "form-control",
                "placeholder": "พิมพ์คอมเมนต์ถึงผู้ใช้งาน",
            }
        ),
    )

    class Meta:
        model = Ticket
        fields = [
            "issue_type",
            "contact",
            "description",
            "status",
            "assignee",
        ]
        widgets = {
            "issue_type": forms.Select(attrs={"class": "form-select"}),
            "contact": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "เบอร์โทรหรือ Line ID"}
            ),
            "description": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "assignee": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "issue_type": "งานที่แจ้ง",
            "contact": "เบอร์โทรหรือ Line ID",
            "description": "รายละเอียด",
            "status": "สถานะ",
            "assignee": "ผู้รับผิดชอบ",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False

        # ✅ ให้รายการ issue เลือกได้เฉพาะ active
        if "issue_type" in self.fields:
            self.fields["issue_type"].queryset = (
                IssueType.objects.filter(is_active=True).select_related("category")
            )
            self.fields["issue_type"].empty_label = "— เลือกงานที่แจ้ง —"

        # 1) ซ่อนสถานะที่ปิดงานแล้วออกจากดรอปดาวน์
        if "status" in self.fields:
            choices = getattr(Ticket, "STATUS_CHOICES", [])
            self.fields["status"].choices = [
                (k, v) for k, v in choices if k not in HIDE_STATUS
            ]

        # 2) ดรอปดาวน์ Assignee เฉพาะ IT
        if "assignee" in self.fields:
            allowed_q = (
                Q(is_superuser=True)
                | Q(
                    user_permissions__codename="change_ticket",
                    user_permissions__content_type__app_label="helpdesk",
                )
                | Q(
                    groups__permissions__codename="change_ticket",
                    groups__permissions__content_type__app_label="helpdesk",
                )
            )
            qs = (
                User.objects.filter(is_active=True)
                .filter(allowed_q)
                .distinct()
                .order_by("first_name", "last_name", "username")
            )
            field = self.fields["assignee"]
            field.queryset = qs
            field.empty_label = "— เลือกผู้รับผิดชอบ —"
            field.label_from_instance = _display_name

    def clean_assignee(self):
        assignee = self.cleaned_data.get("assignee")
        if assignee and not (
            assignee.is_superuser or assignee.has_perm("helpdesk.change_ticket")
        ):
            raise forms.ValidationError("ผู้รับผิดชอบต้องเป็นพนักงาน IT เท่านั้น")
        return assignee


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "form-control",
                    "placeholder": "พิมพ์คอมเมนต์ถึงผู้ใช้งานงาน",
                }
            ),
        }
        labels = {"body": "คอมเมนต์"}


class UserEditForm(forms.ModelForm):
    contact = forms.CharField(
        label="เบอร์โทรหรือ Line ID",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active", "is_staff"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # เติมค่าเริ่มต้นจาก profile
        if self.instance and self.instance.pk:
            profile, _ = UserProfile.objects.get_or_create(user=self.instance)
            self.fields["contact"].initial = profile.contact

        # ใส่ class ให้ช่องอื่น ๆ (ถ้าคุณยังไม่ได้ทำ)
        for name, f in self.fields.items():
            if not getattr(f.widget, "input_type", "") == "checkbox":
                f.widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.contact = self.cleaned_data.get("contact", "") or ""
        if commit:
            profile.save()
        return user
