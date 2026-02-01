from django.db import migrations

def forwards(apps, schema_editor):
    Ticket = apps.get_model('helpdesk', 'Ticket')
    Ticket.objects.filter(status='resolved').update(status='closed')

def backwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0004_alter_ticket_status'),  # เปลี่ยนเลขให้ตรง "ไฟล์ล่าสุดจริง" ของเล็ก
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
