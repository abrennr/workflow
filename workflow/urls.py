from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    # Uncomment this for admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^workflow/', include('workflow.wflocal.urls')),
    (r'^core/', include('workflow.core.urls')),
)
