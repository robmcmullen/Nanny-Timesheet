"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime, date

from django.test import TestCase
from timesheet.models import *
from timesheet.taxes import *

from decimal import *
pennies = Decimal( "0.01" )
def round(d):
    return d.quantize(pennies, ROUND_HALF_UP)

class MockW4(object):
    def __init__(self, a=1):
        self.allowances = a

class CurrencyTest(TestCase):
    def assertCurrency(self, a, b):
        if not isinstance(b, Decimal):
            b = Decimal("%s" % b)
        #self.assertTrue(abs(a - b) < 0.01, "%.16f != %.16f within a penny" % (a, b))
        self.assertEqual(a, round(b))


class FederalTaxTestWeekly(CurrencyTest):
    def test_tax_year(self):
        w4 = MockW4()
        fed = FederalTax2011Weekly(Decimal("1000"), w4)
        self.assertEqual(fed.tax_year, 2011)
        self.assertEqual(fed.allowances, 1)
        self.assertEqual(fed.gross, Decimal("1000"))
        self.assertEqual(fed.one_allowance, Decimal("71.15"))
        #self.assertAlmostEqual(fed.one_allowance, 71.15, 2)
#        self.assertAlmostEqual(71.151, 71.15, 2)
#        self.assertAlmostEqual(71.154, 71.15, 2)
#        self.assertAlmostEqual(71.146, 71.15, 2)
#        self.assertAlmostEqual(71.149, 71.15, 2)
#        self.assertAlmostEqual(71.155, 71.15, 2)
#        self.assertAlmostEqual(71.157, 71.15, 2)
#        self.assertAlmostEqual(71.159, 71.15, 2)
#        self.assertAlmostEqual(71.16, 71.15, 2)

    def test_tax(self):
        rows = [(345.00, 202.70, 16.27, 14.49, 5.00, 309.24, 300.58),
                (408.00, 265.70, 25.66, 17.14, 5.92, 359.28, 348.23),
                (586.50, 444.20, 52.43, 24.63, 8.50, 500.94, 479.81),
                (532.75, 390.45, 44.37, 22.38, 7.72, 458.28, 440.23),
                (231.75,  89.45,  4.95,  9.73, 3.36, 213.71, 208.90),
                ]
        for gross, taxible, i, ss, m, fed_net, net in rows:
            w4 = MockW4(2)
            fed = FederalTax2011Weekly(gross, w4)
            self.assertEqual(fed.allowances, 2)
            self.assertCurrency(fed.gross, gross)
            self.assertCurrency(fed.taxible, taxible)
            self.assertCurrency(fed.employee_ss, ss)
            self.assertCurrency(fed.employee_medicare, m)
            self.assertCurrency(fed.income, i)
            self.assertCurrency(fed.net, fed_net)
    

class CalTaxTestWeekly(CurrencyTest):
    def test_tax_year(self):
        w4 = MockW4()
        cal = CalTax2011Weekly(Decimal("1000"), w4)
        self.assertEqual(cal.tax_year, 2011)
        self.assertEqual(cal.allowances, 1)
        self.assertEqual(cal.gross, Decimal("1000"))
        #self.assertAlmostEqual(cal.one_allowance, 71.15, 2)
#        self.assertAlmostEqual(71.151, 71.15, 2)
#        self.assertAlmostEqual(71.154, 71.15, 2)
#        self.assertAlmostEqual(71.146, 71.15, 2)
#        self.assertAlmostEqual(71.149, 71.15, 2)
#        self.assertAlmostEqual(71.155, 71.15, 2)
#        self.assertAlmostEqual(71.157, 71.15, 2)
#        self.assertAlmostEqual(71.159, 71.15, 2)
#        self.assertAlmostEqual(71.16, 71.15, 2)

    def test_tax(self):
        table = [(1, ((231.75, 160.75, 0.00, 2.78),
                      )
                  ),
                 (0, ((345.00, 274.00, 4.52, 4.14),
                      (408.00, 337.00, 6.17, 4.90),
                      (586.50, 515.50, 14.08, 7.04),
                      (532.75, 461.75, 11.66, 6.39),
                      (231.75, 160.75, 2.03, 2.78),
                      )
                  ),
                 ]
        for exemption, rows in table:
            w4 = MockW4(exemption)
            for gross, taxible, pit, sdi in rows:
                cal = CalTax2011Weekly(gross, w4)
                self.assertEqual(cal.allowances, exemption)
                self.assertCurrency(cal.gross, gross)
                self.assertCurrency(cal.taxible, taxible)
                self.assertCurrency(cal.sdi, sdi)
                self.assertCurrency(cal.pit, pit)


class TaxYearTest(TestCase):
    fixtures = ['2011-09-08']
    
    def test_w4(self):
        today = date.today()
        family = Family.objects.all()
        assert len(family) > 0
        w4 = W4.get_current(today, family[0])
        assert w4.allowances == 2
