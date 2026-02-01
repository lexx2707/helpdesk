from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # หน้าแรก = หน้า Login
    path('', auth_views.LoginView.as_view(
        template_name='helpdesk/login.html'
    ), name='login'),

    # Helpdesk app
    path('helpdesk/', include(('helpdesk.urls', 'helpdesk'), namespace='helpdesk')),

    # login / logout
    path('login/', auth_views.LoginView.as_view(
        template_name='helpdesk/login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Django admin
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
