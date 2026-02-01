from django.db import migrations

def forwards(apps, schema_editor):
    Ticket = apps.get_model('helpdesk', 'Ticket')
    # ย้ายทุกแถวที่เคยเป็น resolved -> closed
    Ticket.objects.filter(status='resolved').update(status='closed')

def backwards(apps, schema_editor):
    # ไม่ย้อนกลับ
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('helpdesk', '0002_alter_ticket_status'),  # ★ ต่อจาก 0002
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
