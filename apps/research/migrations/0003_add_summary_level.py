from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("research", "0002_add_research_type_depth_sources"),
    ]

    operations = [
        migrations.AddField(
            model_name="researchproject",
            name="summary_level",
            field=models.CharField(
                choices=[
                    ("simple", "Einfach — verständlich für alle"),
                    ("medium", "Mittel — informierter Leser"),
                    ("complex", "Komplex — Fachpublikum"),
                    ("scientific", "Wissenschaftlich — Experten"),
                ],
                default="medium",
                max_length=20,
            ),
        ),
    ]
