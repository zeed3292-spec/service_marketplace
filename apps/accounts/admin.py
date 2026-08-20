"""
إعدادات لوحة الإدارة لتطبيق accounts
Admin configuration for accounts app  
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, ProviderProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    إدارة المستخدمين في لوحة التحكم
    Custom User admin
    """
    list_display = ['username', 'email', 'role', 'is_verified', 'is_active', 'created_at']
    list_filter = ['role', 'is_verified', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'phone', 'city']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('معلومات إضافية', {
            'fields': ('role', 'phone', 'city', 'is_verified')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('معلومات إضافية', {
            'fields': ('email', 'role', 'phone', 'city', 'is_verified')
        }),
    )


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    """
    إدارة ملفات مقدمي الخدمات
    Provider profiles admin
    """
    list_display = ['user', 'specialization', 'experience_years', 'get_status_badge', 'average_rating', 
                    'completed_orders', 'is_available', 'created_at']
    list_filter = ['status', 'is_available', 'specialization', 'created_at']
    search_fields = ['user__username', 'user__email', 'specialization', 'bio']
    readonly_fields = ['total_orders', 'completed_orders', 'average_rating', 'created_at', 'updated_at']
    ordering = ['-average_rating', '-completed_orders']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('user', 'bio', 'profile_image')
        }),
        ('معلومات العمل', {
            'fields': ('specialization', 'experience_years', 'hourly_rate', 'status', 'is_available')
        }),
        ('الموقع الجغرافي', {
            'fields': ('address', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('الإحصائيات', {
            'fields': ('total_orders', 'completed_orders', 'average_rating'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_providers', 'reject_providers','request_documents','suspend_providers']
    
    def get_status_badge(self, obj):
        colors = {
            'inactive': 'secondary',
            'active': 'success',
            'suspended': 'danger',
        }
        labels = dict(ProviderProfile.STATUS_CHOICES)
        return format_html('<span class="badge bg-{}">{}</span>', colors.get(obj.status, 'secondary'), labels.get(obj.status, obj.status))
    get_status_badge.short_description = 'حالة الحساب'
    
    def approve_providers(self, request, queryset):
        """الموافقة على مقدمي الخدمات المحددين"""
        updated = queryset.update(status='active', verification_status='verified', verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f'تم الموافقة على {updated} مقدم خدمة.')
    approve_providers.short_description = 'الموافقة على مقدمي الخدمات المحددين'
    
    def reject_providers(self, request, queryset):
        """رفض مقدمي الخدمات المحددين"""
        updated = queryset.update(status='inactive', verification_status='rejected')
        self.message_user(request, f'تم رفض {updated} مقدم خدمة.')
    reject_providers.short_description = 'رفض مقدمي الخدمات المحددين'

from django.utils import timezone
from .models import ProviderDocumentType, ProviderDocument
from apps.core.services import audit, notify

@admin.register(ProviderDocumentType)
class ProviderDocumentTypeAdmin(admin.ModelAdmin):
    list_display=['code','name','is_required','is_active','created_at']; list_filter=['is_required','is_active']; search_fields=['code','name']

@admin.register(ProviderDocument)
class ProviderDocumentAdmin(admin.ModelAdmin):
    list_display=['provider','document_type','status','reviewed_by','reviewed_at','created_at']
    list_filter=['status','document_type','created_at']; search_fields=['provider__user__username','document_type__name']; raw_id_fields=['provider','reviewed_by']
    actions=['approve_documents','reject_documents','request_more_documents']
    def _review(self, request, queryset, status, event):
        for doc in queryset:
            doc.status=status; doc.reviewed_by=request.user; doc.reviewed_at=timezone.now(); doc.save(update_fields=['status','reviewed_by','reviewed_at','updated_at'])
            notify(doc.provider.user,event,'تحديث مستندات التوثيق',f'تم تحديث حالة المستند: {doc.document_type.name}')
            audit(request.user,f'document_{status}',doc)
    def approve_documents(self, request, queryset): self._review(request,queryset,'approved','provider_verified')
    def reject_documents(self, request, queryset): self._review(request,queryset,'rejected','provider_rejected')
    def request_more_documents(self, request, queryset): self._review(request,queryset,'needs_additional_documents','documents_requested')

def _provider_action(modeladmin, request, queryset, status, verification):
    queryset.update(status=status, verification_status=verification)
ProviderProfileAdmin.request_documents = lambda self, request, queryset: _provider_action(self, request, queryset, 'inactive', 'needs_documents')
ProviderProfileAdmin.request_documents.short_description = 'طلب مستندات إضافية'
ProviderProfileAdmin.suspend_providers = lambda self, request, queryset: _provider_action(self, request, queryset, 'suspended', 'suspended')
ProviderProfileAdmin.suspend_providers.short_description = 'إيقاف مقدمي الخدمات'
