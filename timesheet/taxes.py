"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from decimal import *
pennies = Decimal( "0.01" )
def round(d):
    return d.quantize(pennies, ROUND_HALF_UP)

class TaxBase(object):
    tax_year = None
    payroll_frequency = None
    
    def __init__(self, gross):
        if not isinstance(gross, Decimal):
            gross = Decimal("%s" % gross)
        self.gross = round(gross)
        self.net = Decimal("0.00")
        self.taxible = Decimal("0.00")
        self.employee_taxes = Decimal("0.00")
        self.employer_taxes = Decimal("0.00")
    
    def calc_simple_gross(self, rate):
        """Calculate simple tax based on gross salary"""
        return round(rate * self.gross)
    
    def calc_marginal(self, taxible, brackets):
        accounted_for = Decimal("0") # Running total of the portion of salary already taxed
        tax = Decimal("0") # Running total of tax from portion of salary already examined
        
        for (limit, rate) in self.brackets:
            if taxible < limit:
                tax += ( (taxible - accounted_for) * rate )
                accounted_for = taxible
                break # We've found the highest tax bracket we need to bother with
            else:
                tax += ( (limit - accounted_for) * rate )
                accounted_for = limit
        
        # If we went over the max defined tax bracket, use the final rate
        if accounted_for < taxible:
            tax += ( (taxible - accounted_for) * self.final_bracket )
        return round(tax)

class FederalTax(TaxBase):
    one_allowance = None
    employer_ss_rate = None
    employee_ss_rate = None
    employer_medicare_rate = None
    employee_medicare_rate = None
    
    def __init__(self, gross, w4):
        TaxBase.__init__(self, gross)
        self.allowances = w4.allowances
        self.income = Decimal("0.00")
        self.employer_ss = Decimal("0.00")
        self.employee_ss = Decimal("0.00")
        self.employer_medicare = Decimal("0.00")
        self.employee_medicare = Decimal("0.00")
        self.calc()
    
    def calc(self):
        self.employer_ss = self.calc_simple_gross(self.employer_ss_rate)
        self.employee_ss = self.calc_simple_gross(self.employee_ss_rate)
        self.employer_medicare = self.calc_simple_gross(self.employer_medicare_rate)
        self.employee_medicare = self.calc_simple_gross(self.employee_medicare_rate)
        self.taxible = self.calc_taxible()
        self.income = self.calc_marginal(self.taxible, self.brackets)
        self.employee_taxes = self.income + self.employee_ss + self.employee_medicare
        self.employer_taxes = self.employer_ss + self.employer_medicare
        self.net = self.gross - self.employee_taxes
    
    def calc_taxible(self):
        allowances = self.one_allowance * self.allowances
        return round(max(self.gross - allowances, Decimal("0.00")))

    
class FederalTax2011Weekly(FederalTax):
    tax_year = 2011
    payroll_frequency = "weekly"
    one_allowance = Decimal("71.15")
    employer_ss_rate = Decimal("0.062")
    employee_ss_rate = Decimal("0.042")
    employer_medicare_rate = Decimal("0.0145")
    employee_medicare_rate = Decimal("0.0145")
    brackets = [ (40, Decimal("0.0")), (204, Decimal(".10")), (704, Decimal(".15")), (1648, Decimal(".25")), (3394, Decimal(".28")), (7332, Decimal(".33")) ]
    final_bracket = Decimal(".35")


class CalTax(TaxBase):
    sdi_rate = None
    ui_rate = None
    ett_rate = None
    standard_deduction = None
    exemption_allowance = []
    
    def __init__(self, gross, de4):
        TaxBase.__init__(self, gross)
        self.allowances = de4.allowances
        self.pit = Decimal("0.00")
        self.sdi = Decimal("0.00")
        self.ui = Decimal("0.00")
        self.ett = Decimal("0.00")
        self.calc()
    
    def calc(self):
        self.sdi = self.calc_simple_gross(self.sdi_rate)
        self.ui = self.calc_simple_gross(self.ui_rate)
        self.ett = self.calc_simple_gross(self.ett_rate)
        self.taxible = self.calc_taxible()
        self.pit = max(self.calc_marginal(self.taxible, self.brackets) - self.calc_exemption_allowance(), Decimal("0.00"))
        self.employee_taxes = self.pit + self.sdi
        self.employer_taxes = self.ui + self.ett
        self.net = self.gross - self.employee_taxes
    
    def calc_taxible(self):
        return round(max(self.gross - self.standard_deduction, Decimal("0.00")))
    
    def calc_exemption_allowance(self):
        if self.allowances > len(self.exemption_allowance):
            return self.exemption_allowance[1] * self.allowances
        return self.exemption_allowance[self.allowances]

class CalTax2011Weekly(CalTax):
    tax_year = 2011
    sdi_rate = Decimal("0.012")
    ui_rate = Decimal("0.034")
    ett_rate = Decimal("0.001")
    brackets = [ (137, Decimal("0.011")), (325, Decimal(".022")), (513, Decimal(".044")), (712, Decimal(".066")), (899, Decimal(".088")), (19231, Decimal(".1023")) ]
    final_bracket = Decimal(".1133")
    standard_deduction = 71
    exemption_allowance = [Decimal("0.00"),
                           Decimal("2.09"),
                           Decimal("4.19"),
                           Decimal("6.28"),
                           Decimal("8.38"),
                           Decimal("10.47"),
                           Decimal("12.57"),
                           Decimal("14.66"),
                           Decimal("16.75"),
                           Decimal("18.85"),
                           Decimal("20.94"),
                           ]

class TaxYear(object):
    def __init__(self, date, gross, w4, de4):
        if not isinstance(gross, Decimal):
            gross = Decimal("%s" % gross)
        self.gross = round(gross)
        self.fed = FederalTax2011Weekly(self.gross, w4)
        self.cal = CalTax2011Weekly(self.gross, de4)
        self.net = self.gross - self.fed.employee_taxes - self.cal.employee_taxes
