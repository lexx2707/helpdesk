from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'helpdesk'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='helpdesk:dashboard', permanent=False)),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.ticket_update, name='ticket_update'),
    path('tickets/<int:pk>/close/', views.ticket_close, name='ticket_close'),
    path('tickets/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/export/pdf/", views.ticket_list_pdf, name="ticket_list_pdf"),
    path("tickets/<int:pk>/claim/", views.ticket_claim, name="ticket_claim"),
    path("tickets/<int:pk>/accept/", views.ticket_accept, name="ticket_accept"),
    
    # Users
    path("users/", views.users_list, name="users_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/deactivate/", views.user_deactivate, name="user_deactivate"),

    # PDF
    path("tickets/report/pdf/", views.ticket_summary_pdf, name="ticket_summary_pdf"),
    path("reports/year/<int:year>/pdf/", views.ticket_year_summary_pdf, name="ticket_year_summary_pdf"),

    # หน้าเว็บสรุปทั้งปี (สำคัญ!)
    path("reports/year/<int:year>/", views.ticket_year_summary_page, name="ticket_year_summary_page"),
]
