from twisted.internet import reactor
from helga.plugins import command, ResponseNotReady
from helga import log, settings
from jenkins import Jenkins, JenkinsException, NotFoundException
from urllib2 import HTTPError

logger = log.getLogger(__name__)


def get_jenkins_url(settings):
    url = getattr(settings, 'JENKINS_URL', None)
    if not url:
        raise RuntimeError('no JENKINS_URL is configured, cannot continue')
    return url


def job_is_parametrized(job_info):
    """
    If a job is parametrized but no arguments are passed in, then
    python-jenkins will use a different URL to trigger the job (vs. using the
    url that indicates the job is parametrized) causing builds to error and not
    get started.

    This check helps by looking into the job_config to determine if the job is
    in fact parametrized so that we can add a bogus param and trick
    python-jenkins in using the correct URL
    """
    actions = job_info.get('actions', [])
    if not actions:
        return False
    for action in actions:
        if action.get('parameterDefinitions'):
            return True


def get_job_params(build_info):
    """
    A job info is a big dictionary blob and the parameters are tough to parse
    because they are mixed in a series of lists and dictionaries, so we need to
    do a few loops and ensure that the parameters for a given job are there
    otherwise return a sensible default.

    ``params`` live within the 'actions' key in ``job_info`` and it looks something
    similar to::

        [{u'causes': [{u'shortDescription': u'Started by GitHub push by ktdreyer'}]},
         {},
         {u'parameters': [{u'name': u'FORCE', u'value': False}]},
         {},
         {u'buildsByBranchName': {u'origin/master': {u'buildNumber': 155,
            u'buildResult': None,
            u'marked': {u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
             u'branch': [{u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
               u'name': u'origin/master'}]},
            u'revision': {u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
             u'branch': [{u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
               u'name': u'origin/master'}]}}},
          u'lastBuiltRevision': {u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
           u'branch': [{u'SHA1': u'dc331670463992addddb6f03aff364e61693c5f5',
             u'name': u'origin/master'}]},
          u'remoteUrls': [u'https://github.com/ceph/ceph-build'],
          u'scmName': u''},
         {},
         {},
         {}]

    """
    actions = build_info.get('actions', [])
    param_items = [i for i in actions if 'parameters' in i] or [{}]
    params = param_items[0].get('parameters', [])
    param_string = ''
    for p in params:
        param_string += '%s=%s ' % (p['name'], p['value'])
    return param_string


def jobs(conn, *args, **kw):
    return conn.get_jobs()


def status(conn, *args, **kw):
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    # get build number of last build
    build_number = conn.get_job_info(name)['nextBuildNumber']
    try:
        info = conn.get_build_info(name, build_number)
    except NotFoundException:
        # use the previous one
        info = conn.get_build_info(name, build_number-1)
    params = get_job_params(info)
    param_string = 'params: {0}'.format(params) if params else ''
    if info['building']:
        # it is currently building so return a corresponding message
        msg = 'BUILDING %s on server: %s url: %s %s' % (
            name,
            info['builtOn'],
            info['url'],
            param_string,
        )
    else:
        msg = '%s for %s on server: %s url: %s %s' % (
            str(info['result']).upper(),
            name,
            info['builtOn'],
            info['url'],
            param_string,
        )

    return msg


def async_status(conn, name, build_number, client=None, channel=None, nick=None):
    """
    an async status is meant to poll the jenkins server and just report back
    if the build is no longer running.
    """
    info = conn.get_build_info(name, build_number)

    if info['building']:
        # it is currently building so return a corresponding message
        reactor.callLater(
            60,
            async_status,
            conn,
            name,
            build_number,
            client=client,
            channel=channel,
            nick=nick
        )

    else:
        msg = '%s %s for %s on server: %s url: %s' % (
            nick,
            str(info['result']).upper(),
            name,
            info['builtOn'],
            info['url']
        )
        client.msg(channel, msg)


def health(conn, *args, **kw):
    """
    Get a report of the health of a given build. Example usage::
        !ci health {job}
    """
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    info = conn.get_job_info(name)
    return info['healthReport'][0]['description']


