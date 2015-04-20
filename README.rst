A Jenkins plugin for helga chat bot
===================================

About
-----

Helga is a Python chat bot. Full documentation can be found at
http://helga.readthedocs.org.

This Jenkins plugin allows Helga to run Jenkins playbooks from IRC and return
information when they succeed or fail.
For example::

  03:14 < alfredodeza> !jenkins ceph version=0.80.8.1 branch=rhcs-v0.80.8 release=stable clean=true
  03:14 < helgabot> running: ceph jop at http://jenkins.example.com/job/ceph/323


Failed builds will report back minimal information with an optional paste of
the log::

  03:17 < helgabot> alfredodeza: build ceph/323 failed. Details at http://jenkins.example.com/job/ceph/323/console

Successful runs will also report back to the user::

  03:19 < helgabot> alfredodeza: build ceph/323 suceeded!

Installation
------------
This Jenkins plugin is `available from PyPI
<https://pypi.python.org/pypi/helga-jenkins`_, so you can simply install it
with ``pip``::

  pip install helga-jenkins

If you want to hack on the helga-jenkins source code, in your virtualenv where
you are running Helga, clone a copy of this repository from GitHub and run
``python setup.py develop``.

Configuration
-------------
In your ``settings.py`` file (or whatever you pass to ``helga --settings``),
you can configure a few general things like (listed with some defaults)::

  # credentials
  JENKINS_USERNAME = "alfredodeza"
  JENKINS_PASSWORD = "ElCapitano2"
