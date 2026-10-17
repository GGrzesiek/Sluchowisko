from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("facts", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="SeenFact"),
        migrations.DeleteModel(name="Fact"),
        migrations.DeleteModel(name="Place"),
    ]
