from django.urls import path
from . import views
from store.views import add_product
from django.contrib.admin.views.decorators import staff_member_required
from store import views

urlpatterns = [
    path('', views.home, name='home'),
    path('medicine/<int:medicine_id>/', views.medicine_detail, name='medicine_detail'),
    path('register/', views.register_view, name='register'),
      path('dashboard/', views.dashboard_view, name='dashboard'),
     path('api/stock-data/', views.stock_distribution_data, name='stock_data'),
    path('api/category-data/', views.category_distribution_data, name='category_data'),
    path('api/top-medicines-data/', views.top_medicines_data, name='top_medicines_data'),
    path('api/dashboard-stats/', views.dashboard_stats_data, name='dashboard_stats'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:medicine_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:medicine_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:medicine_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    # Protect the add_product view so only staff users access it
    path('admin/add-product/', add_product, name='add_product'),

    path('api/medicine/', views.api_add_medicine, name='api_add_medicine'),
    path('api/medicine/<int:medicine_id>/', views.api_update_medicine, name='api_update_medicine'),
    path('api/medicine/<int:medicine_id>/delete/', views.api_delete_medicine, name='api_delete_medicine'),
    path("switch-org/<int:org_id>/", views.switch_organization, name="switch_org"),
    path('invoice/<int:order_id>/', views.generate_invoice, name='generate_invoice'),
    path("invoice/<int:order_id>/preview/", views.invoice_preview, name="invoice_preview"),
]
