from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("research", "0003_add_summary_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="researchproject",
            name="citation_style",
            field=models.CharField(
                choices=[
                    ("none", "Keine Zitate"),
                    ("inline", "Im Text [Autor Jahr]"),
                    ("bibliography", "Literaturliste am Ende"),
                ],
                default="none",
                max_length=20,
            ),
        ),
    ]
