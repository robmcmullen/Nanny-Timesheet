# Create your views here.
from datetime import date, datetime, timedelta
import dateutil.parser
import calendar
try:
    from itertools import combinations
except:
    def combinations(iterable, r):
        # combinations('ABCD', 2) --> AB AC AD BC BD CD
        # combinations(range(4), 3) --> 012 013 023 123
        pool = tuple(iterable)
        n = len(pool)
        if r > n:
            return
        indices = range(r)
        yield tuple(pool[i] for i in indices)
        while True:
            for i in reversed(range(r)):
                if indices[i] != i + n - r:
                    break
            else:
                return
            indices[i] += 1
            for j in range(i+1, r):
                indices[j] = indices[j-1] + 1
            yield tuple(pool[i] for i in indices)    

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.core import serializers
from django.core.context_processors import csrf
from django.utils import simplejson
from django.contrib.auth.decorators import login_required
from django import forms
from timesheet.models import *
from timesheet.taxes import *

DEBUG = False

def parsedict(querydict):
    """A dhtmlx post is formatted like this:
    
    post=<QueryDict: {u'1312398549900_start_date': [u'2011-08-02 08:45'],
     u'1312398549900_!nativeeditor_status': [u'inserted'],
     u'ids': [u'1312398549900'],
     u'1312398549900_id': [u'1312398549900'],
     u'1312398549900_end_date': [u'2011-08-02 11:30'],
     u'1312398549900_text': [u'New event']}>
    
    so you have to compose string keys for each id in order to get values for
    the particular id.
    
    This function breaks down the querydict into list of dicts where each
    entry in the list is a dict representing that id's data.  E.g.  the above
    example would decompose to:
    
    [
    {'id': '1312398549900', !nativeeditor_status': u'inserted',
    'start_date': u'2011-08-02 08:45', 'end_date': u'2011-08-02 11:30',
    'text': u'New event'},
    ]
    """
    ids = []
    retdict = {}
    for longkey in querydict.keys():
        if "_" in longkey:
            id, shortkey = longkey.split('_', 1)
            try:
                retdict[id][shortkey] = querydict[longkey]
            except KeyError:
                ids.append(id)
                retdict[id] = {shortkey: querydict[longkey]}
    #print ids, retdict
    return ids, retdict

# Simple view that brings up the index page.  Also supplies the CSRF token to
# the view so that the javascript can use it when it posts its updates.  Note
# that the dhtmlxScheduler javascript had to be slightly modified to handle
# Django's CSRF token.
@login_required
def index(request):
    c = {
        'kids': Kid.objects.all(),
        }
    c.update(csrf(request))
    return render_to_response("index.html", c,
                              context_instance=RequestContext(request))
 
# Gets JSON list of current events
@login_required
def all(request):
    if 'from' in request.GET and 'to' in request.GET:
        from_date = datetime.strptime(request.GET['from'], "%Y-%m-%d")
        to_date = datetime.strptime(request.GET['to'], "%Y-%m-%d")
        events = Event.objects.filter(start_date__gte=from_date).filter(start_date__lte=to_date)
    else:
        events = Event.objects.all()
    
    # Can't simply return a json representation of the list of Event objects
    # because the dhtmlxScheduler is expecting the json to be formatted
    # differently than serializers.serialize('json', events) formats it
    json_list = []
    for event in events:
        json_list.append(event.dhtmlx_json())
    return HttpResponse(simplejson.dumps(json_list), mimetype='application/json')
 
def first_day_next_month(d, force=False):
    if force or d.day > 1:
        newmonth = d.month + 1
        if newmonth > 12:
            newyear = d.year + 1
        else:
            newyear = d.year
        d = datetime.combine(date(newyear, newmonth, 1), d.timetz())
    return d


