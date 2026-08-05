from django.contrib import admin
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "status",
        "is_active",
        "allow_inventory_sharing",
        "ai_assistant_enabled",
        "dashboard_ai_enabled",
        "created_at",
    )

    list_filter = (
        "status",
        "is_active",
        "allow_inventory_sharing",
        "ai_assistant_enabled",
        "dashboard_ai_enabled",
    )

    list_editable = (
        "ai_assistant_enabled",
        "dashboard_ai_enabled",
        "allow_inventory_sharing",
        "is_active",
    )

    search_fields = (
        "name",
    )