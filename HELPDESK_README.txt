IT Helpdesk Conversion (no PDF export yet)

Quick Start:
1) Install Django matching your Python version (see earlier suggestion).
2) Make migrations:
   python manage.py makemigrations helpdesk
   python manage.py migrate
3) Create superuser (optional for admin):
   python manage.py createsuperuser
4) Run:
   python manage.py runserver
5) Paths:
   /login/        -> เข้าสู่ระบบ
   /logout/       -> ออกจากระบบ
   /helpdesk/     -> Dashboard
   /helpdesk/tickets/        -> รายการใบงาน + ค้นหา/กรอง
   /helpdesk/tickets/create/ -> เปิดใบงานใหม่
   /helpdesk/tickets/<id>/   -> รายละเอียดงาน + คอมเมนต์
   /helpdesk/tickets/<id>/edit/ -> รับงาน/แก้ไข/เปลี่ยนสถานะ