class KidStats(object):
    def __init__(self, kids, events, zero=False):
        self.include_zero = zero
        self.hours = []
        self.combo = []
        self.build = {}
        self.total_hours = 0.0
        self.total_net = Decimal("0.0")
        self.total_gross = Decimal("0.0")
        self.breakdown_details = []
        self.kid_details = []
        self.build_combo(kids)
        self.loop_events(kids, events)
    
    def build_combo(self, kids):
        for i in range(len(kids)):
            kid = kids[i]
            self.combo.extend(combinations(kids, i+1))
            self.build[i] = {'name': kid.person.first_name,
                             'id': kid.id,
                             'gross': 0.0,
                             'hours': 0.0,
                             'shared_hours': 0.0,
                             'details': []
                             }
        if DEBUG:
            print("combo: %s" % str(list(self.combo)))
    
    def loop_events(self, kids, events):
        details = []
        for p in self.combo:
            combo_hours = 0.0
            if DEBUG:
                print "%d kids" % len(p)
                print "%d events" % len(events)
            for ev in events:
                hours, rate, gross = ev.calc_gross(p)
                if hours > 0 or self.include_zero:
                    combo_hours += hours
                    if DEBUG:
                        print "%s: %f" % (ev.text, combo_hours)
                    detail = {'day': ev.start_date,
                              'hours': hours,
                              'rate': rate,
                              'gross': gross,
                              }
                    details.append((ev.start_date, detail))
                    
                    # kid_details[0]{'name': 'Evan',
                    #                'details': {'day': .... 'gross': ...},
                    #                }
                    for i in range(len(kids)):
                        kid = kids[i]
                        k = "kid%d" % kid.id
                        kid_rate = rate / len(p)
                        if kid in p:
                            d = dict(detail)
                            d['rate'] = kid_rate
                            d['gross'] = detail['hours'] * kid_rate
                            self.build[i]['details'].append((ev.start_date, d))
                            self.build[i]['gross'] += d['gross']
                            self.build[i]['hours'] += d['hours']
                            if len(p) > 1:
                                self.build[i]['shared_hours'] += d['hours']
            if len(p) == 1:
                name = "%s only" % p[0].person.first_name
            else:
                name = "+".join(k.person.first_name for k in p)
            self.hours.append([name, combo_hours])
            self.total_hours += combo_hours
        
        details.sort()
        self.breakdown_details = [d[1] for d in details]
        
        self.total_details()
    
    def total_details(self):
        for entry in self.build.values():
            if DEBUG:
                print "entry: %s" % str(entry)
            details = list(entry['details'])
            if details:
                details.sort()
                entry['details'] = [d[1] for d in details]
                w4 = W4.get_current(details[0][0])
                tax = TaxYear(details[0][0], entry['gross'], w4, w4)
                
                entry['net'] = tax.net
                entry['tax'] = tax
                self.total_net += tax.net
                self.total_gross += tax.gross
                entry['alone_hours'] = entry['hours'] - entry['shared_hours']
                self.kid_details.append(entry)
        if DEBUG:
            print self.kid_details

def get_weekly_stats(label, events, kids=None, zero=False):
    if kids is None:
        kids = Kid.objects.all()
    ks = KidStats(kids, events, zero)
    
    return {'duration': label,
            'kid_stats': ks,
            }

def get_monthly_stats(label, events):
    return {'duration': label,
            }

def get_events_range(start_date, end_date):
    if DEBUG:
        print "%s -> %s" % (start_date, end_date)
    events = Event.objects.filter(start_date__gte=start_date).filter(end_date__lte=end_date).exclude(text__icontains="holiday").order_by('start_date')
    if DEBUG:
        print "\n".join([str(e) for e in events])
    return events

# Gets HTML summary of current activity
@login_required
def stats(request):
    p = request.POST
    if DEBUG:
        print(p)
    raw = simplejson.loads(request.raw_post_data)
    if DEBUG:
        print(repr(raw))
    start_date = dateutil.parser.parse(raw['min_date']).astimezone(dateutil.tz.tzlocal())
    end_date = dateutil.parser.parse(raw['max_date']).astimezone(dateutil.tz.tzlocal())
    
    if raw['mode'] == 'month':
        # Modify start and end date to show the current month
        if start_date.day > 1:
            start_date = first_day_next_month(start_date)
        end_date = first_day_next_month(start_date, True)
        
        label = start_date.strftime("%B")
        stats_fcn = get_monthly_stats
    else:
        label = "this %s" % raw['mode']
        stats_fcn = get_weekly_stats
    events = get_events_range(start_date.date(), end_date.date())
    if events:
        template = "%s_stats.html" % raw['mode']
        template_params = stats_fcn(label, events)
    else:
        template = "no_stats.html"
        template_params = {'duration': label,
                           }
    
    template_params['start_date'] = start_date.date()
    template_params['end_date'] = (end_date - timedelta(hours=1)).date()
    
    return render_to_response(template, template_params,
                              context_instance=RequestContext(request))



