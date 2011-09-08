from django.conf.urls.defaults import patterns, include, url
from nanny import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'nanny.views.home', name='home'),
    # url(r'^nanny/', include('nanny.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    # Applications
    (r'^timesheet/', include('timesheet.urls')),
    (r'^$', 'timesheet.views.index'),

    # Login stuff
    (r'^logout/', 'social_auth_ui.views.signout'),
    (r'^auth/', include('social_auth_ui.urls')),
    (r'', include('social_auth.urls')),
)
