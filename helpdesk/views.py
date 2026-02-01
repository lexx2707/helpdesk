# helpdesk/views.py — full drop-in

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timezone import make_aware
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa
from xhtml2pdf.default import DEFAULT_FONT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Ticket, TicketComment, Category, TicketImage, TicketAttachment

import os

from io import BytesIO  # เผื่อใช้ภายหลัง
import datetime as dt
from django.conf import settings
from django.contrib.staticfiles import finders
from .models import Ticket, TicketComment, Category, UserProfile
from .forms import TicketForm, TicketUpdateForm, TicketCommentForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.models import Group


User = get_user_model()

# สถานะที่ถือว่า "จบงาน" (ห้ามแก้ไข)
CLOSED_CODES = ["closed"]

def _order_open_first(qs):
    """
    ให้ Ticket ที่ยังไม่ปิดอยู่บนสุดเสมอ แล้วค่อยเรียงล่าสุดก่อน
    """
    return qs.annotate(
        is_closed=Case(
            When(status__in=CLOSED_CODES, then=1),
            default=0,
            output_field=IntegerField(),
        )
    ).order_by(
        "is_closed",     # 0 (ยังไม่ปิด) มาก่อน 1 (ปิดแล้ว)
        "-updated_at",
        "-created_at",
        "-id",
    )

# ชื่อเดือนย่อภาษาไทย สำหรับแสดงผลในรายงาน
MONTH_LABELS_TH = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.",
    "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.",
    "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

# ===== Helper =====
def _is_it_staff(user):
    """เจ้าหน้าที่ IT = superuser หรือมีสิทธิ์ change_ticket"""
    return user.is_superuser or user.has_perm("helpdesk.change_ticket")


def _display_name(u):
    full = (getattr(u, "get_full_name", lambda: "")() or "").strip()
    return full or getattr(u, "username", "") or str(u)

# ===== Dashboard =====
@login_required
def dashboard(request):
    user = request.user

    # ขอบเขตที่เห็นได้
    if _is_it_staff(user):
        visible_qs = Ticket.objects.all()
    else:
        # ผู้ใช้ทั่วไป: งานที่ตัวเองร้องขอ หรือถูกมอบหมายให้ตัวเอง
        visible_qs = Ticket.objects.filter(
            Q(requester=user) | Q(assignee=user)
        )

    # KPI ด้านบน (ไม่ตามฟิลเตอร์)
    my_open_count = (
        visible_qs.filter(requester=user)
        .exclude(status__in=CLOSED_CODES)
        .count()
    )

    assigned_to_me = (
        visible_qs.filter(assignee=user)
        .exclude(status__in=CLOSED_CODES)
        .count()
    )

    # ---------- ฟิลเตอร์สำหรับ "รายการล่าสุด" + By Status ----------
    qs = visible_qs

    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    date_from_str = (request.GET.get("date_from") or "").strip()
    date_to_str = (request.GET.get("date_to") or "").strip()

    # ค้นหาคำใน ชื่อเรื่อง/รายละเอียด
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    # ฟิลเตอร์ตามสถานะ
    if status:
        qs = qs.filter(status=status)

    # ฟิลเตอร์ช่วงวันที่
    def _parse_date(s):
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    df = _parse_date(date_from_str)
    dt_ = _parse_date(date_to_str)

    field = (
        "updated_at"
        if hasattr(Ticket, "updated_at")
        else ("created_at" if hasattr(Ticket, "created_at") else None)
    )
    if field:
        if df:
            start = make_aware(dt.datetime.combine(df, dt.time.min))
            qs = qs.filter(**{f"{field}__gte": start})
        if dt_:
            end = make_aware(dt.datetime.combine(dt_, dt.time.max))
            qs = qs.filter(**{f"{field}__lte": end})

    # รายการล่าสุด (หลังฟิลเตอร์แล้ว) — เปิดงานอยู่บนสุดเสมอ
    recent = qs.order_by("-id")

    # mapping จาก STATUS_CHOICES (จะเป็นไทย/อังกฤษตามที่คุณตั้งใน models.py)
    STATUS_LABELS = dict(getattr(Ticket, "STATUS_CHOICES", []))
    STATUS_ORDER = ["open", "in_progress", "on_hold", "closed"]

    by_status_qs = qs.values("status").annotate(c=Count("id")).order_by()
    by_status = [
        {
            "status": (r["status"] or "unknown"),
            "label": STATUS_LABELS.get(r["status"], r["status"] or "ไม่ทราบสถานะ"),
            "c": r["c"],
        }
        for r in by_status_qs
    ]

    order_index = {code: i for i, code in enumerate(STATUS_ORDER)}
    by_status.sort(key=lambda x: order_index.get(x["status"], 999))

    status_choices = getattr(Ticket, "STATUS_CHOICES", [])

    ctx = {
        "my_open_count": my_open_count,
        "assigned_to_me": assigned_to_me,
        "recent": recent,
        "by_status": by_status,
        "closed_codes": CLOSED_CODES,

        # สำหรับฟอร์ม FILTER ใน dashboard.html
        "q": q,
        "status": status,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "status_choices": status_choices,

        # 👉 ส่ง flag ว่าคนนี้เป็น IT หรือไม่
        "is_it_staff": _is_it_staff(user),
    }
    return render(request, "helpdesk/dashboard.html", ctx)

