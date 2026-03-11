from django.db.models.signals import post_save
from django.dispatch import receiver
from organizations.models import Organization
from store.models import UserProfile


@receiver(post_save, sender=Organization)
def assign_org_admin(sender, instance, created, **kwargs):
    if created and instance.owner:
        user = instance.owner

        # allow admin panel access
        user.is_staff = True
        user.save()

        # create/update profile
        profile, created = UserProfile.objects.get_or_create(user=user)

        profile.organization = instance
        profile.role = "org_admin"
        profile.save()