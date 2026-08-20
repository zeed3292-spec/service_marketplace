from django.db import models
from django.core.validators import MinValueValidator
class Payment(models.Model):
    STATUS_PENDING='pending'; STATUS_PROCESSING='processing'; STATUS_PAID='paid'; STATUS_FAILED='failed'; STATUS_REFUNDED='refunded'; STATUS_CANCELLED='cancelled'
    STATUS_CHOICES=[(STATUS_PENDING,'في الانتظار'),(STATUS_PROCESSING,'قيد المعالجة'),(STATUS_PAID,'مدفوع'),(STATUS_FAILED,'فشل'),(STATUS_REFUNDED,'مسترد'),(STATUS_CANCELLED,'ملغي')]
    order=models.ForeignKey('orders.Order',on_delete=models.CASCADE,related_name='payments')
    amount=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])
    currency=models.CharField(max_length=3,default='YER')
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_PENDING,db_index=True)
    payment_method=models.CharField(max_length=50,default='manual')
    transaction_id=models.CharField(max_length=120,blank=True,db_index=True)
    gateway=models.CharField(max_length=80,default='manual')
    paid_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        indexes=[models.Index(fields=['status','created_at']),models.Index(fields=['payment_method','created_at'])]
        permissions=[('manage_payments','Can manage payments')]
    def __str__(self): return f'{self.order} - {self.amount} {self.currency}'
class CommissionRecord(models.Model):
    order=models.OneToOneField('orders.Order',on_delete=models.CASCADE,related_name='commission_record')
    payment=models.OneToOneField(Payment,on_delete=models.SET_NULL,null=True,blank=True,related_name='commission_record')
    commission_rate=models.DecimalField(max_digits=5,decimal_places=2)
    gross_amount=models.DecimalField(max_digits=10,decimal_places=2)
    commission_amount=models.DecimalField(max_digits=10,decimal_places=2)
    provider_net_amount=models.DecimalField(max_digits=10,decimal_places=2)
    currency=models.CharField(max_length=3,default='YER')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: permissions=[('manage_commissions','Can manage commissions')]
