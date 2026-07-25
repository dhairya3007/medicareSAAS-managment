from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from organizations.models import Organization
from store.models import UserProfile, Medicine, Order, OrderItem
from decimal import Decimal

@override_settings(SECURE_SSL_REDIRECT=False)
class PaymentIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testpharmacist', password='testpassword123')
        self.org = Organization.objects.create(name='Test Pharmacy Org', is_active=True)

        # Create UserProfile
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.org,
            role='pharmacist'
        )

        # Log the user in
        self.client.login(username='testpharmacist', password='testpassword123')

        # Create a test medicine
        self.medicine = Medicine.objects.create(
            organization=self.org,
            name='Paracetamol 500mg',
            product_number='PARA123',
            quantity=100,
            company_name='Test Pharma',
            power='500mg',
            price=Decimal('10.00'),
            low_stock_threshold=10
        )

    def test_checkout_cash_payment_flow(self):
        # 1. Add medicine to cart
        add_cart_url = reverse('add_to_cart', args=[self.medicine.id])
        response = self.client.post(add_cart_url)
        self.assertRedirects(response, reverse('cart_view'))

        # 2. Check checkout view renders correct details
        checkout_url = reverse('checkout')
        response = self.client.get(checkout_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paracetamol 500mg')

        # 3. Post checkout form with cash payment
        response = self.client.post(checkout_url, {
            'payment_method': 'cash'
        })

        # Verify redirect to order success
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        order = orders.first()
        self.assertRedirects(response, reverse('order_success', args=[order.id]))

        # Verify order attributes
        self.assertEqual(order.payment_method, 'cash')
        self.assertEqual(order.payment_status, 'paid')
        self.assertTrue(order.is_completed)

        # Verify inventory is reduced
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 99)

    def test_checkout_card_payment_flow_success(self):
        # 1. Add medicine to cart
        add_cart_url = reverse('add_to_cart', args=[self.medicine.id])
        self.client.post(add_cart_url)

        # 2. Post checkout form with valid card details
        checkout_url = reverse('checkout')
        response = self.client.post(checkout_url, {
            'payment_method': 'card',
            'card_number': '1234 5678 1234 5678',
            'card_expiry': '12/28',
            'card_cvv': '123'
        })

        # Verify redirect to order success
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        order = orders.first()
        self.assertRedirects(response, reverse('order_success', args=[order.id]))

        # Verify order attributes
        self.assertEqual(order.payment_method, 'card')
        self.assertEqual(order.payment_status, 'paid')

        # Verify inventory is reduced
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 99)

    def test_checkout_card_payment_flow_invalid_card_number(self):
        # 1. Add medicine to cart
        add_cart_url = reverse('add_to_cart', args=[self.medicine.id])
        self.client.post(add_cart_url)

        # 2. Post checkout form with invalid card details (too short card number)
        checkout_url = reverse('checkout')
        response = self.client.post(checkout_url, {
            'payment_method': 'card',
            'card_number': '1234 5678',
            'card_expiry': '12/28',
            'card_cvv': '123'
        })

        # Verify redirect back to checkout
        self.assertRedirects(response, reverse('checkout'))

        # Verify no order is created
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 0)

        # Verify inventory remains unchanged
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 100)

    def test_checkout_card_payment_flow_invalid_cvv(self):
        # 1. Add medicine to cart
        add_cart_url = reverse('add_to_cart', args=[self.medicine.id])
        self.client.post(add_cart_url)

        # 2. Post checkout form with invalid card details (4 digit CVV)
        checkout_url = reverse('checkout')
        response = self.client.post(checkout_url, {
            'payment_method': 'card',
            'card_number': '1234 5678 1234 5678',
            'card_expiry': '12/28',
            'card_cvv': '1234'
        })

        # Verify redirect back to checkout
        self.assertRedirects(response, reverse('checkout'))

        # Verify no order is created
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 0)

        # Verify inventory remains unchanged
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 100)
