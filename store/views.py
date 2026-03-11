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
    form = MedicineForm(request.POST, request.FILES)

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

@login_required
def dashboard_view(request):
    current_time = timezone.now()
    org = get_user_organization(request)

    Medicine.objects.filter(organization=org)
    Order.objects.filter(organization=org)


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

    # ✅ CLEAN ORDER FILTERING
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

    recent_orders = Order.objects.filter(
        organization=org,
        is_completed=True
    ).select_related('user').order_by('-order_date')[:5]
    
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