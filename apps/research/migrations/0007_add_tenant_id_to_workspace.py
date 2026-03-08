"""Migration: add tenant_id to Workspace for multi-tenancy support."""
from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("research", "0006_add_project_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="tenant_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text="Organization.tenant_id from django_tenancy. NULL = personal workspace.",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(fields=["tenant_id"], name="idx_workspace_tenant"),
        ),
    ]
