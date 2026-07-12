from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from .models import Medicine, Order, OrderItem
from decimal import Decimal
import json
from .decorators import org_staff_required
from .utils import get_user_organization

def home(request):
    medicines = Medicine.objects.none()
    query = request.GET.get('q', '')

    if request.user.is_authenticated:
        org = get_user_organization(request)  # ✅ moved inside

        medicines = Medicine.objects.filter(
            organization=org
        ).order_by('-created_at')[:12]

        if query:
            medicines = Medicine.objects.filter(
                organization=org
            ).filter(
                Q(name__icontains=query) |
                Q(company_name__icontains=query) |
                Q(components__icontains=query)
            )

    return render(request, 'home.html', {
        'medicines': medicines,
        'query': query
    })


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    orders = Order.objects.filter(user=request.user, is_completed=True).order_by('-order_date')

    if request.method == 'POST':
        new_email = request.POST.get('email')
        if new_email:
            request.user.email = new_email
            request.user.save()
            messages.success(request, 'Email updated successfully.')
            return redirect('profile')
        else:
            messages.error(request, 'Please provide a valid email address.')

    return render(request, 'profile.html', {'orders': orders})

def get_cart(request):
    cart = request.session.get('cart', {})
    return cart

def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

@login_required
def add_to_cart(request, medicine_id):
    if request.method == 'POST':
        org = get_user_organization(request)

        medicine = get_object_or_404(
            Medicine,
            id=medicine_id,
            organization=org
        )

        cart = get_cart(request)
        
        medicine_id_str = str(medicine_id)
        if medicine_id_str in cart:
            cart[medicine_id_str]['quantity'] += 1
        else:
            cart[medicine_id_str] = {
                'name': medicine.name,
                'price': str(medicine.price),
                'quantity': 1,
                'image': medicine.image.url if medicine.image else '',
                'max_quantity': medicine.quantity
            }
        
        save_cart(request, cart)
        messages.success(request, f'{medicine.name} added to cart!')
        return redirect('cart_view')
    
    return redirect('medicine_detail', medicine_id=medicine_id)

@login_required
def cart_view(request):
    cart = get_cart(request)
    cart_items = []
    total = Decimal('0.00')
    
    for medicine_id, item in cart.items():
        item_total = Decimal(item['price']) * item['quantity']
        org = get_user_organization(request)
        cart_items.append({
            'id': medicine_id,
            'medicine': get_object_or_404(
                    Medicine,
                    id=medicine_id,
                    organization=org
                ),

            'quantity': item['quantity'],
            'price': item['price'],
            'total': item_total,
            'image': item['image']
        })
        total += item_total
    
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def update_cart(request, medicine_id):
    if request.method == 'POST':
        cart = get_cart(request)
        medicine_id_str = str(medicine_id)
        
        if medicine_id_str in cart:
            quantity_str = request.POST.get('quantity', '').strip()
            if not quantity_str.isdigit():
                messages.error(request, 'Enter a valid quantity.')
                return redirect('cart_view')
            
            quantity = int(quantity_str)
            org = get_user_organization(request)

            medicine = get_object_or_404(
                Medicine,
                id=medicine_id,
                organization=org
            )

            
            if quantity <= 0:
                del cart[medicine_id_str]
                messages.info(request, 'Item removed from cart.')
            elif quantity <= medicine.quantity:
                cart[medicine_id_str]['quantity'] = quantity
                messages.success(request, 'Cart updated!')
            else:
                messages.error(request, f'Only {medicine.quantity} available in stock.')
        
        save_cart(request, cart)
    
    return redirect('cart_view')


@login_required
def remove_from_cart(request, medicine_id):
    if request.method == 'POST':
        cart = get_cart(request)
        medicine_id_str = str(medicine_id)
        
        if medicine_id_str in cart:
            del cart[medicine_id_str]
            save_cart(request, cart)
            messages.info(request, 'Item removed from cart.')
    
    return redirect('cart_view')

from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def checkout_view(request):
    org = get_user_organization(request)
    cart = get_cart(request)
    if not cart:
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart_view')
    
    cart_items = []
    total = Decimal('0.00')
    
    for medicine_id, item in cart.items():
        medicine = get_object_or_404(
        Medicine,
        id=medicine_id,
        organization=org
    )

        if item['quantity'] > medicine.quantity:
            messages.error(request, f'Not enough stock for {medicine.name}. Only {medicine.quantity} available.')
            return redirect('cart_view')
        
        item_total = Decimal(item['price']) * item['quantity']
        cart_items.append({
            'medicine': medicine,
            'quantity': item['quantity'],
            'price': item['price'],
            'total': item_total
        })
        total += item_total
    
    discount_percentage = Decimal('0')
    final_amount = total

    if request.method == 'POST':
        # Only allow discount if user is staff/admin
        if request.user.is_staff:
            discount_input = request.POST.get('discount') or '0'
            discount_percentage = Decimal(discount_input)

            discount_amount = total * (discount_percentage / Decimal('100'))
            final_amount = total - discount_amount

        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    organization=org, # 👈 ADD THIS
                user=request.user,
                total_amount=total,
                discount_percentage=discount_percentage,
                final_amount=final_amount,
                is_completed=True
            )

                
                # Create order items and update medicine quantities
                for item in cart_items:
                    OrderItem.objects.create(
                        organization=org,
                        order=order,
                        medicine=item['medicine'],
                        quantity=item['quantity'],
                        price=item['price']
                    )

                    item['medicine'].quantity -= item['quantity']
                    item['medicine'].save()
                
                # Clear cart
                request.session['cart'] = {}
                request.session.modified = True
                
                messages.success(request, f'Order placed successfully! Total: ₹{final_amount:.2f}')
                return redirect('order_success', order_id=order.id)
                
       # except Exception as e:
            #messages.error(request, 'An error occurred during checkout. Please try again.')
        except Exception as e:
            print(e)
            raise e
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'final_amount': final_amount,
        'discount_percentage': discount_percentage,
        'now': timezone.now()  # pass current date/time for billing
    })
