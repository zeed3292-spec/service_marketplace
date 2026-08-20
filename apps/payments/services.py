from abc import ABC, abstractmethod
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.core.models import TermsAndConditions, calculate_commission
from apps.core.services import notify, audit
from .models import Payment, CommissionRecord


class PaymentGateway(ABC):
    name = 'base'

    @abstractmethod
    def create_payment(self, order, amount):
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, payment):
        raise NotImplementedError

    @abstractmethod
    def refund_payment(self, payment):
        raise NotImplementedError


class ManualPaymentGateway(PaymentGateway):
    """Manual gateway for real offline/admin payment confirmation; it never auto-confirms payment."""
    name = 'manual'
    def create_payment(self, order, amount):
        return {'transaction_id': f'MANUAL-{order.order_number}-{timezone.now().strftime("%Y%m%d%H%M%S")}', 'status': Payment.STATUS_PENDING}
    def verify_payment(self, payment):
        return payment.status == Payment.STATUS_PAID
    def refund_payment(self, payment):
        return {'refunded': True}


class TestPaymentGateway(PaymentGateway):
    """Test-only gateway used in DEBUG/test environments to exercise success/failure workflow."""
    name = 'test'
    def create_payment(self, order, amount):
        return {'transaction_id': f'TEST-{order.order_number}-{timezone.now().strftime("%Y%m%d%H%M%S")}', 'status': Payment.STATUS_PROCESSING}
    def verify_payment(self, payment):
        return True
    def refund_payment(self, payment):
        return {'refunded': True}


def get_gateway(name='manual'):
    if name == 'test' and settings.DEBUG:
        return TestPaymentGateway()
    return ManualPaymentGateway()


@transaction.atomic
def create_payment(order, method='manual', gateway_name='manual'):
    gateway=get_gateway(gateway_name); data=gateway.create_payment(order, order.agreed_price)
    existing = Payment.objects.filter(order=order, status__in=[Payment.STATUS_PENDING, Payment.STATUS_PROCESSING]).first()
    if existing:
        return existing
    return Payment.objects.create(order=order, amount=order.agreed_price, currency=getattr(order,'currency','YER'), payment_method=method, gateway=gateway.name, transaction_id=data['transaction_id'], status=data.get('status', Payment.STATUS_PENDING))


@transaction.atomic
def mark_payment_paid(payment, actor=None):
    payment.status=Payment.STATUS_PAID; payment.paid_at=timezone.now(); payment.save(update_fields=['status','paid_at','updated_at'])
    order=payment.order; order.payment_status='paid'
    if order.status == order.STATUS_PAYMENT_PENDING:
        order.transition_to(order.STATUS_PAID, actor=actor)
    order.save()
    terms=TermsAndConditions.objects.filter(is_active=True).first()
    rate=terms.commission_rate if terms else 0
    amounts=calculate_commission(payment.amount, rate)
    CommissionRecord.objects.update_or_create(order=order, defaults={**amounts,'payment':payment,'currency':payment.currency})
    order.commission_rate=amounts['commission_rate']; order.commission_amount=amounts['commission_amount']; order.provider_net_amount=amounts['provider_net_amount']; order.save(update_fields=['commission_rate','commission_amount','provider_net_amount'])
    notify(order.provider,'payment_successful','تم الدفع',f'تم دفع الطلب {order.order_number}')
    audit(actor,'payment_paid',payment, order=order.order_number)
    return payment


@transaction.atomic
def mark_payment_failed(payment, actor=None, reason=''):
    payment.status=Payment.STATUS_FAILED; payment.save(update_fields=['status','updated_at'])
    order=payment.order; order.payment_status='failed'; order.save(update_fields=['payment_status'])
    notify(order.customer,'payment_failed','فشل الدفع',f'فشل دفع الطلب {order.order_number}')
    audit(actor,'payment_failed',payment, reason=reason, order=order.order_number)
    return payment
