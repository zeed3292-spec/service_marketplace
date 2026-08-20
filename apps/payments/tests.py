from django.test import TestCase, override_settings
from django.urls import reverse
from apps.accounts.models import User
from apps.marketplace.models import Category, Service
from apps.orders.models import Order
from .models import Payment, CommissionRecord

class PaymentWorkflowTests(TestCase):
    def setUp(self):
        self.customer=User.objects.create_user(username='cust', email='cust@example.com', password='x', role='customer')
        self.provider=User.objects.create_user(username='prov', email='prov@example.com', password='x', role='provider')
        cat=Category.objects.create(name='Dev')
        self.service=Service.objects.create(provider=self.provider, category=cat, title='Web', description='Build', price=100, delivery_time=3, status='active')
        self.order=Order.objects.create(customer=self.customer, provider=self.provider, service=self.service, title='Web', description='Need', agreed_price=100, delivery_days=3, status=Order.STATUS_PAYMENT_PENDING)
    def test_create_payment_keeps_order_unpaid(self):
        self.client.force_login(self.customer)
        response=self.client.post(reverse('payments:payment_create', args=[self.order.order_number]))
        self.assertEqual(response.status_code, 302)
        payment=Payment.objects.get(order=self.order)
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        self.assertEqual(self.order.payment_status, 'pending')
        self.assertEqual(self.order.status, Order.STATUS_PAYMENT_PENDING)
    @override_settings(DEBUG=True)
    def test_debug_success_updates_payment_order_and_commission(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('payments:payment_create', args=[self.order.order_number]))
        payment=Payment.objects.get(order=self.order)
        response=self.client.post(reverse('payments:payment_test_success', args=[payment.pk]))
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(self.order.payment_status, 'paid')
        self.assertTrue(CommissionRecord.objects.filter(order=self.order).exists())
    @override_settings(DEBUG=True)
    def test_debug_failure_does_not_mark_order_paid(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('payments:payment_create', args=[self.order.order_number]))
        payment=Payment.objects.get(order=self.order)
        self.client.post(reverse('payments:payment_test_fail', args=[payment.pk]))
        payment.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_FAILED)
        self.assertNotEqual(self.order.status, Order.STATUS_PAID)