# ===== List =====
@login_required
def ticket_list(request):
    """
    IT: เห็นทุกงาน
    ผู้ใช้ทั่วไป: เห็นเฉพาะที่ตัวเอง 'ร้องขอ' (requester)
    รองรับตัวกรอง q, status, date_from, date_to
    """
    if _is_it_staff(request.user):
        qs = Ticket.objects.all()
    else:
        qs = Ticket.objects.filter(requester=request.user)

    # ------- รับพารามิเตอร์ -------
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    date_from_str = (request.GET.get("date_from") or "").strip()
    date_to_str = (request.GET.get("date_to") or "").strip()

    # ------- คีย์เวิร์ด -------
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # ------- สถานะ -------
    if status:
        qs = qs.filter(status=status)

    # ------- ช่วงวันที่ (รวมปลายทางทั้งวัน) -------
    def _parse_date(s):
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    df = _parse_date(date_from_str)
    dt_ = _parse_date(date_to_str)

    # field เวลาอ้างอิง: updated_at > created_at
    field = (
        "updated_at"
        if hasattr(Ticket, "updated_at")
        else ("created_at" if hasattr(Ticket, "created_at") else None)
    )
    if field:
        if df:
            start = make_aware(dt.datetime.combine(df, dt.time.min))
            qs = qs.filter(**{f"{field}__gte": start})
        if dt_:
            end = make_aware(dt.datetime.combine(dt_, dt.time.max))
            qs = qs.filter(**{f"{field}__lte": end})

    # เรียง: เปิดงานก่อนเสมอ แล้วล่าสุดก่อน
    qs = _order_open_first(qs)  

    status_choices = getattr(Ticket, "STATUS_CHOICES", [])
    total = qs.count()

    ctx = {
        "tickets": qs,
        "q": q,
        "status": status,
        "status_choices": status_choices,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "total": total,
        "closed_codes": CLOSED_CODES,
    }
    return render(request, "helpdesk/ticket_list.html", ctx)

