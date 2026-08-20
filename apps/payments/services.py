from django.db import transaction
from django.utils import timezone
from apps.core.models import TermsAndConditions, calculate_commission
from apps.core.services import notify, audit
from .models import Payment, CommissionRecord

class ManualPaymentGateway:
    name='manual'
    def create_payment(self, order, amount): return {'transaction_id': f'MANUAL-{order.order_number}'}
    def verify_payment(self, payment): return payment.status == Payment.STATUS_PAID
    def refund_payment(self, payment): return {'refunded': True}

@transaction.atomic
def create_payment(order, method='manual'):
    gateway=ManualPaymentGateway(); data=gateway.create_payment(order, order.agreed_price)
    return Payment.objects.create(order=order,amount=order.agreed_price,currency=getattr(order,'currency','YER'),payment_method=method,gateway=gateway.name,transaction_id=data['transaction_id'])

@transaction.atomic
def mark_payment_paid(payment, actor=None):
    payment.status=Payment.STATUS_PAID; payment.paid_at=timezone.now(); payment.save(update_fields=['status','paid_at','updated_at'])
    order=payment.order; order.payment_status='paid'; order.transition_to(order.STATUS_PAID, actor=actor); order.save()
    terms=TermsAndConditions.objects.filter(is_active=True).first()
    rate=terms.commission_rate if terms else 0
    amounts=calculate_commission(payment.amount, rate)
    CommissionRecord.objects.update_or_create(order=order, defaults={**amounts,'payment':payment,'currency':payment.currency})
    notify(order.provider,'payment_successful','تم الدفع',f'تم دفع الطلب {order.order_number}')
    audit(actor,'payment_paid',payment, order=order.order_number)
    return payment
