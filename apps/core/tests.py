from decimal import Decimal
from django.test import TestCase
from apps.core.models import calculate_commission
class CommissionCalculationTests(TestCase):
    def test_calculate_commission_uses_decimal_snapshot_amounts(self):
        result=calculate_commission(Decimal('100.00'), Decimal('10.00'))
        self.assertEqual(result['commission_amount'], Decimal('10.00'))
        self.assertEqual(result['provider_net_amount'], Decimal('90.00'))
