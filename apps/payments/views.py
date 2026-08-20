from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.orders.models import Order
from .models import Payment
from .services import create_payment, mark_payment_paid, mark_payment_failed


@login_required
def payment_create(request, order_number):
    order=get_object_or_404(Order.objects.select_related('service','provider'), order_number=order_number, customer=request.user)
    if order.status != Order.STATUS_PAYMENT_PENDING:
        messages.error(request,'لا يمكن إنشاء دفع لهذا الطلب حالياً.')
        return redirect('orders:order_detail', order_number=order_number)
    payment=create_payment(order, method=request.POST.get('payment_method','manual') if request.method == 'POST' else 'manual')
    return redirect('payments:payment_detail', pk=payment.pk)


@login_required
def payment_detail(request, pk):
    payment=get_object_or_404(Payment.objects.select_related('order','order__service','order__provider'), pk=pk, order__customer=request.user)
    return render(request,'payments/payment_detail.html',{'payment':payment,'debug_payment_actions':settings.DEBUG})


@login_required
@require_POST
def payment_test_success(request, pk):
    if not settings.DEBUG:
        messages.error(request, 'تأكيد الدفع التجريبي غير متاح في الإنتاج.')
        return redirect('payments:payment_detail', pk=pk)
    payment=get_object_or_404(Payment, pk=pk, order__customer=request.user)
    mark_payment_paid(payment, actor=request.user)
    messages.success(request, 'تم تأكيد الدفع التجريبي وتحديث الطلب.')
    return redirect('orders:order_detail', order_number=payment.order.order_number)


@login_required
@require_POST
def payment_test_fail(request, pk):
    if not settings.DEBUG:
        messages.error(request, 'فشل الدفع التجريبي غير متاح في الإنتاج.')
        return redirect('payments:payment_detail', pk=pk)
    payment=get_object_or_404(Payment, pk=pk, order__customer=request.user)
    mark_payment_failed(payment, actor=request.user, reason='debug-test-failure')
    messages.error(request, 'تم تسجيل فشل الدفع التجريبي ولم يتم جعل الطلب مدفوعاً.')
    return redirect('payments:payment_detail', pk=pk)
