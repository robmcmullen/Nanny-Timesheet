from django.conf.urls.defaults import *

urlpatterns = patterns('timesheet.views',
    (r'^$', 'index'),
    (r'^paychecks$', 'paychecks'),
    (r'^pay_process$', 'pay_process'),
    (r'^pay$', 'pay'),
    (r'^ytd$', 'ytd'),
    (r'^stats', 'stats'),
    (r'^all','all'),
    (r'^update','update'),
)