def builds(conn, *args, **kw):
    """
    Get the status of builds for a given job. Defaults to last, failed, and good builds. Example usage::
        !ci builds {job}
        !ci builds {job} (ok|bad|last)
    """
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    info = conn.get_job_info(name)

    sub_commands = {
        'last': 'lastBuild',
        'failed': 'lastFailedBuild',
        'bad': 'lastFailedBuild',
        'successful': 'lastSuccessfulBuild',
        'ok': 'lastSuccessfulBuild',
        'good': 'lastSuccessfulBuild',
        'pass': 'lastSuccessfulBuild',
    }

    if args:  # we got asked for a specific one
        keys = [sub_commands.get(args[0])] or []
    else:
        keys = [
            'lastBuild',
            'lastSuccessfulBuild',
            'lastFailedBuild',
        ]

    def split_name(name):
        title = []
        for ch in name:
            if ch.isupper():
                title.append(' ')
            title.append(ch)
        return ''.join(title)

    def build_info(info, key):
        if info[key] is None:
            return 'there are no "%s" recorded for this job' % split_name(key)
        return '%s: %s' % (split_name(key), info[key]['url'])

    return [
        '%s' % build_info(info, key) for key in keys
    ]


def args_to_dict(args, add_bogus=False):
    """
    Translate args that may look like::

        ["command", "sub-command", "FORCE=True"]

    Into:

        {'FORCE': 'True'}

    Optionally it adds a bogus key so that python-jenkins
    can use the right parametrized url

    """
    params = {}
    if add_bogus:
        params['__bogus_param__'] = "1"

    for item in args:
        if '=' in item:
            key, value = item.split('=')
        else:
            key, value = item, None
        params[key] = value

    return params


def async_build_info(jenkins_conn, name, next_build_number, client=None, channel=None, nick=None):
    build_info = jenkins_conn.get_build_info(name, next_build_number)
    msg = '%s: %s build started at: %s' % (nick, name, build_info['url'])
    client.msg(channel, msg)


def build(jenkins_conn, *args, **kw):
    """
    Trigger a build in Jenkins. Authentication is probably required. Example usage::
        !ci build {job} BRANCH=master RELEASE=True
    """
    # blow up if we don't have these
    client = kw['client']
    channel = kw['channel']
    nick = kw['nick']

    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(jenkins_conn, args.pop(0))
    info = jenkins_conn.get_job_info(name)

    next_build_number = info['nextBuildNumber']

    params = args_to_dict(args, add_bogus=job_is_parametrized(info))
    jenkins_conn.build_job(name, parameters=params, token=jenkins_conn.password)

    # we need to wait for a little while before jenkins gets out of the silent
    # period so that we can ask for information about the build.
    reactor.callLater(
        10,
        async_build_info,
        jenkins_conn,
        name,
        next_build_number,
        client=client,
        channel=channel,
        nick=nick
    )
    # now we also need to set a recurring check for the build so that when it
    # completes the user will get pinged about it.
    reactor.callLater(
        60,
        async_status,
        jenkins_conn,
        name,
        next_build_number,
        client=client,
        channel=channel,
        nick=nick
    )

    raise ResponseNotReady


def get_name(conn, name):
    if conn.job_exists(name):
        return name
    raise RuntimeError('%s does not exist (or could not be found) in Jenkins' % name)


def enable(conn, *args, **kw):
    """
    Enable a job that is currently disabled. Example usage::
        !ci enable {job}
    """
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    conn.enable_job(name)
    return 'enabled job: %s' % name


def disable(conn, *args, **kw):
    """
    Disable a job that is currently enabled. Example usage::
        !ci disable {job}
    """
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    conn.disable_job(name)
    return 'disabled job: %s' % name


def connect(credentials):
    """
    Since a user can have simple authentication with a single user/password or
    define a set of IRC nick to Jenkin's users with API tokens, this helper
    untangles this and returns a connection.

    If no authentication is configured, just a connection is returned with no
    authentication (probably read-only, depending on Jenkins settings)
    """
    connection = Jenkins(
        credentials['url'],
        username=credentials['username'],
        password=credentials['password'],
    )
    connection.password = credentials['password']

    # try an actual request so we can bail if something is off
    connection.get_info()

    return connection


sub_commands = {
    'status': status,
    'health': health,
    'builds': builds,
    'build': build,
    'enable': enable,
    'disable': disable,
}


