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
<https://pypi.python.org/pypi/helga-jenkins>`_, so you can simply install it
with ``pip``::

  pip install helga-jenkins

If you want to hack on the helga-jenkins source code, in your virtualenv where
you are running Helga, clone a copy of this repository from GitHub and run
``python setup.py develop``.

Configuration
=============
In your ``settings.py`` file (or whatever you pass to ``helga --settings``),
you can configure a few general things like credentials and Jenkins locations.

In most cases, the plugin will only be configured for a single Jenkins
instance, but there is support for multiple instances if configured to do so.

Single Instance
---------------
A single instance can be configured as follows (listed with some defaults)::

  # simple authentication
  JENKINS_USERNAME = "alfredodeza"
  JENKINS_PASSWORD = "ElCapitano2"

  # Jenkins url
  JENKINS_URL = "http://jenkins.example.com"

  # for multiple auth/tokens, define a 'credentials' dictionary
  JENKINS_CREDENTIALS = {
    "alfredodeza": {
      "username": "adeza",
      "token": "33b3ffadgg3v61g1bfd6fd8543df50e4",
    }
  }

For multiple users, it is useful to map IRC nicks to usernames in Jenkins,
allowing a user to have different usernames (often the case).

Multiple Instances
------------------
For multiple instances, it is required to have defined a key that holds the
information for connections and users::

  # Multiple Jenkins
  MULTI_JENKINS = {
    "test": {
        # URL is always required
        'url': 'http://test_jenkins.example.com',
        'credentials': {
          "alfredodeza": {
              "username": "adeza",
              "token": "33b3ffadgg3v61g1bfd6fd8543df50e4",
          },
          "ktdreyer": {
            "username": "kdreyer",
            "token": "44bh4gggg3dkjasdweiuhr780wer234ss",
          }
        },
    "prod": {
        # if no credentials per-user is supplied, define a global one that
        # any user can use
        'url': 'http://test_jenkins.example.com',
        'username': 'admin',
        'password': 'secret',
  }

Note that each key in ``MULTI_JENKINS`` will equate to a supported command when
invoking it on IRC, for example::

  <alfredodeza> !ci test build test-job

Where *test* is a configured Jenkins instance. Or::

  <alfredodeza> !ci prod build other-job

Either ``credentials`` (with IRC nicks as keys, as username and tokens) or
``username`` and ``password`` must exist, the bot will fallback from one to the
other depending on what is defined and available to connect.

sub commands
------------
There are a few commands that are allowed, you can trigger their exampe usage
at any time with::

    !ci help {command}

This is a list of all the available ones with a short description of what they
do (most of them will require a job name argument at the very least):

* `enable`:  Enable a disabled job.
* `disable`: Disable an enabled job.
* `build`: Trigger a job build, will probably need authentication.
* `health`: Report on the current health of a job.
* `builds`: Report on the last builds of a job
