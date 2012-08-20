from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User

from timesheet import taxes

class Family(models.Model):
    name = models.TextField()

class Person(models.Model):
    first_name = models.TextField()
    last_name = models.TextField()
    family = models.ForeignKey(Family)

class Kid(models.Model):
    person = models.OneToOneField(Person)
    active = models.BooleanField(default=True)
    
    def __unicode__(self):
        return u"Kid: %d (person=%d) %s %s" % (self.id, self.person.id, self.person.first_name, self.person.last_name)

class Rate(models.Model):
    effective_date = models.DateTimeField()
    single_rate = models.FloatField()
    double_rate = models.FloatField()

    @classmethod
    def get_additional_overtime_rate(cls, date):
        # Get the most recent rate
        rate = Rate.objects.filter(effective_date__lte=date).order_by('-effective_date')[0]
        return rate.single_rate / 2.0

class W4(models.Model):
    effective_date = models.DateTimeField()
    allowances = models.IntegerField()
    person = models.ForeignKey(Person)
    family = models.ForeignKey(Family)
    
    def __unicode__(self):
        return "%s -> allowances=%s effective %s" % (self.family.name, self.allowances, self.effective_date)

    @classmethod
    def get_current(cls, date, family):
        # Get the most recent rate
        #print W4.objects.all()
        rate = W4.objects.filter(effective_date__lte=date).filter(family=family).order_by('-effective_date')[0]
        return rate

class DE4(models.Model):
    effective_date = models.DateTimeField()
    allowances = models.IntegerField()
    person = models.ForeignKey(Person)
    family = models.ForeignKey(Family)
    
    def __unicode__(self):
        return "%s -> allowances=%s effective %s" % (self.family.name, self.allowances, self.effective_date)

    @classmethod
    def get_current(cls, date, family):
        # Get the most recent rate
        rate = DE4.objects.filter(effective_date__lte=date).filter(family=family).order_by('-effective_date')[0]
        return rate

class Paycheck(models.Model):
    pay_date = models.DateField()
    paid_by = models.ForeignKey(User)
    paid_for = models.ForeignKey(Kid)
    start_date = models.DateField()
    end_date = models.DateField()
    gross = models.DecimalField(max_digits=8, decimal_places=2)
    net = models.DecimalField(max_digits=8, decimal_places=2)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    note = models.TextField()
    check_number = models.IntegerField()

    @classmethod
    def get_range(cls, start_date, end_date):
        """Get all paychecks that include events in the range and inclusive
        of the specified dates
        
        """
        paychecks = Paycheck.objects.filter(start_date__gte=start_date).filter(end_date__lte=end_date).order_by('start_date')
        return paychecks

class Event(models.Model):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    text = models.TextField()
    details = models.TextField()
    kids = models.ManyToManyField(Kid)
    
    def __unicode__(self):
        return "%s -> %s: %s %s %s" % (self.start_date, self.end_date, str([k.id for k in self.kids.all()]), self.text, self.details)
    
    def get_hours(self, kid_subset):
        s1 = set([k.id for k in kid_subset])
        s2 = set([k.id for k in self.kids.all()])
        if s1 == s2:
            td = (self.end_date - self.start_date)
            hours = (td.days * 24.0) + (td.seconds/3600.0)
        else:
            hours = 0
        return hours

    def get_rates(self):
        # Get the most recent rate
        rate = Rate.objects.filter(effective_date__lte=self.start_date).order_by('-effective_date')[0]
        
        rates = [0.0, rate.single_rate, rate.double_rate, rate.single_rate*2]
        t = self.text.lower()
        if 'half rate' in t or 'half time' in t:
            rates = [r / 2.0 for r in rates]
        if 'holiday' in t:
            rates = [r * 0.0 for r in rates]
        return rates

    def calc_gross(self, kid_subset):
        rates = self.get_rates()
        s1 = set([k.id for k in kid_subset])
        s2 = set([k.id for k in self.kids.all()])
        if s1 == s2:
            td = (self.end_date - self.start_date)
            hours = (td.days * 24.0) + (td.seconds/3600.0)
        else:
            hours = 0
        rate = rates[len(kid_subset)]
        gross = hours * rate
        return hours, rate, gross

    def add_kids_by_csv(self, csv):
        """Add kids given csv list of Kid IDs
        
        """
        self.kids.clear()
        print(csv)
        if csv:
            for id in csv.split(","):
                try:
                    pk = int(id)
                    print("attempting to add %d" % pk)
                    k = Kid.objects.get(pk=pk)
                    print("  kid object %s" % k.person.first_name)
                    self.kids.add(k)
                    print("added %d" % pk)
                except ValueError:
                    pass
                except Kid.DoesNotExist:
                    pass
            self.save()
        print self.dhtmlx_json()

    def dhtmlx_json(self):
        """
        The dhtmlxScheduler doesn't chokes on the json generated by
        serializers.serialize, so need this custom routine to generate the
        json it expects.
        """
        idlist = ",".join(str(k.id) for k in self.kids.all())
        if not idlist:
            idlist = "0"
        #print(idlist)
        return {
            'id': self.id,
            'start_date': self.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            'end_date': self.end_date.strftime("%Y-%m-%d %H:%M:%S"),
            'text': self.text,
            'details': self.details,
            'kids': idlist,
            }