class PaymentForm(forms.Form):
    amount = forms.DecimalField(max_digits=8, decimal_places=2)
    check_number = forms.IntegerField()
    note = forms.CharField(required=False)

# Enter payment form
@login_required
def pay(request):
    p = request.GET
    raw = p
    form = PaymentForm(initial={'amount': raw['net']})

    kid = Kid.objects.get(pk=int(raw['kid_id']))
    
    recent = Paycheck.objects.filter(paid_for=kid).order_by('-pay_date')
    
    template = "pay_form.html"
    template_params = {
        'date': date.today(),
        'start_date': dateutil.parser.parse(raw['start_date']),
        'end_date': dateutil.parser.parse(raw['end_date']),
        'target_id': raw['target_id'],
        'gross': raw['gross'],
        'net': raw['net'],
        'kid': kid,
        'form': form,
        'recent': recent,
        }
    
    return render_to_response(template, template_params,
                              context_instance=RequestContext(request))

# Process payment form
@login_required
def pay_process(request):
    p = request.POST
    raw = p
    form = PaymentForm(p)
    kid = Kid.objects.get(pk=int(raw['kid_id']))
    start_date = dateutil.parser.parse(raw['start_date'])
    end_date = dateutil.parser.parse(raw['end_date'])
    if form.is_valid():
        check = Paycheck(pay_date=date.today(), paid_by=request.user,
                         paid_for=kid, start_date=start_date, end_date=end_date,
                         gross=raw['gross'], net=raw['net'],
                         amount=form.cleaned_data['amount'],
                         note=form.cleaned_data['note'],
                         check_number=form.cleaned_data['check_number'],
                         )
        check.save()
        template = "pay_recorded.html"
        template_params = {
            'date': date.today(),
            'start_date': start_date,
            'end_date': end_date,
            'amount': form.cleaned_data['amount'],
            'gross': raw['gross'],
            'net': raw['net'],
            'note': form.cleaned_data['note'],
            'check_number': form.cleaned_data['check_number'],
            'kid': kid,
            }
    else:
        recent = Paycheck.objects.filter(paid_for=kid).order_by('-pay_date')
        template = "pay_form.html"
        template_params = {
            'date': date.today(),
            'start_date': start_date,
            'end_date': end_date,
            'target_id': raw['target_id'],
            'gross': raw['gross'],
            'net': raw['net'],
            'kid': kid,
            'form': form,
            'recent': recent,
            }
    
    return render_to_response(template, template_params,
                              context_instance=RequestContext(request))

# Update database with changes to the calendar
@login_required
def update(request):
    try:
        if DEBUG:
            print "In update.\n  GET=%s\n\n  POST=%s" % (str(request.GET),str(request.POST))
        p = request.POST
        k = p.keys()
        ids, d = parsedict(p)
        if len(ids) != 1:
            raise RuntimeError("Update only allowed with a single ID")
        id = ids[0]
        post = d[id]
        status = post['!nativeeditor_status']
        if DEBUG:
            print "    id=%s, status=%s, post=%s" % (id, status, post)
        db_id = None
        
        if status == "inserted":
            event = Event(start_date=datetime.strptime(post['start_date'], "%Y-%m-%d %H:%M"),
                          end_date=datetime.strptime(post['end_date'], "%Y-%m-%d %H:%M"),
                          text=post['text'])
            event.save()
            event.add_kids_by_csv(post['kids'])
            db_id = event.id
            template = 'update_data.xml'
        elif status == "updated":
            event = Event.objects.get(pk=id)
            event.start_date = datetime.strptime(post['start_date'], "%Y-%m-%d %H:%M")
            event.end_date = datetime.strptime(post['end_date'], "%Y-%m-%d %H:%M")
            event.text = post['text']
            event.save()
            event.add_kids_by_csv(post['kids'])
            db_id = event.id
            template = 'update_data.xml'
        elif status == "deleted":
            event = Event.objects.get(pk=id)
            event.delete()
            db_id = id
            template = 'delete_data.xml'
    except Exception,e:
        import traceback
        tb = traceback.format_exc()
        return render_to_response(
                'update_data_error.xml',
                {'error': e, 'traceback': tb},
                mimetype='text/xml', context_instance=RequestContext(request))
    else:
        return render_to_response(template,
                                  {'before_id': id, 'after_id': db_id},
                                  mimetype='text/xml',
                                  context_instance=RequestContext(request))

