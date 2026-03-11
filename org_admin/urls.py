from django.urls import path
from . import views

urlpatterns = [
    path('', views.org_admin_home, name='org_admin_home'),
    path('users/', views.user_list, name='org_admin_users'),
    path('users/add/', views.add_user, name='org_admin_add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='org_admin_edit_user'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='org_admin_toggle_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='org_admin_delete_user'),

    # Categories
path('categories/', views.category_list, name='org_admin_categories'),
path('categories/add/', views.add_category, name='org_admin_add_category'),
path('categories/<int:category_id>/delete/', views.delete_category, name='org_admin_delete_category'),

# Suppliers
path('suppliers/', views.supplier_list, name='org_admin_suppliers'),
path('suppliers/add/', views.add_supplier, name='org_admin_add_supplier'),
path('suppliers/<int:supplier_id>/delete/', views.delete_supplier, name='org_admin_delete_supplier'),
path(
    'suppliers/<int:supplier_id>/edit/',
    views.edit_supplier,
    name='org_admin_edit_supplier'
),


path(
    'categories/<int:category_id>/edit/',
    views.edit_category,
    name='org_admin_edit_category'
),

]
