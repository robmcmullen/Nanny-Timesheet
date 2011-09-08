from django.conf.urls.defaults import *

urlpatterns = patterns('social_auth_ui.views',
    (r'^$', 'provider'),
    (r'^js/$', 'jsprovider'),
    (r'^process/$', 'jsprocess'),
    (r'^manage/$', 'manage'),
    (r'^error/$', 'error'),
    (r'^signout/$', 'signout'),
)