@login_required
def order_success(request, order_id):
    org = get_user_organization(request)

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        organization=org
    )

    return render(request, 'order_success.html', {'order': order})

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from .forms import MedicineForm
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import MedicineForm
from .decorators import org_staff_required

@org_staff_required
def add_product(request):
    org = get_user_organization(request)   # ✅ get organization first

    if request.method == 'POST':
        form = MedicineForm(
            request.POST,
            request.FILES,
            organization=org
        )

        if form.is_valid():
            medicine = form.save(commit=False)
            medicine.organization = org   # ✅ use org instead of userprofile
            medicine.save()

            messages.success(request, "Medicine added successfully!")
            return redirect('add_product')

    else:
        form = MedicineForm(
            organization=org
        )

    return render(request, 'add_product.html', {'form': form})

from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required

@org_staff_required
def redirect_to_medicine_admin(request):
    return redirect('admin:store_medicine_changelist')

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Medicine
from .forms import MedicineForm
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from .models import Medicine, Category, Supplier
from .forms import MedicineForm

@org_staff_required
def admin_product_management(request):
    """Comprehensive product management page with tenant filtering"""
    try:
        org = get_user_organization(request)  # 🔐 Tenant isolation

        filter_type = request.GET.get('filter', 'all')

        # Base queryset (ALWAYS tenant filtered)
        medicines = Medicine.objects.filter(
            organization=org
        ).order_by('-created_at')

        # Apply filters ON TOP of tenant filter
        if filter_type == 'expired':
            medicines = medicines.filter(
                expiry_date__lt=timezone.now().date()
            ).order_by('expiry_date')

        elif filter_type == 'low_stock':
            medicines = medicines.filter(
                quantity__lte=10
            ).order_by('quantity')

        elif filter_type == 'out_of_stock':
            medicines = medicines.filter(
                quantity=0
            ).order_by('name')

        # Categories & suppliers (optional: also filter by org if needed)
        categories = Category.objects.filter(organization=org)
        suppliers = Supplier.objects.filter(organization=org)

        form = MedicineForm(
    organization=org
)

        context = {
            'medicines': medicines,
            'categories': categories,
            'suppliers': suppliers,
            'form': form,
            'title': 'Product Management',
            'current_filter': filter_type,
            'expired_count': medicines.filter(
                expiry_date__lt=timezone.now().date()
            ).count(),
            'low_stock_count': medicines.filter(
                quantity__lte=10,
                quantity__gt=0
            ).count(),
            'out_of_stock_count': medicines.filter(
                quantity=0
            ).count(),
            'total_count': medicines.count(),
        }

        return render(request, 'admin_product_management.html', context)

    except Exception as e:
        print(f"Admin product management error: {e}")
        return render(request, 'admin_product_management.html', {
            'medicines': [],
            'categories': [],
            'form': MedicineForm(),
            'error_message': 'Error loading product management page'
        })
from decimal import Decimal ,InvalidOperation

from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

@org_staff_required
@csrf_exempt
@require_http_methods(["POST"])
@org_staff_required
@require_http_methods(["POST"])

def api_update_medicine(request, medicine_id):

    if request.method != "POST":
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)

    org = get_user_organization(request)

    medicine = get_object_or_404(
        Medicine,
        id=medicine_id,
        organization=org
    )

    try:
        data = json.loads(request.body)

        # -------- BASIC FIELDS --------

        if 'name' in data and data['name'] != "":
            medicine.name = data['name'].strip()

        if 'company_name' in data and data['company_name'] != "":
            medicine.company_name = data['company_name'].strip()

        if 'power' in data and data['power'] != "":
            medicine.power = data['power'].strip()

        # -------- NUMERIC FIELDS --------

        if 'quantity' in data and data['quantity'] != "":
            medicine.quantity = int(data['quantity'])

        if 'price' in data and data['price'] != "":
            try:
                medicine.price = Decimal(str(data['price']))
            except InvalidOperation:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid price format'
                }, status=400)

        # -------- DATE FIELD --------

        if 'expiry_date' in data and data['expiry_date']:
            try:
                medicine.expiry_date = datetime.strptime(
                    data['expiry_date'],
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid expiry date format (YYYY-MM-DD required)'
                }, status=400)

        # -------- SAFE CATEGORY UPDATE --------

        if 'category_id' in data and data['category_id']:
            category = get_object_or_404(
                Category,
                id=data['category_id'],
                organization=org
            )
            medicine.category = category

        # -------- SAFE SUPPLIER UPDATE --------

        if 'supplier_id' in data and data['supplier_id']:
            supplier = get_object_or_404(
                Supplier,
                id=data['supplier_id'],
                organization=org
            )
            medicine.supplier = supplier

        # -------- SAVE --------

        medicine.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Medicine updated successfully'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)

    except Exception as e:
        print("UPDATE ERROR:", e)  # 👈 shows real issue in terminal
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }, status=400)

