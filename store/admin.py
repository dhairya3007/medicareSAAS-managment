from django.contrib import admin
from .models import Medicine, Order, OrderItem, Category, Supplier, UserProfile
from django.utils.html import format_html


# 🔹 CATEGORY ADMIN
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'description']
    list_filter = ['organization']
    search_fields = ['name', 'organization__name']
    list_per_page = 20


# 🔹 SUPPLIER ADMIN
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'contact_person', 'phone', 'email']
    list_filter = ['organization']
    search_fields = ['name', 'contact_person', 'organization__name']
    list_per_page = 20


# 🔹 MEDICINE ADMIN
class MedicineAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'organization',
        'company_name',
        'power',
        'price',
        'quantity',
        'category',
        'supplier',
        'expiry_date',
        'stock_status',
        'image_preview',
        'created_at'
    ]

    list_filter = ['organization', 'company_name', 'category', 'supplier', 'created_at']
    search_fields = ['name', 'company_name', 'product_number', 'organization__name']
    readonly_fields = ['image_preview', 'created_at', 'stock_status']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

    def stock_status(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color:red;font-weight:bold;">Out of Stock</span>')
        elif obj.is_low_stock():
            return format_html('<span style="color:orange;font-weight:bold;">Low Stock</span>')
        return format_html('<span style="color:green;font-weight:bold;">In Stock</span>')
    stock_status.short_description = 'Stock Status'


# 🔹 ORDER ITEM INLINE
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['medicine', 'quantity', 'price']


# 🔹 ORDER ADMIN
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'organization',
        'user',
        'order_date',
        'total_amount',
        'discount_percentage',
        'final_amount',
        'is_completed'
    ]

    list_filter = ['organization', 'order_date', 'is_completed']
    search_fields = ['user__username', 'id', 'organization__name']
    inlines = [OrderItemInline]
    readonly_fields = ['order_date']


# 🔹 USER PROFILE ADMIN
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'phone', 'loyalty_points']
    list_filter = ['organization', 'role']
    search_fields = ['user__username', 'organization__name']
    list_per_page = 20


# 🔹 REGISTER MODELS
admin.site.register(Category, CategoryAdmin)
admin.site.register(Supplier, SupplierAdmin)
admin.site.register(Medicine, MedicineAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(UserProfile, UserProfileAdmin)
