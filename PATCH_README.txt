Patch contents (drop-in):
1) helpdesk/views.py — เพิ่ม permission checks (_is_it_staff), กรองรายการตามสิทธิ์, ล็อกแก้ไขเมื่อปิดงาน, ซ่อน internal สำหรับผู้ใช้ทั่วไป
2) helpdesk/templates/helpdesk/base.html — ใช้ไฟล์สไตล์รวมเดียว app.css + Logout แบบ POST (กัน 405)
3) helpdesk/templates/helpdesk/dashboard.html — โชว์ requester, แถวคลิกได้, แสดง badge สถานะ, เวลาท้องถิ่น d-m-Y H:i
4) helpdesk/templates/helpdesk/ticket_list.html — เพิ่มคอลัมน์ผู้แจ้งงาน, ซ่อนปุ่มแก้ไขเมื่อสถานะปิด, เวลาท้องถิ่น
5) helpdesk/templates/helpdesk/ticket_detail.html — เก็บข้อมูลแสดงผลให้เนียน ใช้ localtime
6) static/helpdesk/app.css — รวมธีม + สี badge ในไฟล์เดียว

วิธีลงแพตช์:
- สำรองไฟล์เดิมก่อน
- คัดลอกไฟล์ตาม path ข้างบนไปทับในโปรเจกต์
- แก้ base.html ใน MyApp (ถ้ามี) ให้ใช้ {% static 'helpdesk/app.css' %}
- ตั้งค่า logout URL ใน myproject/urls.py ใช้ LogoutView ได้เหมือนเดิม และปุ่มเป็น POST แล้ว
- เคลียร์แคชเบราว์เซอร์ หรือเพิ่ม ?v=2 ท้ายลิงก์ CSS

ออปชัน:
- ถ้าอยากเวลาระบบเป็นโซนไทย: settings.py → TIME_ZONE = 'Asia/Bangkok', USE_TZ = True
- ถ้าอยากลบสถานะ "resolved" ออกจากโมเดล ให้เพิ่ม migration เพื่อย้ายค่า resolved → closed ก่อน แล้วค่อยลบ choice