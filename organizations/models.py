from django.contrib.auth.models import User
from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=255)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_organizations"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
        ],
        default="active",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    allow_inventory_sharing = models.BooleanField(default=True)

    # NEW FIELD
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name