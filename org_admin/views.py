from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from store.decorators import org_admin_required
from store.models import UserProfile
from store.utils import get_user_organization


@org_admin_required
def org_admin_home(request):
    return render(request, "org_admin/home.html")


@org_admin_required
def user_list(request):
    org = get_user_organization(request)

    users = UserProfile.objects.filter(
        organization=org
    ).select_related('user')

    return render(request, "org_admin/user_list.html", {"users": users})

@org_admin_required
def edit_user(request, user_id):
    org = get_user_organization(request)

    profile = get_object_or_404(
        UserProfile,
        id=user_id,
        organization=org
    )

    if request.method == "POST":
        profile.role = request.POST.get("role")
        profile.user.email = request.POST.get("email")
        profile.user.save()
        profile.save()

        return redirect('org_admin_users')

    return render(request, "org_admin/edit_user.html", {"profile": profile})


@org_admin_required
def toggle_user_status(request, user_id):
    org = get_user_organization(request)

    profile = get_object_or_404(
        UserProfile,
        id=user_id,
        organization=org
    )

    profile.user.is_active = not profile.user.is_active
    profile.user.save()

    return redirect('org_admin_users')

@org_admin_required
def delete_user(request, user_id):
    org = get_user_organization(request)

    profile = get_object_or_404(
        UserProfile,
        id=user_id,
        organization=org
    )

    # Prevent deleting yourself
    if profile.user == request.user:
        return redirect('org_admin_users')

    if request.method == "POST":
        profile.user.delete()
        return redirect('org_admin_users')

    return redirect('org_admin_users')
from store.models import Category, Supplier

@org_admin_required
def category_list(request):
    org = get_user_organization(request)
    categories = Category.objects.filter(organization=org)
    return render(request, "org_admin/category_list.html", {"categories": categories})


@org_admin_required
def add_category(request):
    org = get_user_organization(request)

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")

        Category.objects.create(
            organization=org,
            name=name,
            description=description
        )

        return redirect('org_admin_categories')

    return render(request, "org_admin/add_category.html")


@org_admin_required
def delete_category(request, category_id):
    org = get_user_organization(request)

    category = get_object_or_404(
        Category,
        id=category_id,
        organization=org
    )

    category.delete()
    return redirect('org_admin_categories')
@org_admin_required
def supplier_list(request):
    org = get_user_organization(request)
    suppliers = Supplier.objects.filter(organization=org)
    return render(request, "org_admin/supplier_list.html", {"suppliers": suppliers})


@org_admin_required
def add_supplier(request):
    org = get_user_organization(request)

    if request.method == "POST":
        Supplier.objects.create(
            organization=org,
            name=request.POST.get("name"),
            contact_person=request.POST.get("contact_person"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            address=request.POST.get("address"),
        )

        return redirect('org_admin_suppliers')

    return render(request, "org_admin/add_supplier.html")


@org_admin_required
def delete_supplier(request, supplier_id):
    org = get_user_organization(request)

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id,
        organization=org
    )

    supplier.delete()
    return redirect('org_admin_suppliers')
@org_admin_required
def edit_category(request, category_id):
    org = get_user_organization(request)

    category = get_object_or_404(
        Category,
        id=category_id,
        organization=org
    )

    if request.method == "POST":
        category.name = request.POST.get("name")
        category.description = request.POST.get("description")
        category.save()

        return redirect("org_admin_categories")

    return render(request, "org_admin/edit_category.html", {
        "category": category
    })
@org_admin_required
def edit_supplier(request, supplier_id):
    org = get_user_organization(request)

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id,
        organization=org
    )

    if request.method == "POST":
        supplier.name = request.POST.get("name")
        supplier.contact_person = request.POST.get("contact_person")
        supplier.phone = request.POST.get("phone")
        supplier.email = request.POST.get("email")
        supplier.address = request.POST.get("address")
        supplier.save()

        return redirect("org_admin_suppliers")

    return render(request, "org_admin/edit_supplier.html", {
        "supplier": supplier
    })
from django.contrib import messages
from django.contrib.auth.models import User
from store.models import UserProfile

@org_admin_required
def add_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")

        # 🔐 Check duplicate username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("org_admin_add_user")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # 🔥 Auto-set Django staff if role is staff or org_admin
        if role in ["staff", "Pharmacist"]:
            user.is_staff = True
            user.save()


        # 🔥 SAFELY get or create profile
        profile, created = UserProfile.objects.get_or_create(user=user)

        profile.organization = get_user_organization(request)
        profile.role = role
        profile.save()

        messages.success(request, "User created successfully.")
        return redirect("org_admin_users")

    return render(request, "org_admin/add_user.html")
