from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import UserProfile

User = get_user_model()

def it_contact(request):
    # หา IT 1 คน (กรณีองค์กรมีคนเดียว)
    it_user = (
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name__icontains="IT") | Q(user_permissions__codename="change_ticket"))
        .distinct()
        .first()
    )

    contact = ""
    if it_user:
        profile, _ = UserProfile.objects.get_or_create(user=it_user)
        contact = profile.contact or ""

    return {"IT_CONTACT": contact}