@org_staff_required
@csrf_exempt
@require_http_methods(["POST"])

def api_add_medicine(request):
    org = get_user_organization(request)

    form = MedicineForm(
        request.POST,
        request.FILES,
        organization=org
    )

    if form.is_valid():
        medicine = form.save(commit=False)

        # 🔐 AUTO ASSIGN TENANT
        medicine.organization = get_user_organization(request)

        medicine.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Medicine added successfully',
            'medicine': {
                'id': medicine.id,
                'name': medicine.name,
                'company_name': medicine.company_name,
                'power': medicine.power,
                'price': str(medicine.price),
                'quantity': medicine.quantity,
                'image_url': medicine.image.url if medicine.image else ''
            }
        })
    else:
        print("FORM ERRORS:", form.errors)
        return JsonResponse({
            'status': 'error',
            'message': 'Form validation failed',
            'errors': form.errors
        }, status=400)


@org_staff_required
@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_medicine(request, medicine_id):
    """API endpoint to delete a medicine"""
    org = get_user_organization(request)

    medicine = get_object_or_404(
        Medicine,
        id=medicine_id,
        organization=org
    )

    medicine_name = medicine.name
    medicine.delete()
    
    return JsonResponse({
        'status': 'success',
        'message': f'Medicine "{medicine_name}" deleted successfully'
    })
from django.shortcuts import render, get_object_or_404
from .models import Medicine
import requests

