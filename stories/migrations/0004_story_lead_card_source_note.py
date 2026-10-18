from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stories", "0003_story_blocks"),
    ]

    operations = [
        migrations.AddField(
            model_name="story",
            name="lead",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="story",
            name="card",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="story",
            name="source_note",
            field=models.CharField(blank=True, max_length=300),
        ),
    ]
