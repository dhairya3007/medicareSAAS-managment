from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates a superuser if one does not already exist'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@admin.com',
                password='admin9898'
            )
            self.stdout.write(self.style.SUCCESS('✅ Superuser "admin" created successfully'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ Superuser "admin" already exists — skipping'))
