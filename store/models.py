from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
from organizations.models import Organization

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('org_admin', 'Organization Admin'),
        ('pharmacist', 'Pharmacist'),
        ('customer', 'Customer'),
        ('staff', 'Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 🟢 ADD THIS
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
class Category(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()

    def __str__(self):
        return self.name

class Medicine(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=200)
    components = models.TextField(blank=True)
    product_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    company_name = models.CharField(max_length=200)
    power = models.CharField(max_length=50)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    image = models.ImageField(
        upload_to='medicines/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    low_stock_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = ('organization', 'product_number')

class Order(models.Model):
    organization = models.ForeignKey(   # 👈 ADD THIS
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
class OrderItem(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"
