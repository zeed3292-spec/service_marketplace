from decimal import Decimal
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from apps.marketplace.models import Category, Service
from apps.core.models import TermsAndConditions, TermsAcceptance
from .forms import ProviderDocumentForm, ProviderProfileForm
from .models import ProviderDocument, ProviderDocumentType, User

class ProviderDocumentValidationTests(TestCase):
    def setUp(self):
        self.doc_type=ProviderDocumentType.objects.get(code='IDENTITY')
    def test_rejects_executable_upload(self):
        form=ProviderDocumentForm(data={'document_type':self.doc_type.pk}, files={'file':SimpleUploadedFile('bad.exe', b'MZ', content_type='application/x-msdownload')})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
    def test_accepts_pdf_upload_and_saves_private_document(self):
        user=User.objects.create_user(username='provider-doc', email='pd@example.com', password='x', role='provider')
        form=ProviderDocumentForm(data={'document_type':self.doc_type.pk}, files={'file':SimpleUploadedFile('id.pdf', b'%PDF-1.4', content_type='application/pdf')})
        self.assertTrue(form.is_valid(), form.errors)
        doc=form.save(commit=False); doc.provider=user.provider_profile; doc.save()
        self.assertTrue(doc.file.name.startswith('provider_documents/'))
    def test_provider_cannot_download_another_provider_document(self):
        owner=User.objects.create_user(username='owner', email='owner@example.com', password='x', role='provider')
        other=User.objects.create_user(username='other', email='other@example.com', password='x', role='provider')
        doc=ProviderDocument.objects.create(provider=owner.provider_profile, document_type=self.doc_type, file=SimpleUploadedFile('id.pdf', b'%PDF', content_type='application/pdf'))
        self.client.force_login(other)
        response=self.client.get(reverse('accounts:provider_document_download', args=[doc.pk]))
        self.assertEqual(response.status_code, 302)

class ProviderLocationAndOnboardingTests(TestCase):
    def test_provider_profile_form_saves_location_coordinates(self):
        user=User.objects.create_user(username='map-provider', email='map@example.com', password='x', role='provider')
        form=ProviderProfileForm(data={'bio':'Bio','specialization':'Design','experience_years':3,'hourly_rate':'10.00','address':'Street','city':'Sanaa','district':'Old City','latitude':'15.369400','longitude':'44.191000','service_radius':10,'availability':'Daily','qualifications':'Cert','experience':'Work','is_available':'on'}, instance=user.provider_profile)
        self.assertTrue(form.is_valid(), form.errors)
        profile=form.save()
        self.assertEqual(profile.latitude, Decimal('15.369400'))
        self.assertEqual(profile.longitude, Decimal('44.191000'))
    def test_submit_review_requires_checklist(self):
        user=User.objects.create_user(username='incomplete', email='inc@example.com', password='x', role='provider')
        self.client.force_login(user)
        response=self.client.post(reverse('accounts:provider_submit_review'))
        user.provider_profile.refresh_from_db()
        self.assertNotEqual(user.provider_profile.verification_status, 'pending_review')
        self.assertEqual(response.status_code, 302)
