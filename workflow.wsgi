import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'workflow.settings'
sys.path.append('/usr/local/dlxs/prep/w/workflow/django')
sys.path.append('/usr/local/dlxs/prep/w/workflow/lib')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

os.environ['PYTHON_EGG_CACHE'] = '/tmp'
