Nanny Timesheet is a Python/Django website for time tracking and payroll
calculations for a two-family nanny share.

It uses the GPL version of the `DHTMLX Scheduler`__ for AJAXian goodness.

__ http://dhtmlx.com/docs/products/dhtmlxScheduler/index.shtml

Also uses `django-social-auth`__ for OpenID validation.

__ http://pypi.python.org/pypi/django-social-auth/


Prerequisites
=============

* Python 2.5 - 2.7
* Django 1.3
* sqlite3 (usually installed with Python)
* dateutil 1.5 (note that dateutil 2.0 doesn't work with python 2.x)
* httplib2 (required by django-social-auth)
* oauth2 (required by django-social-auth)
* python_openid (required by django-social-auth)


Running Locally
===============

Don't forget to install prerequisites if not already installed.::

    $ pip install http://labix.org/download/python-dateutil/python-dateutil-1.5.tar.gz
    $ pip install httplib2
    $ pip install oauth2
    $ pip install python_openid

Check out the code using git.::

    $ git clone git://github.com/robmcmullen/Nanny-Timesheet.git

The code is already set up in a Django project, which may or may not be what
you want.  But it allows for easy development in place, so that's that.

Run a test server using::

    $ python manage.py runserver

and point your web browser at http://localhost:8000 to see the login screen.
You'll have to actually log in with one of the login methods (OpenID, google
account, etc.) in order to see the actual application.


Running On A Production Server
==============================

[FIXME: Apache integration docs go here...]