def parse_instance(arguments):
    multi = getattr(settings, 'MULTI_JENKINS', None)
    if multi:
        instance = arguments[0]
        if instance in multi.keys():
            return instance
    return None


def parse_credentials(nick, arguments, instance=None):
    """
    A trivial helper to make sense of the arguments passed in, validate them,
    and error accordingly if information is missing or erroneous

    Returns a dictionary with the mappings necessary to operate throughout the
    plugin.

    ``args`` is a list of arguments after the name of the plugin. For example::

        !ci build job

    Would get this function: ``['build', 'job']``
    """
    parsed = {}
    # First, look if we have ``MULTI_JENKINS`` set so that we can prioritize that
    multi = getattr(settings, 'MULTI_JENKINS', None)
    if multi:
        # make sure that configured instances will not collide with supported
        # sub-commands
        for k in multi.keys():
            if k in sub_commands.keys():
                raise RuntimeError(
                    "A configured Jenkins instance ('%s') has the same name as \
                    a sub-command. This is not allowed, that instance needs to \
                    be renamed." % k
                )
        # If we didn't raise it means that we should check if the first argument
        # is a configured Jenkins instance before continuing
        if arguments[0] in multi.keys():
            instance = arguments[0]
            try:
                parsed['url'] = multi[instance]['url']
            except KeyError:
                raise RuntimeError('"url" is a required key for Jenkins instance "%s"' % instance)

            # per-nick credentials first
            credentials = multi[instance].get('credentials', {})
            user_auth = credentials.get(nick, {})
            username = user_auth.get('username')
            password = user_auth.get('token')

            if not username:
                # fallback to regular user creds
                username = multi[instance].get('username')
                password = multi[instance].get('password')

            parsed['username'] = username
            parsed['password'] = password

    else:
        parsed['url'] = get_jenkins_url(settings)
        username = getattr(settings, 'JENKINS_USERNAME', None)
        password = getattr(settings, 'JENKINS_PASSWORD', None)
        credentials = getattr(settings, 'JENKINS_CREDENTIALS', {})
        user_auth = credentials.get(nick, {})

        # favor user creds first, fallback to simple creds, and ultimately
        # fallback to None which is allowed
        user = user_auth.get('username')
        token = user_auth.get('token')
        if user and token:
            username = user
            password = token

        parsed['username'] = username
        parsed['password'] = password

    try:
        for k in ['username', 'password', 'url']:
            if parsed[k] is None:
                raise KeyError(k)
    except KeyError as missing_key:
        if instance:
            msg = 'Unable to connect to %s, missing credential config key: %s' % (instance, missing_key)
        else:
            msg = 'Unable to connect, missing credential config key: %s' % (missing_key)
        raise RuntimeError(msg)

    return parsed


@command('jenkins', aliases=['ci'], help='Control Jenkins. See !jenkins help (or !ci help)', priority=0, shlex=True)
def helga_jenkins(client, channel, nick, message, cmd, args):
    instance = parse_instance(args)
    credentials = parse_credentials(nick, args, instance)
    try:
        conn = connect(credentials)
    except RuntimeError as error:
        return str(error)
    except JenkinsException as error:
        try:
            nick_msg = "%s is probably unauthorized to connect to Jenkins as '%s'" % (nick, credentials['username'])
        except KeyError:
            nick_msg = "%s is not configured to connect to Jenkins" % nick
        msg = [
            nick_msg,
            "An API token and matching IRC nick and Jenkins usernames are required",
            "Error from Jenkins was: %s" % str(error)
        ]
        return msg

    sub_command = args[0]
    if len(args) == 1 and 'help' not in args:
        return 'need more arguments for sub command: %s' % sub_command
    try:
        return sub_commands[sub_command](conn, *args, client=client, channel=channel, nick=nick)
    except (JenkinsException, HTTPError, RuntimeError) as error:
        return str(error)
    except KeyError:
        if sub_command == 'help':
            if len(args) == 1:  # we just got 'help' so give a few examples of how to use it
                return (
                    "help is available for subcommands: %s." % ' '.join(sub_commands.keys()),
                    "subcommand help can be requested with: !ci help {subcommand}"
                )
            if len(args) > 1:  # we got asked for a specific command:
                try:
                    func = sub_commands[args[1]]
                except KeyError:
                    return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
                return [i.strip() for i in func.__doc__.strip().split('\n')]
        return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
