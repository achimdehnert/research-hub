"""Add Project model as mid-layer between Workspace and ResearchProject."""
from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("research", "0005_add_workspace_model"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("workspace", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="projects",
                    to="research.workspace",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="research_projects_owned",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_workspace_project_name",
            ),
        ),
        # Change ResearchProject.workspace related_name to avoid clash
        migrations.AlterField(
            model_name="researchproject",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="research_projects",
                to="research.workspace",
            ),
        ),
        migrations.AddField(
            model_name="researchproject",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="researches",
                to="research.project",
            ),
        ),
    ]
