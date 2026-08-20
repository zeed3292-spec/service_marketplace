from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from apps.orders.models import Order
from .services import create_payment
@login_required
def payment_create(request, order_number):
    order=get_object_or_404(Order, order_number=order_number, customer=request.user)
    if order.status != Order.STATUS_PAYMENT_PENDING:
        messages.error(request,'لا يمكن إنشاء دفع لهذا الطلب حالياً.'); return redirect('orders:order_detail', order_number=order_number)
    payment=create_payment(order)
    messages.success(request,'تم إنشاء سجل الدفع. NEEDS EXTERNAL CONFIGURATION للبوابة الخارجية.')
    return render(request,'payments/payment_detail.html',{'payment':payment})
