"""
Views لتطبيق accounts (تسجيل، دخول، ملف شخصي)
Views for accounts app
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import DetailView
from django.contrib.auth import login as auth_login, logout as auth_logout
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm, ProviderProfileForm
from .models import User, ProviderProfile, ProviderDocument, ProviderDocumentType
from . import services
from .utils import get_provider_onboarding_status


def register_view(request):
    """
    صفحة تسجيل مستخدم جديد
    User registration page
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = form.cleaned_data['role']
            user.save()
            
            # منع تسجيل الدخول التلقائي لمقدمي الخدمات
            if user.is_provider():
                messages.success(request, 'تم إنشاء حسابك بنجاح! حسابك الآن قيد المراجعة من الإدارة لتتمكن من تقديم خدماتك. يرجى المحاولة لاحقاً.')
                return redirect('accounts:login')
                
            # تسجيل دخول تلقائي للعملاء
            auth_login(request, user)
            messages.success(request, f'مرحباً {user.username}! تم إنشاء حسابك بنجاح.')
            return redirect('home')
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    صفحة تسجيل الدخول
    Login page
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # تحقق من حالة الاعتماد لمقدمي الخدمات
            if user.is_provider():
                profile = services.get_provider_profile(user)
                if profile.status == 'pending':
                    messages.warning(request, 'حسابك قيد المراجعة حالياً من قبل الإدارة. يرجى الانتظار حتى يتم اعتماده لتتمكن من الدخول.')
                    return redirect('accounts:login')
                elif profile.status == 'rejected':
                    messages.error(request, 'نعتذر، لقد تم رفض طلبك للانضمام كمقدم خدمة.')
                    return redirect('accounts:login')
                    
            auth_login(request, user)
            messages.success(request, f'مرحباً بعودتك {user.username}!')
            
            # التوجيه للصفحة المطلوبة أو الرئيسية
            next_page = request.GET.get('next', 'home')
            return redirect(next_page)
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    تسجيل الخروج
    Logout
    """
    username = request.user.username
    auth_logout(request)
    messages.info(request, f'تم تسجيل خروجك بنجاح. نراك قريباً!')
    return redirect('home')


@login_required
def profile_view(request):
    """
    صفحة الملف الشخصي
    User profile page
    """
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث معلوماتك بنجاح.')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'user': user,
        'form': form,
    }
    
    # إذا كان مقدم خدمة، أضف معلومات إضافية
    if user.is_provider():
        context['provider_profile'] = services.get_provider_profile(user)
    
    return render(request, 'accounts/profile.html', context)


@login_required
def provider_profile_edit_view(request):
    """
    صفحة تعديل ملف مقدم الخدمة
    Provider profile edit page
    """
    # التحقق من أن المستخدم مقدم خدمة
    if not request.user.is_provider():
        messages.error(request, 'هذه الصفحة متاحة لمقدمي الخدمات فقط.')
        return redirect('accounts:profile')
    
    profile = services.get_provider_profile(request.user)
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        provider_form = ProviderProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and provider_form.is_valid():
            user_form.save()
            provider_form.save()
            messages.success(request, 'تم تحديث ملفك الشخصي بنجاح.')
            return redirect('accounts:provider_profile_edit')
    else:
        user_form = UserProfileForm(instance=request.user)
        provider_form = ProviderProfileForm(instance=profile)
    
    checklist, can_submit = get_provider_onboarding_status(profile)
    context = {
        'user_form': user_form,
        'provider_form': provider_form,
        'profile': profile,
        'verification_checklist': checklist,
        'can_submit_for_review': can_submit,
    }
    
    return render(request, 'accounts/provider_profile_edit.html', context)


class ProviderDetailView(DetailView):
    """
    صفحة عرض ملف مقدم الخدمة للزوار
    Public provider profile view
    """
    model = User
    template_name = 'accounts/provider_detail.html'
    context_object_name = 'provider'
    
    def get_queryset(self):
        """فقط المستخدمين من نوع provider"""
        return User.objects.filter(role='provider', is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provider = self.get_object()
        
        # الحصول على ملف مقدم الخدمة
        context['provider_profile'] = services.get_provider_profile(provider)
        context['provider_services'] = provider.services.filter(status='active').select_related('category')
        context['provider_reviews'] = provider.reviews_received.filter(is_public=True).select_related('customer', 'service')[:5]
        
        return context


# الدالة الديكورية للتحقق من الأدوار (سنستخدمها لاحقاً)
def role_required(allowed_roles):
    """
    ديكوريتر للتحقق من دور المستخدم
    Decorator to check user role
    
    Usage:
        @role_required(['provider', 'admin'])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'يجب تسجيل الدخول أولاً.')
                return redirect('accounts:login')
            
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة.')
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

@login_required
def provider_documents_view(request):
    if not request.user.is_provider():
        messages.error(request, 'هذه الصفحة لمقدمي الخدمات فقط.')
        return redirect('home')
    from .forms import ProviderDocumentForm
    from .models import ProviderDocument
    profile = services.get_provider_profile(request.user)
    if request.method == 'POST':
        form = ProviderDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False); doc.provider = profile; doc.save()
            messages.success(request, 'تم رفع المستند وإرساله للمراجعة.')
            return redirect('accounts:provider_documents')
    else:
        form = ProviderDocumentForm()
    required_types = ProviderDocumentType.objects.filter(is_active=True, is_required=True)
    uploaded_codes = set(ProviderDocument.objects.filter(provider=profile).values_list('document_type__code', flat=True))
    missing_documents = required_types.exclude(code__in=uploaded_codes)
    return render(request, 'accounts/provider_documents.html', {'form': form, 'documents': ProviderDocument.objects.filter(provider=profile).select_related('document_type'), 'required_types': required_types, 'missing_documents': missing_documents, 'missing_document_codes': set(missing_documents.values_list('code', flat=True))})

@login_required
def provider_submit_review(request):
    if not request.user.is_provider():
        messages.error(request, 'هذه الصفحة لمقدمي الخدمات فقط.'); return redirect('home')
    profile = services.get_provider_profile(request.user)
    if request.method == 'POST':
        checklist, can_submit = get_provider_onboarding_status(profile)
        if not can_submit:
            missing = ', '.join([key for key, ok in checklist.items() if not ok])
            messages.error(request, f'لا يمكن إرسال طلب المراجعة. أكمل المتطلبات الناقصة: {missing}')
            return redirect('accounts:provider_profile_edit')
        profile.verification_status = 'pending_review'; profile.status = 'inactive'; profile.save(update_fields=['verification_status','status','updated_at'])
        from apps.core.services import notify
        for admin in User.objects.filter(is_staff=True): notify(admin,'provider_submitted','طلب توثيق جديد',f'{request.user.username} أرسل حسابه للمراجعة')
        messages.success(request, 'تم إرسال ملفك للمراجعة.')
    return redirect('accounts:profile')


@login_required
def provider_document_download(request, pk):
    document = get_object_or_404(ProviderDocument, pk=pk)
    if not document.can_be_viewed_by(request.user):
        messages.error(request, 'ليس لديك صلاحية لعرض هذا المستند.')
        return redirect('home')
    from django.http import FileResponse
    return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.file.name.split('/')[-1])
