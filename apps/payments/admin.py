from django.contrib import admin
from .models import Payment, CommissionRecord
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin): list_display=['order','amount','currency','status','payment_method','gateway','transaction_id','paid_at','created_at']; list_filter=['status','payment_method','gateway','created_at']; search_fields=['order__order_number','transaction_id']
@admin.register(CommissionRecord)
class CommissionAdmin(admin.ModelAdmin): list_display=['order','gross_amount','commission_rate','commission_amount','provider_net_amount','currency','created_at']; list_filter=['currency','created_at']; search_fields=['order__order_number']