@login_required
def ticket_list_pdf(request):
    """
    สร้าง PDF รายการ Ticket ตาม filter เดียวกับหน้า /helpdesk/tickets/
    """
    user = request.user

    # ขอบเขตข้อมูลที่ดูได้เหมือนใน ticket_list
    if _is_it_staff(user):
        qs = Ticket.objects.all()
    else:
        qs = Ticket.objects.filter(requester=user)

    # ------- รับพารามิเตอร์จาก GET (เหมือน ticket_list) -------
    q = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    date_from_str = (request.GET.get("date_from") or "").strip()
    date_to_str = (request.GET.get("date_to") or "").strip()

    # ------- คีย์เวิร์ด -------
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    # ------- สถานะ -------
    if status:
        qs = qs.filter(status=status)

    # ------- ช่วงวันที่ (รวมปลายทางทั้งวัน) -------
    def _parse_date(s):
        try:
            return dt.datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    df = _parse_date(date_from_str)
    dt_ = _parse_date(date_to_str)

    field = (
        "updated_at"
        if hasattr(Ticket, "updated_at")
        else ("created_at" if hasattr(Ticket, "created_at") else None)
    )

    if field:
        if df:
            start = make_aware(dt.datetime.combine(df, dt.time.min))
            qs = qs.filter(**{f"{field}__gte": start})
        if dt_:
            end = make_aware(dt.datetime.combine(dt_, dt.time.max))
            qs = qs.filter(**{f"{field}__lte": end})

        # ✅ เรียงเก่าก่อน → ใหม่ (งานแรก → งานสุดท้าย)
        qs = qs.order_by("created_at", "id")   # หรือใช้ "id" อย่างเดียวก็ได้
        # qs = qs.order_by("id")

    tickets = qs
    total = tickets.count()

    # ===== REGISTER THAI FONT (ใช้ THSarabunNew) =====
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "THSarabunNew.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("THSarabun", font_path))
        DEFAULT_FONT["helvetica"] = "THSarabun"

    context = {
        "tickets": tickets,
        "total": total,
        "q": q,
        "status": status,
        "date_from": date_from_str,
        "date_to": date_to_str,
    }

    template = get_template("helpdesk/ticket_list_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="tickets_filtered.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("เกิดข้อผิดพลาดในการสร้างไฟล์ PDF", status=500)

    return response

# ===== Detail =====
@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    # สิทธิ์การมองเห็น: IT หรือ requester หรือ assignee
    if not (
        _is_it_staff(request.user)
        or ticket.requester_id == request.user.id
        or ticket.assignee_id == request.user.id
    ):
        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงใบงานนี้")

    # คอมเมนต์: ถ้ามี internal=True ให้ซ่อนจาก non-staff
    comments = TicketComment.objects.filter(ticket=ticket).order_by("created_at")
    if not request.user.is_staff and hasattr(TicketComment, "internal"):
        comments = comments.filter(internal=False)

    comment_form = TicketCommentForm()

    return render(
        request,
        "helpdesk/ticket_detail.html",
        {
            "ticket": ticket,
            "comments": comments,
            "comment_form": comment_form,
            "closed_codes": CLOSED_CODES,
        },
    )


# ===== Create =====
@login_required
def ticket_create(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user

            # contact default จากโปรไฟล์
            if not (ticket.contact or "").strip():
                ticket.contact = (profile.contact or "").strip()

            ticket.save()   # 🔒 title/category ถูกเซ็ตจาก issue_type ใน Ticket.save()
            form.save_m2m()

            # จำ contact ใหม่กลับไป profile
            new_contact = (ticket.contact or "").strip()
            if new_contact and new_contact != (profile.contact or "").strip():
                profile.contact = new_contact
                profile.save(update_fields=["contact"])

            # save images (เหมือนที่คุณทำอยู่)
            files = request.FILES.getlist("images")
            for f in files:
                TicketImage.objects.create(ticket=ticket, image=f)

            return redirect("helpdesk:ticket_list")
    else:
        form = TicketForm(initial={"contact": (profile.contact or "").strip()})

    return render(request, "helpdesk/ticket_form.html", {"form": form, "mode": "create"})

# ===== Update =====
@login_required
@permission_required("helpdesk.change_ticket", raise_exception=True)
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    # แก้ไขได้เฉพาะ IT เท่านั้น
    if not _is_it_staff(request.user):
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไขใบงานนี้")
        return redirect("helpdesk:ticket_detail", pk=pk)

    # ต้องเป็น assignee หรือ superuser
    if request.user != ticket.assignee and not request.user.is_superuser:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์แก้ไขงานนี้")

    if ticket.status in CLOSED_CODES:
        messages.warning(request, "ใบงานปิดแล้ว ไม่สามารถแก้ไขได้")
        return redirect("helpdesk:ticket_detail", pk=pk)

    if request.method == "POST":
        # 🔸 ต้องใส่ request.FILES ด้วย
        form = TicketUpdateForm(request.POST, request.FILES, instance=ticket)
        if form.is_valid():
            ticket = form.save()

            comment_text = (form.cleaned_data.get("comment") or "").strip()
            if comment_text:
                TicketComment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    body=comment_text,
                )


            messages.success(request, "บันทึกการแก้ไขเรียบร้อย")
            return redirect("helpdesk:ticket_detail", pk=pk)
    else:
        form = TicketUpdateForm(instance=ticket)

    comment_form = TicketCommentForm()
    return render(
        request,
        "helpdesk/ticket_form.html",
        {
            "form": form,
            "ticket": ticket,
            "mode": "edit",
            "comment_form": comment_form,
            "closed_codes": CLOSED_CODES,
        },
    )


# ===== Add Comment =====
@login_required
def add_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method != "POST":
        return redirect("helpdesk:ticket_detail", pk=pk)

    # ใครคอมเมนต์ได้บ้าง: IT หรือ requester หรือ assignee
    if not (
        _is_it_staff(request.user)
        or ticket.requester_id == request.user.id
        or ticket.assignee_id == request.user.id
    ):
        raise PermissionDenied("คุณไม่มีสิทธิ์คอมเมนต์ใบงานนี้")

    form = TicketCommentForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.ticket = ticket
        c.author = request.user
        if hasattr(c, "internal"):
            c.internal = False
        c.save()
        messages.success(request, "เพิ่มคอมเมนต์เรียบร้อย")
    else:
        messages.error(request, "ข้อมูลคอมเมนต์ไม่ถูกต้อง")

    next_page = request.POST.get("next") or request.GET.get("next")
    if next_page == "edit":
        return redirect("helpdesk:ticket_update", pk=pk)
    return redirect("helpdesk:ticket_detail", pk=pk)

@login_required
@permission_required("helpdesk.change_ticket", raise_exception=True)
@require_POST
def ticket_claim(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    # IT เท่านั้น
    if not _is_it_staff(request.user):
        return HttpResponseForbidden("คุณไม่มีสิทธิ์รับงานนี้")

    # ห้ามรับงานถ้าปิดแล้ว
    if ticket.status in CLOSED_CODES:
        messages.warning(request, "งานนี้ปิดแล้ว ไม่สามารถรับงานได้")
        return redirect("helpdesk:ticket_detail", pk=pk)

    # ถ้ามีคนรับแล้ว และไม่ใช่ตัวเอง
    if ticket.assignee and ticket.assignee != request.user and not request.user.is_superuser:
        messages.warning(request, "งานนี้มีผู้รับผิดชอบแล้ว")
        return redirect("helpdesk:ticket_detail", pk=pk)

    ticket.assignee = request.user
    ticket.status = "in_progress"   # ✅ ต้องตรงกับ STATUS_CHOICES ใน model
    ticket.save(update_fields=["assignee", "status"])

    messages.success(request, "รับงานเรียบร้อย และเปลี่ยนสถานะเป็นกำลังดำเนินการ")
    return redirect("helpdesk:ticket_detail", pk=pk)


# ===== Transitions =====
@login_required
@permission_required("helpdesk.change_ticket", raise_exception=True)
@require_POST
def ticket_close(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if not _is_it_staff(request.user):
        return HttpResponseForbidden("คุณไม่มีสิทธิ์ปิดใบงานนี้")
    if not (request.user.is_superuser or request.user == ticket.assignee):
        return HttpResponseForbidden("เฉพาะผู้รับผิดชอบงานเท่านั้นที่ปิดงานได้")

    if ticket.status in CLOSED_CODES:
        messages.info(request, "ใบงานนี้ปิด/ยกเลิกไปแล้ว")
        return redirect("helpdesk:ticket_detail", pk=pk)

    # ✅ 1) บันทึกคอมเมนต์ (ถ้ามี) จากฟอร์มเดียวกัน
    comment_text = (request.POST.get("comment") or "").strip()
    if comment_text:
        TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            body=comment_text,
        )

    # ✅ 2) ปิดงาน
    ticket.status = "closed"
    ticket.save(update_fields=["status"])

    messages.success(request, "ปิดงานเรียบร้อย")
    return redirect("helpdesk:ticket_detail", pk=pk)

# ===== Users Management =====
@login_required
@permission_required("auth.view_user", raise_exception=True)
def users_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.all().order_by(
        "is_active", "is_staff", "first_name", "last_name", "username"
    )
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    return render(
        request,
        "helpdesk/users_list.html",
        {"users": qs, "q": q, "display_name": _display_name},
    )


@login_required
@permission_required("auth.add_user", raise_exception=True)
def user_create(request):
    class SimpleCreate(UserCreationForm):
        # ✅ เพิ่ม contact
        contact = forms.CharField(
            label="เบอร์โทรหรือ Line ID",
            required=False,
            widget=forms.TextInput(attrs={"class": "form-control"})
        )
        # เลือกกลุ่มตั้งแต่ตอนสร้างผู้ใช้
        GROUP_CHOICES = (
            ("user", "User (ผู้ใช้ทั่วไป)"),
            ("it", "IT Staff (เจ้าหน้าที่ IT)"),
        )
        group_choice = forms.ChoiceField(
            choices=GROUP_CHOICES,
            label="กลุ่มผู้ใช้",
            initial="user",
            widget=forms.Select(attrs={"class": "form-select"})
        )

        class Meta(UserCreationForm.Meta):
            model = User
            fields = ("username", "first_name", "last_name", "email")

    if request.method == "POST":
        form = SimpleCreate(request.POST)
        if form.is_valid():
            u = form.save(commit=False)
            u.is_active = True

            group_choice = form.cleaned_data.get("group_choice") or "user"

            # ถ้าเลือก IT Staff ให้เป็น staff ด้วย
            if group_choice == "it":
                u.is_staff = True
            else:
                u.is_staff = False

            u.save()
            # ✅ บันทึก contact ลงโปรไฟล์
            profile, _ = UserProfile.objects.get_or_create(user=u)
            profile.contact = (form.cleaned_data.get("contact") or "").strip()
            profile.save(update_fields=["contact"])

            # จัดกลุ่มให้ user
            group_name_map = {
                "user": "User",
                "it": "IT Staff",
            }
            target_name = group_name_map.get(group_choice)

            if target_name:
                group_obj, _ = Group.objects.get_or_create(name=target_name)
                u.groups.clear()
                u.groups.add(group_obj)

            messages.success(request, "สร้างผู้ใช้เรียบร้อย")
            return redirect("helpdesk:users_list")
    else:
        form = SimpleCreate()

    return render(
        request,
        "helpdesk/user_form.html",
        {"form": form, "mode": "create"},
    )

@login_required
@permission_required("auth.change_user", raise_exception=True)
def user_edit(request, pk):
    u = get_object_or_404(User, pk=pk)

    class SimpleChange(UserChangeForm):
        password = None  # ซ่อนฟิลด์ password ในฟอร์มหลัก

        contact = forms.CharField(
        label="เบอร์โทรหรือ Line ID",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
        )

        GROUP_CHOICES = (
            ("user", "User (ผู้ใช้ทั่วไป)"),
            ("it", "IT Staff (เจ้าหน้าที่ IT)"),
        )
        group_choice = forms.ChoiceField(
            choices=GROUP_CHOICES,
            label="กลุ่มผู้ใช้",
            required=False,
            widget=forms.Select(attrs={"class": "form-select"})
        )

        class Meta(UserChangeForm.Meta):
            model = User
            fields = ("first_name", "last_name", "email", "is_active", "is_staff")

    if request.method == "POST":
        form = SimpleChange(request.POST, instance=u)
        if form.is_valid():
            user_obj = form.save()

            profile, _ = UserProfile.objects.get_or_create(user=user_obj)
            new_contact = (form.cleaned_data.get("contact") or "").strip()
            profile.contact = new_contact
            profile.save(update_fields=["contact"])

            group_choice = form.cleaned_data.get("group_choice")

            if group_choice:
                group_name_map = {
                    "user": "User",
                    "it": "IT Staff",
                }
                target_name = group_name_map.get(group_choice)
                if target_name:
                    group_obj, _ = Group.objects.get_or_create(name=target_name)
                    user_obj.groups.clear()
                    user_obj.groups.add(group_obj)

                # sync is_staff ให้ตรงกับกลุ่มที่เลือก
                if group_choice == "it":
                    user_obj.is_staff = True
                else:
                    user_obj.is_staff = False
                user_obj.save(update_fields=["is_staff"])

            messages.success(request, "บันทึกผู้ใช้เรียบร้อย")
            return redirect("helpdesk:users_list")
    else:
        form = SimpleChange(instance=u)
        # ตั้งค่าเริ่มต้นของ group_choice จากกลุ่มที่ user อยู่ปัจจุบัน
        if u.groups.filter(name="IT Staff").exists():
            form.fields["group_choice"].initial = "it"
        else:
            form.fields["group_choice"].initial = "user"
        profile, _ = UserProfile.objects.get_or_create(user=u)
        form.fields["contact"].initial = profile.contact

    return render(
        request,
        "helpdesk/user_form.html",
        {"form": form, "mode": "edit", "user_obj": u},
    )


@login_required
@permission_required("auth.delete_user", raise_exception=True)
@require_POST
def user_deactivate(request, pk):
    u = get_object_or_404(User, pk=pk)
    if u.is_superuser:
        messages.error(request, "ห้ามปิดใช้งาน superuser")
    else:
        u.is_active = False
        u.save(update_fields=["is_active"])
        messages.success(request, "ปิดใช้งานผู้ใช้แล้ว")
    return redirect("helpdesk:users_list")


# ===== Helper สำหรับรายงานปี (ใช้ร่วม PDF/HTML) =====
def _build_year_summary(year):
    """คืนข้อมูลที่ใช้แสดงตารางสรุปใบงานทั้งปี"""
    qs = Ticket.objects.filter(created_at__year=year)

    month_numbers = list(range(1, 13))   # ใช้สำหรับ filter ใน DB
    categories = list(Category.objects.all().order_by("name"))

    rows = []
    grand_total = 0

    for cat in categories:
        monthly = []
        row_total = 0
        for m in month_numbers:
            c = qs.filter(category=cat, created_at__month=m).count()
            monthly.append(c)
            row_total += c
        grand_total += row_total

        rows.append({
            "category": cat,
            "monthly": monthly,
            "row_total": row_total,
        })

    # รวมแต่ละเดือน (แนวตั้ง)
    month_totals = []
    for m in month_numbers:
        c = qs.filter(created_at__month=m).count()
        month_totals.append(c)

    return {
        "months": MONTH_LABELS_TH,  # <== ส่งชื่อเดือนย่อออกไป
        "rows": rows,
        "month_totals": month_totals,
        "grand_total": grand_total,
    }

def link_callback(uri, rel):
    """
    ทำให้ xhtml2pdf หาไฟล์ใน STATICFILES (css, fonts, รูป) เจอ
    """
    # ถ้าเป็นไฟล์ใน STATIC_URL (เช่น /static/...)
    if uri.startswith(settings.STATIC_URL):
        path = uri.replace(settings.STATIC_URL, "")
        result = finders.find(path)
        if result:
            # ถ้าเจอหลาย path ให้ใช้ตัวแรก
            if isinstance(result, (list, tuple)):
                result = result[0]
            return result

    # ถ้าเป็น URL http(s) ไปเลยก็ให้คืนค่าเดิม
    return uri


    # รวมแต่ละเดือน (แนวตั้ง)
    month_totals = []
    for m in months:
        c = qs.filter(created_at__month=m).count()
        month_totals.append(c)

    return {
        "months": months,
        "rows": rows,
        "month_totals": month_totals,
        "grand_total": grand_total,
    }


# ===== HTML Report : หน้าเว็บสรุปงานรายปี =====
@login_required
def ticket_year_summary_page(request, year):
    """
    แสดงหน้าเว็บสรุปงานรายปี (HTML)
    """
    if not _is_it_staff(request.user):
        return HttpResponseForbidden("อนุญาตเฉพาะเจ้าหน้าที่ IT เท่านั้น")

    # ถ้ามี ?year= ใน query ให้ใช้ค่านั้นแทนปีจาก URL
    try:
        year_param = int(request.GET.get("year", year))
    except (TypeError, ValueError):
        year_param = year
    year = year_param  # ใช้ตัวแปร year ต่อจากนี้

    qs = Ticket.objects.filter(created_at__year=year)

    month_numbers = list(range(1, 13))
    categories = list(Category.objects.all().order_by("name"))

    rows = []
    grand_total = 0

    for cat in categories:
        monthly = []
        row_total = 0
        for m in month_numbers:
            count = qs.filter(category=cat, created_at__month=m).count()
            monthly.append(count)
            row_total += count
        grand_total += row_total

        rows.append({
            "category": cat,
            "monthly": monthly,
            "row_total": row_total
        })

    month_totals = []
    for m in month_numbers:
        count = qs.filter(created_at__month=m).count()
        month_totals.append(count)

    context = {
        "year": year,
        "months": MONTH_LABELS_TH,   # ถ้าพี่ประกาศ MONTH_LABELS_TH ไว้ด้านบนแล้ว
        "rows": rows,
        "month_totals": month_totals,
        "grand_total": grand_total,
    }

    return render(request, "helpdesk/ticket_year_summary.html", context)

# ===== PDF Report : สรุปจำนวนใบงานรายปี (ใช้ year จาก query) =====
def ticket_summary_pdf(request):
    if not _is_it_staff(request.user):
        return HttpResponseForbidden("อนุญาตเฉพาะเจ้าหน้าที่ IT เท่านั้น")

    try:
        year = int(request.GET.get("year", timezone.now().year))
    except ValueError:
        year = timezone.now().year

    summary = _build_year_summary(year)

    # ==== REGISTER THAI FONT ====
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "THSarabunNew.ttf")
    pdfmetrics.registerFont(TTFont("THSarabun", font_path))
    DEFAULT_FONT["helvetica"] = "THSarabun"

    context = {
        "year": year,
        **summary,
    }

    template = get_template("helpdesk/ticket_report_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    filename = f"ticket_summary_{year}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
    )

    if pisa_status.err:
        return HttpResponse("เกิดข้อผิดพลาดในการสร้างไฟล์ PDF", status=500)
    return response

# ===== PDF Report : สรุปจำนวนใบงานรายปี (ใช้ year จาก URL) =====
@login_required
def ticket_year_summary_pdf(request, year):
    if not _is_it_staff(request.user):
        return HttpResponseForbidden("อนุญาตเฉพาะเจ้าหน้าที่ IT เท่านั้น")

    summary = _build_year_summary(year)

    font_path = (
        settings.BASE_DIR / "static" / "fonts" / "THSarabunNew.ttf"
    ).as_posix()

    context = {
        "year": year,
        "th_sarabun_path": font_path,  # ★ ส่งเข้า template
        **summary,
    }

    template = get_template("helpdesk/ticket_report_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    filename = f"ticket_year_summary_{year}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("เกิดข้อผิดพลาดในการสร้างไฟล์ PDF", status=500)

    return response

# views.py
@login_required
@permission_required("helpdesk.change_ticket", raise_exception=True)
@require_POST
def ticket_accept(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if ticket.status in CLOSED_CODES:
        messages.info(request, "งานนี้ปิดแล้ว")
        return redirect("helpdesk:ticket_detail", pk=pk)

    # ถ้ามีคนรับแล้ว และไม่ใช่ตัวเอง/ไม่ใช่ superuser -> กันแย่ง
    if ticket.assignee and ticket.assignee != request.user and not request.user.is_superuser:
        messages.error(request, "งานนี้มีผู้รับผิดชอบแล้ว")
        return redirect("helpdesk:ticket_detail", pk=pk)

    ticket.assignee = request.user
    ticket.status = "in_progress"  # หรือโค้ดสถานะที่พี่ใช้จริง
    ticket.save(update_fields=["assignee", "status"])

    messages.success(request, "รับงานเรียบร้อย")
    return redirect("helpdesk:ticket_update", pk=pk)  # ✅ เด้งไปหน้า 🛠 ตรวจสอบงาน
