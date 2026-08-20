from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from .forms import ProviderDocumentForm
from .models import ProviderDocumentType
class ProviderDocumentValidationTests(TestCase):
    def test_rejects_executable_upload(self):
        doc_type=ProviderDocumentType.objects.create(code='IDENTITY',name='Identity')
        form=ProviderDocumentForm(data={'document_type':doc_type.pk}, files={'file':SimpleUploadedFile('bad.exe', b'MZ')})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