def medicine_detail(request, medicine_id):
    org = get_user_organization(request)

    medicine = get_object_or_404(
        Medicine,
        id=medicine_id,
        organization=org
    )

    
    medicine_info = {
        "description": "No information available from FDA database",
        "uses": "No information available from FDA database", 
        "side_effects": "No information available from FDA database",
        "precautions": "No information available from FDA database",
    }

    try:
        # Try FDA API with the medicine name
        url = f'https://api.fda.gov/drug/label.json?search=openfda.brand_name:"{medicine.name}"&limit=1'
        print(f"🔍 API URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                result = data["results"][0]
                print("✅ FDA API returned data")
                print(f"🔑 Available keys: {list(result.keys())}")
                
                # Extract description from various possible fields
                if result.get("description"):
                    medicine_info["description"] = result["description"][0]
                elif result.get("purpose"):
                    medicine_info["description"] = result["purpose"][0]
                elif result.get("clinical_pharmacology"):
                    medicine_info["description"] = result["clinical_pharmacology"][0]
                
                # Extract uses
                if result.get("indications_and_usage"):
                    medicine_info["uses"] = result["indications_and_usage"][0]
                elif result.get("purpose"):
                    medicine_info["uses"] = result["purpose"][0]
                
                # EXTRACT SIDE EFFECTS - ENHANCED
                if result.get("adverse_reactions"):
                    medicine_info["side_effects"] = result["adverse_reactions"][0]
                elif result.get("warnings"):
                    medicine_info["side_effects"] = result["warnings"][0]
                elif result.get("boxed_warning"):
                    medicine_info["side_effects"] = result["boxed_warning"][0]
                elif result.get("contraindications"):
                    medicine_info["side_effects"] = result["contraindications"][0]
                elif result.get("drug_interactions"):
                    medicine_info["side_effects"] = result["drug_interactions"][0]
                # If still no side effects, use a generic message
                elif medicine_info["side_effects"] == "No information available from FDA database":
                    medicine_info["side_effects"] = "Common side effects may include nausea, headache, or dizziness. Consult your doctor for specific side effects."
                
                # Extract precautions
                if result.get("precautions"):
                    medicine_info["precautions"] = result["precautions"][0]
                elif result.get("warnings"):
                    medicine_info["precautions"] = result["warnings"][0]
                elif result.get("drug_interactions"):
                    medicine_info["precautions"] = result["drug_interactions"][0]
                elif result.get("contraindications"):
                    medicine_info["precautions"] = result["contraindications"][0]
                    
                print(f"📊 Extracted data - Description: {bool(result.get('description'))}, Uses: {bool(result.get('indications_and_usage'))}, Side Effects: {bool(result.get('adverse_reactions'))}, Precautions: {bool(result.get('precautions'))}")
                    
            else:
                print("❌ No results in FDA API response")
        else:
            print(f"❌ FDA API returned status: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Error calling FDA API: {e}")

    context = {
        'medicine': medicine,
        'medicine_info': medicine_info,
    }
    return render(request, 'product_detail.html', context)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import JsonResponse
import json
from .models import Medicine, Order, Category
from datetime import timedelta
@login_required
def dashboard_view(request):
    current_time = timezone.now()
    org = get_user_organization(request)

    filter_type = request.GET.get("filter", "recent")
    month = request.GET.get("month")
    year = request.GET.get("year")

    total_medicines = Medicine.objects.filter(
        organization=org
    ).count()

    low_stock_medicines = Medicine.objects.filter(
        organization=org,
        quantity__lte=10
    )

    low_stock_count = low_stock_medicines.count()

    expired_medicines = Medicine.objects.filter(
        organization=org,
        expiry_date__lt=current_time.date()
    )

    expired_count = expired_medicines.count()

    out_of_stock_count = Medicine.objects.filter(
        organization=org,
        quantity=0
    ).count()

    total_revenue = Order.objects.filter(
        organization=org,
        is_completed=True
    ).aggregate(total=Sum('final_amount'))['total'] or 0

    total_orders = Order.objects.filter(
        organization=org,
        is_completed=True
    ).count()

    # 🔹 Base Query
    orders = Order.objects.filter(
        organization=org,
        is_completed=True
    ).select_related('user').order_by('-order_date')

    # 🔹 Last Week Filter
    if filter_type == "week":
        last_week = current_time - timedelta(days=7)
        orders = orders.filter(order_date__gte=last_week)

    # 🔹 Monthly Filter
    elif filter_type == "month" and month and year:
        orders = orders.filter(
            order_date__month=month,
            order_date__year=year
        )

    recent_orders = orders[:10]

    context = {
        'current_time': current_time,
        'total_medicines': total_medicines,
        'low_stock_count': low_stock_count,
        'low_stock_medicines': low_stock_medicines[:5],
        'expired_medicines': expired_medicines[:5],
        'expired_count': expired_count,
        'out_of_stock_count': out_of_stock_count,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'active_filter': filter_type
    }

    return render(request, 'dashboard.html', context)


# API endpoints for dynamic data
@login_required
@login_required
def stock_distribution_data(request):
    try:
        org = get_user_organization(request)

        medicines = Medicine.objects.filter(organization=org)

        total_medicines = medicines.count()
        low_stock_count = medicines.filter(quantity__lte=10).count()
        expired_count = medicines.filter(
            expiry_date__lt=timezone.now().date()
        ).count()
        out_of_stock_count = medicines.filter(quantity=0).count()

        in_stock_count = total_medicines - (
            low_stock_count + out_of_stock_count + expired_count
        )

        return JsonResponse({
            'labels': ['In Stock', 'Low Stock', 'Out of Stock', 'Expired'],
            'data': [in_stock_count, low_stock_count, out_of_stock_count, expired_count],
            'colors': ['#2ecc71', '#f39c12', '#e74c3c', '#2c3e50']
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@login_required
def category_distribution_data(request):
    try:
        org = get_user_organization(request)

        categories = Category.objects.annotate(
            medicine_count=Count(
                'medicine',
                filter=Q(medicine__organization=org)
            )
        )

        labels = [cat.name for cat in categories]
        data = [cat.medicine_count for cat in categories]

        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
        if len(labels) > len(colors):
            colors = colors * (len(labels) // len(colors) + 1)

        return JsonResponse({
            'labels': labels,
            'data': data,
            'colors': colors[:len(labels)]
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@login_required
def top_medicines_data(request):
    try:
        org = get_user_organization(request)

        top_medicines = Medicine.objects.filter(
            organization=org
        ).order_by('-quantity')[:5]

        labels = [med.name for med in top_medicines]
        data = [med.quantity for med in top_medicines]

        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']

        return JsonResponse({
            'labels': labels,
            'data': data,
            'colors': colors[:len(labels)]
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dashboard_stats_data(request):
    """API endpoint for all dashboard stats"""
    try:
        current_time = timezone.now()
        org = get_user_organization(request)  # 🔐 Tenant

        total_medicines = Medicine.objects.filter(
            organization=org
        ).count()

        low_stock_count = Medicine.objects.filter(
            organization=org,
            quantity__lte=10
        ).count()

        expired_count = Medicine.objects.filter(
            organization=org,
            expiry_date__lt=current_time.date()
        ).count()

        out_of_stock_count = Medicine.objects.filter(
            organization=org,
            quantity=0
        ).count()

        total_revenue = Order.objects.filter(
            organization=org,
            is_completed=True
        ).aggregate(
            total=Sum('final_amount')
        )['total'] or 0

        total_orders = Order.objects.filter(
            organization=org,
            is_completed=True
        ).count()

        return JsonResponse({
            'total_medicines': total_medicines,
            'low_stock_count': low_stock_count,
            'expired_count': expired_count,
            'out_of_stock_count': out_of_stock_count,
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'last_updated': current_time.strftime('%b %d, %Y %H:%M:%S')
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from .pdf_utils import generate_simple_invoice
from django.http import JsonResponse, HttpResponse
@login_required
def generate_invoice_pdf(request, order_id):
    org = get_user_organization(request)

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        organization=org
    )

    try:
        pdf_content = generate_simple_invoice(order)

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('order_success', order_id=order_id)

@login_required
@login_required
def sales_report(request):
    org = get_user_organization(request)  # 🔐 Tenant

    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=30)

    # 📊 Sales Data
    daily_sales = Order.objects.filter(
        organization=org,
        is_completed=True,
        order_date__range=[start_date, end_date]
    ).extra({'date': "date(order_date)"}).values('date').annotate(
        total_sales=Sum('final_amount'),
        order_count=Count('id')
    ).order_by('date')

    # 💊 Top Selling Medicines
    top_medicines = OrderItem.objects.filter(
        order__organization=org,
        order__is_completed=True,
        order__order_date__range=[start_date, end_date]
    ).values('medicine__name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_sold')[:10]

    context = {
        'daily_sales': daily_sales,
        'top_medicines': top_medicines,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'sales_report.html', context)

from organizations.models import Organization
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

@user_passes_test(lambda u: u.is_superuser)
def switch_organization(request, org_id):
    org = Organization.objects.filter(id=org_id).first()
    if org:
        request.session["selected_org_id"] = org.id
    return redirect(request.META.get("HTTP_REFERER", "/"))
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from weasyprint import HTML
from .models import Order


def generate_invoice(request, order_id):
    org = get_user_organization(request)

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        organization=org
    )

    items = order.items.all()

    for item in items:
        item.line_total = item.quantity * item.price

    html_string = render_to_string("invoice.html", {
        "order": order,
        "items": items,
        "pdf": True
    })

    pdf = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.id}.pdf"'

    return response


def invoice_preview(request, order_id):
    org = get_user_organization(request)

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        organization=org
    )

    items = order.items.all()

    for item in items:
        item.line_total = item.quantity * item.price

    return render(request, "invoice.html", {
        "order": order,
        "items": items,
        "pdf": False
    })
from django.shortcuts import render
from .models import Medicine, UserProfile


@login_required
@org_staff_required
def network_medicine_search(request):

    query = request.GET.get("q")
    results = []

    if query:

        current_org = request.user.userprofile.organization

        medicines = Medicine.objects.filter(
            name__icontains=query,
            quantity__gt=0,
            organization__allow_inventory_sharing=True
        ).exclude(
            organization=current_org
        )

        for med in medicines:

            contact = UserProfile.objects.filter(
                organization=med.organization
            ).exclude(phone="").first()

            results.append({
                "medicine": med.name,
                "pharmacy": med.organization.name,
                "address": med.organization.address,
                "contact_name": contact.user.username if contact else "N/A",
                "phone": contact.phone if contact else "N/A"
            })

    return render(request, "network_search.html", {"results": results})
from django.db.models import Sum, F
from datetime import datetime

@org_staff_required
def supplier_detail(request, supplier_id):

    org = get_user_organization(request)

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id,
        organization=org
    )

    medicines = Medicine.objects.filter(
        organization=org,
        supplier=supplier
    ).order_by("-created_at")

    # GET filters
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    month = request.GET.get("month")

    if start_date:
        medicines = medicines.filter(
            created_at__date__gte=start_date
        )

    if end_date:
        medicines = medicines.filter(
            created_at__date__lte=end_date
        )

    if month:
        medicines = medicines.filter(
            created_at__month=month
        )

    total_quantity = medicines.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    total_value = medicines.aggregate(
        total=Sum(F("quantity") * F("price"))
    )["total"] or 0

    context = {
        "supplier": supplier,
        "medicines": medicines,
        "total_quantity": total_quantity,
        "total_value": total_value,
        "start_date": start_date,
        "end_date": end_date,
        "month": month
    }

    return render(request, "org_admin/supplier_detail.html", context)
@org_staff_required
def add_supplier_purchase(request, supplier_id):

    org = get_user_organization(request)

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id,
        organization=org
    )

    if request.method == "POST":

        name = request.POST.get("name")
        company = request.POST.get("company_name")
        power = request.POST.get("power")
        quantity = request.POST.get("quantity")
        price = request.POST.get("price")
        expiry = request.POST.get("expiry_date")

        Medicine.objects.create(
            organization=org,
            supplier=supplier,
            name=name,
            company_name=company,
            power=power,
            quantity=quantity,
            price=price,
            expiry_date=expiry
        )

        return redirect("supplier_detail", supplier_id=supplier.id)

    return render(
        request,
        "org_admin/add_supplier_purchase.html",
        {"supplier": supplier}
    )
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta, datetime

@login_required
def download_sales_report(request):
    org = get_user_organization(request)

    # 📅 GET FILTERS
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    months = request.GET.get("months")

    orders = Order.objects.filter(
        organization=org,
        is_completed=True
    )

    # 🔹 OPTION 1: Custom Date Range
    if start_date and end_date:
        orders = orders.filter(
            order_date__date__range=[start_date, end_date]
        )

    # 🔹 OPTION 2: Last X Months
    elif months:
        months = int(months)
        end = timezone.now()
        start = end - timedelta(days=30 * months)

        orders = orders.filter(order_date__range=[start, end])

        start_date = start.date()
        end_date = end.date()

    # 🔹 DEFAULT: Last 30 days
    else:
        end = timezone.now()
        start = end - timedelta(days=30)

        orders = orders.filter(order_date__range=[start, end])

        start_date = start.date()
        end_date = end.date()

    # 💰 TOTAL
    total_revenue = orders.aggregate(total=Sum('final_amount'))['total'] or 0

    # 🧾 HTML
    html = render_to_string("report_pdf.html", {
        "orders": orders,
        "total_revenue": total_revenue,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": timezone.now()
    })

    pdf = HTML(string=html).write_pdf()

    # 📄 FILE NAME BASED ON DATE
    filename = f"{start_date}_to_{end_date}_report.pdf"

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
from django.core import serializers
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def backup_data(request):
    org = get_user_organization(request)

    medicines = Medicine.objects.filter(organization=org)
    orders = Order.objects.filter(organization=org)
    order_items = OrderItem.objects.filter(organization=org)
    categories = Category.objects.filter(organization=org)
    suppliers = Supplier.objects.filter(organization=org)

    # Combine all data
    all_data = (
        list(medicines) +
        list(orders) +
        list(order_items) +
        list(categories) +
        list(suppliers)
    )

    data = serializers.serialize('json', all_data)

    response = HttpResponse(data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="full_backup.json"'
    return response
from django.core import serializers
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import RestoreLog, Medicine, Order, OrderItem, Category, Supplier
from .utils import get_user_organization


@login_required
def restore_backup(request):
    org = get_user_organization(request)

    # 📊 Get last 10 logs for UI table
    restore_logs = RestoreLog.objects.filter(
        organization=org
    ).order_by('-created_at')[:10]

    if request.method == 'POST':
        file = request.FILES.get('backup_file')

        if not file:
            messages.error(request, "No file uploaded")
            return redirect('restore_backup')

        try:
            data = file.read().decode('utf-8')
            objects = serializers.deserialize('json', data)

            # 🔒 SAFE TRANSACTION
            with transaction.atomic():

                # 🧹 DELETE OLD DATA
                Medicine.objects.filter(organization=org).delete()
                Order.objects.filter(organization=org).delete()
                OrderItem.objects.filter(organization=org).delete()
                Category.objects.filter(organization=org).delete()
                Supplier.objects.filter(organization=org).delete()

                # 📥 RESTORE DATA
                for obj in objects:
                    obj.save()

            # ✅ SUCCESS LOG
            RestoreLog.objects.create(
                organization=org,
                user=request.user,
                file_name=file.name,
                status='success',
                message='Backup restored successfully'
            )

            messages.success(request, "✅ Backup restored successfully!")

        except Exception as e:

            # ❌ FAILURE LOG
            RestoreLog.objects.create(
                organization=org,
                user=request.user,
                file_name=file.name if file else '',
                status='failed',
                message=str(e)
            )

            messages.error(request, f"❌ Restore failed: {str(e)}")

        return redirect('restore_backup')

    return render(request, 'restore_backup.html', {
        'restore_logs': restore_logs
    })
@login_required
def report_page(request):
    return render(request, "report_filter.html")
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Count
from django.db.models import F
from django.utils.timezone import now
from datetime import timedelta
import json


@login_required
@require_POST
def ai_assistant(request):

    try:

        org = get_user_organization(request)

        # =====================================================
        # ORGANIZATION VALIDATION
        # =====================================================

        if not org:

            return JsonResponse({

                "reply": (
                    "🚫 ORGANIZATION ERROR\n\n"
                    "No organization is linked to your account."
                ),

                "access_denied": True

            }, status=403)


        # =====================================================
        # FEATURE ACCESS CONTROL
        # =====================================================

        if not org.ai_assistant_enabled:

            return JsonResponse({

                "reply": (
                    "🚫 ACCESS RESTRICTED\n\n"

                    "Your organization does not currently "
                    "have access to the AI Assistant feature.\n\n"

                    "Please contact the administrator "
                    "to enable premium AI features."
                ),

                "access_denied": True

            }, status=403)


        # =====================================================
        # REQUEST DATA
        # =====================================================

        data = json.loads(request.body)

        message = data.get("message", "").lower().strip()


        # =====================================================
        # LOW STOCK
        # =====================================================

        if any(keyword in message for keyword in [

            "low stock",
            "stock issue",
            "stock alert",
            "less stock"

        ]):

            medicines = Medicine.objects.filter(
                organization=org,
                quantity__lte=10
            )


            if medicines.exists():

                return JsonResponse({

                    "reply": (
                        "⚠ LOW STOCK ALERT\n\n"

                        "Medicines:\n• "

                        + "\n• ".join(
                            [m.name for m in medicines[:5]]
                        )

                        + f"\n\nTotal affected medicines: "
                          f"{medicines.count()}\n\n"

                        "Recommendation:\n"
                        "• Restock medicines soon\n"
                        "• Monitor fast-moving inventory"
                    )

                })


            return JsonResponse({

                "reply": (
                    "✅ INVENTORY STATUS\n\n"
                    "No low stock medicines found."
                )

            })


        # =====================================================
        # EXPIRED MEDICINES
        # =====================================================

        elif any(keyword in message for keyword in [

            "expired",
            "expiry",
            "expired medicines",
            "expired meds"

        ]):

            medicines = Medicine.objects.filter(
                organization=org,
                expiry_date__lt=timezone.now().date()
            )


            if medicines.exists():

                return JsonResponse({

                    "reply": (
                        "❌ EXPIRED MEDICINES\n\n"

                        "Medicines:\n• "

                        + "\n• ".join(
                            [m.name for m in medicines[:5]]
                        )

                        + f"\n\nTotal expired medicines: "
                          f"{medicines.count()}\n\n"

                        "Recommendation:\n"
                        "• Remove expired stock\n"
                        "• Verify inventory batches"
                    )

                })


            return JsonResponse({

                "reply": (
                    "✅ EXPIRY STATUS\n\n"
                    "No expired medicines found."
                )

            })


        # =====================================================
        # REVENUE ANALYTICS
        # =====================================================

        elif any(keyword in message for keyword in [

            "revenue",
            "sales",
            "income",
            "earnings"

        ]):

            revenue = Order.objects.filter(
                organization=org,
                is_completed=True
            ).aggregate(
                total=Sum("final_amount")
            )["total"] or 0


            total_orders = Order.objects.filter(
                organization=org,
                is_completed=True
            ).count()


            return JsonResponse({

                "reply": (
                    "💰 REVENUE ANALYTICS\n\n"

                    f"Total Revenue: ₹{revenue}\n"

                    f"Completed Orders: {total_orders}\n\n"

                    "Business Status:\n"
                    "• Sales tracking active\n"
                    "• Revenue analytics operational"
                )

            })


        # =====================================================
        # INVENTORY INSIGHTS
        # =====================================================

        elif any(keyword in message for keyword in [

            "inventory insights",
            "inventory summary",
            "summary",
            "insights",
            "attention",
            "inventory"

        ]):

            low_stock = Medicine.objects.filter(
                organization=org,
                quantity__lte=10
            ).count()

            expired = Medicine.objects.filter(
                organization=org,
                expiry_date__lt=timezone.now().date()
            ).count()

            total_products = Medicine.objects.filter(
                organization=org
            ).count()


            return JsonResponse({

                "reply": (
                    "📊 INVENTORY INSIGHTS\n\n"

                    f"📦 Total Medicines: "
                    f"{total_products}\n"

                    f"⚠ Low Stock Medicines: "
                    f"{low_stock}\n"

                    f"❌ Expired Medicines: "
                    f"{expired}\n\n"

                    "Recommendations:\n"

                    "• Review low stock inventory\n"
                    "• Remove expired medicines\n"
                    "• Monitor inventory regularly\n"
                    "• Maintain supplier coordination"
                )

            })


        # =====================================================
        # ORDER ANALYTICS
        # =====================================================

        elif any(keyword in message for keyword in [

            "orders",
            "completed orders",
            "sales orders"

        ]):

            total_orders = Order.objects.filter(
                organization=org,
                is_completed=True
            ).count()


            return JsonResponse({

                "reply": (
                    "📦 ORDER ANALYTICS\n\n"

                    f"Completed Orders: "
                    f"{total_orders}\n\n"

                    "Order System Status:\n"
                    "• Order tracking active\n"
                    "• Sales workflow operational"
                )

            })

        # =====================================================
        # TOP SELLING MEDICINES
        # =====================================================

        elif any(keyword in message for keyword in [

            "top selling",
            "best selling",
            "top medicines",
            "top selling medicines"

        ]):

            top_medicines = (
                OrderItem.objects.filter(
                    order__organization=org
                )
                .values("medicine__name")
                .annotate(
                    total_sold=Sum("quantity")
                )
                .order_by("-total_sold")[:5]
            )

            if top_medicines:

                response = (
                    "🏆 TOP SELLING MEDICINES\n\n"
                )

                for idx, item in enumerate(top_medicines, start=1):

                    response += (
                        f"{idx}. "
                        f"{item['medicine__name']} "
                        f"→ {item['total_sold']} units sold\n"
                    )

                response += (
                    "\nInsights:\n"
                    "• High demand medicines detected\n"
                    "• Maintain sufficient inventory"
                )

                return JsonResponse({
                    "reply": response
                })

            return JsonResponse({
                "reply": "No sales data found."
            })

        # =====================================================
        # MONTHLY SALES ANALYSIS
        # =====================================================

        elif any(keyword in message for keyword in [

            "monthly sales",
            "monthly analysis",
            "sales analysis",
            "monthly report"

        ]):

            start_date = now() - timedelta(days=30)

            monthly_orders = Order.objects.filter(
                organization=org,
                created_at__gte=start_date,
                is_completed=True
            )

            total_revenue = monthly_orders.aggregate(
                total=Sum("final_amount")
            )["total"] or 0

            total_orders = monthly_orders.count()

            total_items = OrderItem.objects.filter(
                order__in=monthly_orders
            ).aggregate(
                total=Sum("quantity")
            )["total"] or 0


            return JsonResponse({

                "reply": (
                    "📊 MONTHLY SALES ANALYSIS\n\n"

                    f"💰 Revenue: ₹{total_revenue}\n"

                    f"📦 Orders: {total_orders}\n"

                    f"💊 Medicines Sold: {total_items}\n\n"

                    "Business Insights:\n"
                    "• Monthly sales analytics active\n"
                    "• Inventory movement monitored"
                )

            })
        
        # =====================================================
        # ORDER DETAILS
        # =====================================================

        elif "order" in message and any(
            char.isdigit() for char in message
        ):

            order_number = ''.join(
                filter(str.isdigit, message)
            )

            order = Order.objects.filter(
                organization=org,
                id=order_number
            ).first()

            if not order:

                return JsonResponse({
                    "reply": (
                        "❌ ORDER NOT FOUND\n\n"
                        f"No order found with ID #{order_number}"
                    )
                })

            items = OrderItem.objects.filter(
                order=order
            )

            response = (
                "📦 ORDER DETAILS\n\n"

                f"Order ID: #{order.id}\n"

                f"Total Amount: ₹{order.final_amount}\n"

                f"Status: "
                f"{'Completed' if order.is_completed else 'Pending'}\n\n"

                "Medicines:\n"
            )

            for item in items:

                response += (
                    f"• {item.medicine.name} "
                    f"× {item.quantity}\n"
                )

            return JsonResponse({
                "reply": response
            })
        
        # =====================================================
        # STOCK DISTRIBUTION
        # =====================================================

        elif any(keyword in message for keyword in [

            "stock distribution",
            "stock analysis",
            "inventory distribution"

        ]):

            high_stock = Medicine.objects.filter(
                organization=org,
                quantity__gt=50
            ).count()

            medium_stock = Medicine.objects.filter(
                organization=org,
                quantity__gt=10,
                quantity__lte=50
            ).count()

            low_stock = Medicine.objects.filter(
                organization=org,
                quantity__lte=10
            ).count()

            out_of_stock = Medicine.objects.filter(
                organization=org,
                quantity=0
            ).count()


            return JsonResponse({

                "reply": (
                    "📦 STOCK DISTRIBUTION\n\n"

                    f"🟢 High Stock: {high_stock}\n"

                    f"🟡 Medium Stock: {medium_stock}\n"

                    f"⚠ Low Stock: {low_stock}\n"

                    f"🔴 Out of Stock: {out_of_stock}\n\n"

                    "Insights:\n"
                    "• Inventory distribution analyzed\n"
                    "• Restock low inventory items"
                )

            })
        
        # =====================================================
        # FAST MOVING INVENTORY
        # =====================================================

        elif any(keyword in message for keyword in [

            "fast moving",
            "fast selling",
            "moving inventory"

        ]):

            fast_items = (
                OrderItem.objects.filter(
                    order__organization=org
                )
                .values("medicine__name")
                .annotate(
                    total_sold=Sum("quantity")
                )
                .order_by("-total_sold")[:5]
            )

            response = (
                "🚀 FAST MOVING INVENTORY\n\n"
            )

            for idx, item in enumerate(fast_items, start=1):

                response += (
                    f"{idx}. "
                    f"{item['medicine__name']} "
                    f"→ {item['total_sold']} sold\n"
                )

            response += (
                "\nRecommendations:\n"
                "• Increase stock availability\n"
                "• Coordinate with suppliers"
            )

            return JsonResponse({
                "reply": response
            })
        # =====================================================
        # SLOW MOVING INVENTORY
        # =====================================================

        elif any(keyword in message for keyword in [

            "slow moving",
            "slow selling",
            "less selling"

        ]):

            slow_items = (
                OrderItem.objects.filter(
                    order__organization=org
                )
                .values("medicine__name")
                .annotate(
                    total_sold=Sum("quantity")
                )
                .order_by("total_sold")[:5]
            )

            response = (
                "🐢 SLOW MOVING INVENTORY\n\n"
            )

            for idx, item in enumerate(slow_items, start=1):

                response += (
                    f"{idx}. "
                    f"{item['medicine__name']} "
                    f"→ {item['total_sold']} sold\n"
                )

            response += (
                "\nRecommendations:\n"
                "• Consider promotional offers\n"
                "• Reduce overstock inventory"
            )

            return JsonResponse({
                "reply": response
            })
        

        # =====================================================
        # DEFAULT RESPONSE
        # =====================================================

        return JsonResponse({

            "reply": (

                "🤖 AI PHARMACY INTELLIGENCE ASSISTANT\n\n"

                "I can help you with:\n\n"

                "📦 Inventory Management\n"
                "• Low stock medicines\n"
                "• Expired medicines\n"
                "• Stock distribution\n"
                "• Inventory insights\n\n"

                "💰 Business Analytics\n"
                "• Revenue analytics\n"
                "• Monthly sales analysis\n"
                "• Order analytics\n"
                "• Top selling medicines\n\n"

                "🚀 Inventory Intelligence\n"
                "• Fast moving inventory\n"
                "• Slow moving inventory\n"
                "• Best selling medicines\n\n"

                "📋 Order Management\n"
                "• Order details by order number\n\n"

                "Example Questions:\n\n"

                "• Show low stock medicines\n"
                "• Give inventory insights\n"
                "• Show revenue analytics\n"
                "• Top selling medicines\n"
                "• Monthly sales analysis\n"
                "• Stock distribution\n"
                "• Fast moving inventory\n"
                "• Show order 1023"
            )

        })


    except Exception as e:

        return JsonResponse({

            "reply": (
                "⚠ SYSTEM ERROR\n\n"
                f"{str(e)}"
            )

        }, status=500)