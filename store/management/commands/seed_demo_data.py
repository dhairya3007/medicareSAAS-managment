"""
Management command to seed realistic demo data for MediCare SaaS deployment.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset  # Clears existing demo data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
import random

from organizations.models import Organization
from store.models import (
    UserProfile, Category, Supplier,
    Medicine, Order, OrderItem
)


# ─────────────────────────────────────────────
#  Static demo fixtures
# ─────────────────────────────────────────────

DEMO_ORGS = [
    {
        "name": "MediCare Pharmacy",
        "address": "12, Health Street, Mumbai, Maharashtra 400001",
        "admin_username": "demo_admin",
        "admin_email": "demo@medicare.com",
        "admin_password": "Demo@1234",
        "ai_assistant_enabled": True,
        "dashboard_ai_enabled": True,
    },
    {
        "name": "City Life Chemist",
        "address": "45, Gandhi Road, Pune, Maharashtra 411001",
        "admin_username": "citylife_admin",
        "admin_email": "admin@citylife.com",
        "admin_password": "Demo@1234",
        "ai_assistant_enabled": False,
        "dashboard_ai_enabled": False,
    },
]

CATEGORIES = [
    ("Antibiotics", "Medicines that fight bacterial infections"),
    ("Pain Relief", "Analgesics and anti-inflammatory drugs"),
    ("Vitamins & Supplements", "Nutritional supplements and vitamins"),
    ("Cardiac Care", "Heart and blood pressure medications"),
    ("Diabetes Care", "Insulin and anti-diabetic medicines"),
    ("Gastrology", "Antacids and digestive medicines"),
    ("Dermatology", "Skin care and topical medicines"),
    ("Respiratory", "Cough, cold, and asthma medicines"),
    ("Neurology", "Medicines for nervous system disorders"),
    ("Pediatrics", "Medicines for children"),
]

SUPPLIERS = [
    {
        "name": "Sun Pharma Distributors",
        "contact_person": "Rajesh Sharma",
        "phone": "+91-9876543210",
        "email": "rajesh@sunpharma.com",
        "address": "Andheri East, Mumbai, MH 400069",
    },
    {
        "name": "Cipla Wholesale",
        "contact_person": "Priya Mehta",
        "phone": "+91-9123456780",
        "email": "priya@cipla.com",
        "address": "Vikhroli, Mumbai, MH 400083",
    },
    {
        "name": "Abbott Healthcare Supply",
        "contact_person": "Arjun Patel",
        "phone": "+91-9988776655",
        "email": "arjun@abbott.com",
        "address": "Anand, Gujarat 388001",
    },
    {
        "name": "Mankind Pharma Depot",
        "contact_person": "Sneha Rao",
        "phone": "+91-9871234560",
        "email": "sneha@mankind.com",
        "address": "Pitampura, New Delhi 110034",
    },
    {
        "name": "Himalaya Drug Co.",
        "contact_person": "Vikram Nair",
        "phone": "+91-9654321087",
        "email": "vikram@himalaya.com",
        "address": "Bangalore, Karnataka 560080",
    },
]

# Tuple: (name, components, product_number, company_name, power,
#          quantity, price, cat_name, sup_name, batch, expiry_days)
MEDICINES_DATA = [
    # Antibiotics
    ("Amoxicillin 500mg", "Amoxicillin", "MED-001", "GlaxoSmithKline", "500mg",
     150, Decimal("45.00"), "Antibiotics", "Sun Pharma Distributors", "BATCH-A001", 180),
    ("Azithromycin 250mg", "Azithromycin", "MED-002", "Cipla Ltd", "250mg",
     80, Decimal("120.00"), "Antibiotics", "Cipla Wholesale", "BATCH-A002", 365),
    ("Ciprofloxacin 500mg", "Ciprofloxacin", "MED-003", "Lupin Pharma", "500mg",
     120, Decimal("35.00"), "Antibiotics", "Sun Pharma Distributors", "BATCH-A003", 270),
    ("Doxycycline 100mg", "Doxycycline", "MED-004", "Abbott India", "100mg",
     60, Decimal("55.00"), "Antibiotics", "Abbott Healthcare Supply", "BATCH-A004", 300),
    # Pain Relief
    ("Paracetamol 500mg", "Paracetamol", "MED-005", "Cipla Ltd", "500mg",
     500, Decimal("12.00"), "Pain Relief", "Cipla Wholesale", "BATCH-P001", 365),
    ("Ibuprofen 400mg", "Ibuprofen", "MED-006", "Sun Pharma", "400mg",
     300, Decimal("18.50"), "Pain Relief", "Sun Pharma Distributors", "BATCH-P002", 400),
    ("Diclofenac 50mg", "Diclofenac Sodium", "MED-007", "Novartis India", "50mg",
     200, Decimal("22.00"), "Pain Relief", "Mankind Pharma Depot", "BATCH-P003", 365),
    ("Tramadol 50mg", "Tramadol HCl", "MED-008", "Sun Pharma", "50mg",
     5, Decimal("75.00"), "Pain Relief", "Sun Pharma Distributors", "BATCH-P004", 365),  # Low stock
    # Vitamins
    ("Vitamin C 1000mg", "Ascorbic Acid", "MED-009", "Himalaya", "1000mg",
     250, Decimal("180.00"), "Vitamins & Supplements", "Himalaya Drug Co.", "BATCH-V001", 730),
    ("Vitamin D3 60K IU", "Cholecalciferol", "MED-010", "Abbott India", "60000 IU",
     100, Decimal("210.00"), "Vitamins & Supplements", "Abbott Healthcare Supply", "BATCH-V002", 365),
    ("Multivitamin Tablet", "Multi Vitamins & Minerals", "MED-011", "Cipla Ltd", "One-a-Day",
     180, Decimal("350.00"), "Vitamins & Supplements", "Cipla Wholesale", "BATCH-V003", 730),
    ("Zinc 50mg", "Zinc Sulphate", "MED-012", "Mankind Pharma", "50mg",
     8, Decimal("95.00"), "Vitamins & Supplements", "Mankind Pharma Depot", "BATCH-V004", 365),  # Low stock
    # Cardiac Care
    ("Atorvastatin 10mg", "Atorvastatin Calcium", "MED-013", "Pfizer India", "10mg",
     200, Decimal("85.00"), "Cardiac Care", "Sun Pharma Distributors", "BATCH-C001", 365),
    ("Amlodipine 5mg", "Amlodipine Besylate", "MED-014", "Sun Pharma", "5mg",
     150, Decimal("60.00"), "Cardiac Care", "Sun Pharma Distributors", "BATCH-C002", 365),
    ("Metoprolol 50mg", "Metoprolol Tartrate", "MED-015", "AstraZeneca India", "50mg",
     120, Decimal("110.00"), "Cardiac Care", "Mankind Pharma Depot", "BATCH-C003", 365),
    ("Aspirin 75mg", "Acetylsalicylic Acid", "MED-016", "Bayer India", "75mg",
     6, Decimal("28.00"), "Cardiac Care", "Abbott Healthcare Supply", "BATCH-C004", 365),  # Low stock
    # Diabetes Care
    ("Metformin 500mg", "Metformin HCl", "MED-017", "Sun Pharma", "500mg",
     300, Decimal("42.00"), "Diabetes Care", "Sun Pharma Distributors", "BATCH-D001", 365),
    ("Glibenclamide 5mg", "Glibenclamide", "MED-018", "Cipla Ltd", "5mg",
     100, Decimal("65.00"), "Diabetes Care", "Cipla Wholesale", "BATCH-D002", 365),
    ("Insulin Glargine 100U/mL", "Insulin Glargine rDNA", "MED-019", "Sanofi India", "100 U/mL",
     50, Decimal("750.00"), "Diabetes Care", "Abbott Healthcare Supply", "BATCH-D003", 90),
    # Gastrology
    ("Omeprazole 20mg", "Omeprazole", "MED-020", "AstraZeneca", "20mg",
     400, Decimal("38.00"), "Gastrology", "Cipla Wholesale", "BATCH-G001", 365),
    ("Pantoprazole 40mg", "Pantoprazole Sodium", "MED-021", "Sun Pharma", "40mg",
     250, Decimal("55.00"), "Gastrology", "Sun Pharma Distributors", "BATCH-G002", 365),
    ("Ondansetron 4mg", "Ondansetron HCl", "MED-022", "GSK India", "4mg",
     150, Decimal("45.00"), "Gastrology", "Abbott Healthcare Supply", "BATCH-G003", 300),
    # Dermatology
    ("Clotrimazole Cream 1%", "Clotrimazole", "MED-023", "GSK India", "1%",
     80, Decimal("95.00"), "Dermatology", "Abbott Healthcare Supply", "BATCH-SK001", 365),
    ("Hydrocortisone Cream 1%", "Hydrocortisone", "MED-024", "Cipla Ltd", "1%",
     60, Decimal("115.00"), "Dermatology", "Cipla Wholesale", "BATCH-SK002", 365),
    # Respiratory
    ("Salbutamol Inhaler 100mcg", "Salbutamol Sulphate", "MED-025", "GSK India", "100mcg/dose",
     40, Decimal("280.00"), "Respiratory", "Abbott Healthcare Supply", "BATCH-R001", 365),
    ("Montelukast 10mg", "Montelukast Sodium", "MED-026", "Merck India", "10mg",
     100, Decimal("190.00"), "Respiratory", "Mankind Pharma Depot", "BATCH-R002", 365),
    ("Cetirizine 10mg", "Cetirizine HCl", "MED-027", "UCB India", "10mg",
     200, Decimal("25.00"), "Respiratory", "Cipla Wholesale", "BATCH-R003", 365),
    # Neurology
    ("Gabapentin 300mg", "Gabapentin", "MED-028", "Pfizer India", "300mg",
     70, Decimal("165.00"), "Neurology", "Sun Pharma Distributors", "BATCH-N001", 365),
    ("Alprazolam 0.5mg", "Alprazolam", "MED-029", "Sun Pharma", "0.5mg",
     3, Decimal("85.00"), "Neurology", "Sun Pharma Distributors", "BATCH-N002", 365),  # Low stock
    # Pediatrics
    ("Paracetamol Syrup 120mg/5mL", "Paracetamol", "MED-030", "Cipla Ltd", "120mg/5mL",
     90, Decimal("55.00"), "Pediatrics", "Cipla Wholesale", "BATCH-PD001", 365),
    ("Amoxicillin Dry Syrup 125mg/5mL", "Amoxicillin Trihydrate", "MED-031", "Ranbaxy", "125mg/5mL",
     75, Decimal("72.00"), "Pediatrics", "Sun Pharma Distributors", "BATCH-PD002", 180),
    ("ORS Sachet", "Sodium Chloride, Potassium Chloride", "MED-032", "Mankind Pharma", "WHO Formula",
     200, Decimal("15.00"), "Pediatrics", "Mankind Pharma Depot", "BATCH-PD003", 730),
]

STAFF_USERS = [
    {
        "username": "pharmacist_ravi",
        "email": "ravi@medicare.com",
        "password": "Demo@1234",
        "role": "pharmacist",
        "first_name": "Ravi",
        "last_name": "Kumar",
    },
    {
        "username": "pharmacist_anita",
        "email": "anita@medicare.com",
        "password": "Demo@1234",
        "role": "pharmacist",
        "first_name": "Anita",
        "last_name": "Singh",
    },
    {
        "username": "staff_rohit",
        "email": "rohit@medicare.com",
        "password": "Demo@1234",
        "role": "staff",
        "first_name": "Rohit",
        "last_name": "Verma",
    },
]

CUSTOMER_USERS = [
    {"username": "customer_meera", "email": "meera@gmail.com", "password": "Demo@1234", "first_name": "Meera", "last_name": "Patel"},
    {"username": "customer_suresh", "email": "suresh@gmail.com", "password": "Demo@1234", "first_name": "Suresh", "last_name": "Nair"},
    {"username": "customer_kavya", "email": "kavya@gmail.com", "password": "Demo@1234", "first_name": "Kavya", "last_name": "Reddy"},
    {"username": "customer_mohan", "email": "mohan@gmail.com", "password": "Demo@1234", "first_name": "Mohan", "last_name": "Das"},
    {"username": "customer_preethi", "email": "preethi@gmail.com", "password": "Demo@1234", "first_name": "Preethi", "last_name": "Iyer"},
]


class Command(BaseCommand):
    help = "Seeds realistic demo data for MediCare SaaS deployment preview"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing demo data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo_data()

        self.stdout.write(self.style.MIGRATE_HEADING("\nSeeding MediCare SaaS demo data...\n"))

        with transaction.atomic():
            org_objects = self._create_organizations()
            primary_org = org_objects[0]

            category_map = self._create_categories(primary_org)
            supplier_map = self._create_suppliers(primary_org)
            medicine_map = self._create_medicines(primary_org, category_map, supplier_map)
            self._create_staff_users(primary_org)
            customer_users = self._create_customer_users(primary_org)
            self._create_orders(primary_org, customer_users, medicine_map)

        self._print_summary()

    # ──────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────

    def _reset_demo_data(self):
        self.stdout.write(self.style.WARNING("Resetting existing demo data..."))
        demo_usernames = (
            [o["admin_username"] for o in DEMO_ORGS]
            + [u["username"] for u in STAFF_USERS]
            + [u["username"] for u in CUSTOMER_USERS]
        )
        User.objects.filter(username__in=demo_usernames).delete()
        Organization.objects.filter(name__in=[o["name"] for o in DEMO_ORGS]).delete()
        self.stdout.write(self.style.SUCCESS("Reset complete.\n"))

    def _get_or_create_user(self, username, email, password, first_name="", last_name="", is_staff=False):
        if User.objects.filter(username=username).exists():
            return User.objects.get(username=username), False
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
        )
        return user, True

    def _create_organizations(self):
        created_orgs = []
        for org_data in DEMO_ORGS:
            owner, created = self._get_or_create_user(
                username=org_data["admin_username"],
                email=org_data["admin_email"],
                password=org_data["admin_password"],
                first_name="Demo",
                last_name="Admin",
                is_staff=True,
            )
            status = "created" if created else "already exists"
            self.stdout.write(f"  User '{org_data['admin_username']}' - {status}")

            org, org_created = Organization.objects.get_or_create(
                name=org_data["name"],
                defaults={
                    "owner": owner,
                    "address": org_data["address"],
                    "status": "active",
                    "is_active": True,
                    "ai_assistant_enabled": org_data["ai_assistant_enabled"],
                    "dashboard_ai_enabled": org_data["dashboard_ai_enabled"],
                },
            )
            org_status = "created" if org_created else "already exists"
            self.stdout.write(f"  Organization '{org.name}' - {org_status}")

            profile, _ = UserProfile.objects.get_or_create(user=owner)
            profile.organization = org
            profile.role = "org_admin"
            profile.phone = "+91-9000000001"
            profile.save()

            created_orgs.append(org)

        self.stdout.write(self.style.SUCCESS(f"\n{len(created_orgs)} organization(s) ready.\n"))
        return created_orgs

    def _create_categories(self, org):
        category_map = {}
        for name, description in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                organization=org,
                name=name,
                defaults={"description": description},
            )
            category_map[name] = cat
        self.stdout.write(self.style.SUCCESS(f"{len(CATEGORIES)} categories seeded.\n"))
        return category_map

    def _create_suppliers(self, org):
        supplier_map = {}
        for s in SUPPLIERS:
            supplier, _ = Supplier.objects.get_or_create(
                organization=org,
                name=s["name"],
                defaults={
                    "contact_person": s["contact_person"],
                    "phone": s["phone"],
                    "email": s["email"],
                    "address": s["address"],
                },
            )
            supplier_map[s["name"]] = supplier
        self.stdout.write(self.style.SUCCESS(f"{len(SUPPLIERS)} suppliers seeded.\n"))
        return supplier_map

    def _create_medicines(self, org, category_map, supplier_map):
        medicine_map = {}
        today = date.today()
        count = 0

        for (
            name, components, product_number, company_name, power,
            quantity, price, cat_name, sup_name, batch, expiry_days
        ) in MEDICINES_DATA:
            expiry = today + timedelta(days=expiry_days)
            cat = category_map.get(cat_name)
            sup = supplier_map.get(sup_name)

            med, created = Medicine.objects.get_or_create(
                organization=org,
                product_number=product_number,
                defaults={
                    "name": name,
                    "components": components,
                    "company_name": company_name,
                    "power": power,
                    "quantity": quantity,
                    "price": price,
                    "category": cat,
                    "supplier": sup,
                    "batch_number": batch,
                    "expiry_date": expiry,
                    "low_stock_threshold": 10,
                },
            )
            medicine_map[product_number] = med
            if created:
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{count} new medicines seeded (total {len(MEDICINES_DATA)} defined).\n")
        )
        return medicine_map

    def _create_staff_users(self, org):
        for u in STAFF_USERS:
            user, _ = self._get_or_create_user(
                username=u["username"],
                email=u["email"],
                password=u["password"],
                first_name=u["first_name"],
                last_name=u["last_name"],
                is_staff=(u["role"] in ["pharmacist", "staff"]),
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.organization = org
            profile.role = u["role"]
            profile.save()
        self.stdout.write(self.style.SUCCESS(f"{len(STAFF_USERS)} staff/pharmacist users seeded.\n"))

    def _create_customer_users(self, org):
        customer_user_objs = []
        for u in CUSTOMER_USERS:
            user, _ = self._get_or_create_user(
                username=u["username"],
                email=u["email"],
                password=u["password"],
                first_name=u["first_name"],
                last_name=u["last_name"],
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.organization = org
            profile.role = "customer"
            profile.loyalty_points = random.randint(50, 500)
            profile.save()
            customer_user_objs.append(user)
        self.stdout.write(self.style.SUCCESS(f"{len(CUSTOMER_USERS)} customer users seeded.\n"))
        return customer_user_objs

    def _create_orders(self, org, customers, medicine_map):
        """Create 30 realistic past orders spread over the last 90 days."""
        medicine_list = list(medicine_map.values())
        today = timezone.now()
        orders_created = 0

        for _ in range(30):
            customer = random.choice(customers)
            days_ago = random.randint(1, 90)
            order_date = today - timedelta(days=days_ago)

            chosen_meds = random.sample(medicine_list, k=random.randint(1, 4))
            total = Decimal("0.00")
            items_to_create = []

            for med in chosen_meds:
                qty = random.randint(1, 5)
                total += med.price * qty
                items_to_create.append((med, qty, med.price))

            discount = Decimal(str(random.choice([0, 0, 0, 5, 10, 15])))
            final = total * (1 - discount / 100)

            order = Order.objects.create(
                organization=org,
                user=customer,
                total_amount=total.quantize(Decimal("0.01")),
                discount_percentage=discount,
                final_amount=final.quantize(Decimal("0.01")),
                is_completed=True,
                order_date=order_date,
            )

            for med, qty, price in items_to_create:
                OrderItem.objects.create(
                    organization=org,
                    order=order,
                    medicine=med,
                    quantity=qty,
                    price=price,
                )

            orders_created += 1

        self.stdout.write(self.style.SUCCESS(f"{orders_created} demo orders seeded.\n"))

    def _print_summary(self):
        separator = "=" * 55
        self.stdout.write(self.style.MIGRATE_HEADING(separator))
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!\n"))
        self.stdout.write(self.style.MIGRATE_HEADING("Demo Login Credentials\n"))
        credentials = [
            ("Superuser / Django Admin", "admin", "admin9898"),
            ("Org Admin (MediCare Pharmacy)", "demo_admin", "Demo@1234"),
            ("Org Admin (City Life Chemist)", "citylife_admin", "Demo@1234"),
            ("Pharmacist", "pharmacist_ravi", "Demo@1234"),
            ("Staff", "staff_rohit", "Demo@1234"),
            ("Customer", "customer_meera", "Demo@1234"),
        ]
        for role, username, password in credentials:
            self.stdout.write(f"  {role}:")
            self.stdout.write(f"    username : {username}")
            self.stdout.write(f"    password : {password}\n")
        self.stdout.write(self.style.MIGRATE_HEADING(separator))