def flatten(l, level=2, current=0):
    out = []
    for item in l:
        if current < level and isinstance(item, (list, tuple)):
            out.extend(flatten(item, level, current+1))
        else:
            out.append(item)
    return out

def iter_weeks(year):
    c = calendar.Calendar(calendar.SUNDAY)
    weeks = flatten(c.yeardatescalendar(year, 1))
    last_sunday = weeks[0][0] - timedelta(7)
    for week in weeks:
        if week[0] > last_sunday:
            yield week
            last_sunday = week[0]

# Gets week-by-week list of payments and taxes
def get_week_summary_template_params(today, kids):
    week_list = []
    ytd = {
        'gross': Decimal("0.0"),
        'net': Decimal("0.0"),
        'kid': [dict.fromkeys(['gross', 'fed', 'cal', 'net', 'takehome'], Decimal("0.0")) for k in kids],
        }
    for week in iter_weeks(today.year):
        events = get_events_range(week[0], week[6] + timedelta(1))
        paychecks = Paycheck.get_range(week[0], week[6])
        #print paychecks
        stats = get_weekly_stats("stats", events, kids, True)
        entry = {'start_day': week[0],
                 'end_day': week[6],
                 'kid_stats': stats['kid_stats'],
                 'paychecks': paychecks,
                 }
        ks = stats['kid_stats']
        ytd['gross'] += ks.total_gross
        ytd['net'] += ks.total_net
        for index in range(len(ks.kid_details)):
            k = ks.kid_details[index]
            k['paychecks'] = []
            for p in paychecks:
                #print "Paycheck: %s" % str((p.paid_for, p.amount, p.pay_date))
                #print "Kid: %s" % kids[index]
                if p.paid_for == kids[index]:
                    #print "FOUND PAYCHECK!!!"
                    k['paychecks'].append(p)
                    ytd['kid'][index]['takehome'] += p.amount
            ytd['kid'][index]['gross'] += k['tax'].gross
            ytd['kid'][index]['fed'] += k['tax'].fed.employee_taxes
            ytd['kid'][index]['cal'] += k['tax'].cal.employee_taxes
            ytd['kid'][index]['net'] += k['tax'].net
            ytd['kid'][index]['id'] = kids[index].id
            
        # exclude weeks at the beginning of the year if no work done
        if ytd['gross'] > 0:
            week_list.append(entry)
        
        # Skip any weeks in the future by checking if the Sunday is after today
        if week[6] >= today:
            break
    
    template_params = {
        'week_list':week_list,
        'year': today.year,
        'ytd': ytd,
        'kids': kids,
        }
    return template_params

# Gets HTML summary of hours and taxes
@login_required
def ytd(request):
    today = date.today()
    kids = Kid.objects.all()
    template_params = get_week_summary_template_params(today, kids)
    return render_to_response("ytd.html", template_params,
                              context_instance=RequestContext(request))

# Gets HTML summary of payments
@login_required
def paychecks(request):
    today = date.today()
    kids = Kid.objects.all()
    template_params = get_week_summary_template_params(today, kids)
    return render_to_response("ytd_paychecks.html", template_params,
                              context_instance=RequestContext(request))

# Gets HTML summary of quarterly tax information
@login_required
def tax_year(request):
    today = date.today()
    kids = Kid.objects.all()
    template_params = get_week_summary_template_params(today, kids)
    return render_to_response("tax_year.html", template_params,
                              context_instance=RequestContext(request))
