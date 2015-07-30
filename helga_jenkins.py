from twisted.internet import reactor
from helga.plugins import command, ResponseNotReady
from helga import log, settings
from jenkins import Jenkins, JenkinsException

logger = log.getLogger(__name__)


def get_jenkins_url(settings):
    url = getattr(settings, 'JENKINS_URL', None)
    if not url:
        raise RuntimeError('no JENKINS_URL is configured, cannot continue')
    return url


def status(conn, name, *args, **kw):
    logger.debug('user requested name: %s' % name)
    return conn.get_job_info(name)


def jobs(conn, *args, **kw):
    return conn.get_jobs()


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


def args_to_dict(args):
    """
    Translate args that may look like::

        ["command", "sub-command"]

    """
    params = {}
    for item in args:
        if '=' in item:
            key, value = item.split('=')
        else:
            key, value = item, None
        params[key] = value

    return params


def async_build_info(jenkins_conn, name, next_build_number, client=None, channel=None, nick=None):
    build_info = jenkins_conn.get_build_info(name, next_build_number)
    msg = '%s: %s build started at: %s' % (name, build_info['url'])
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

    next_build_number = jenkins_conn.get_job_info(name)['nextBuildNumber']

    params = args_to_dict(args)
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


def connect(nick):
    """
    Since a user can have simple authentication with a single user/password or
    define a set of IRC nick to Jenkin's users with API tokens, this helper
    untangles this and returns a connection.

    If no authentication is configured, just a connection is returned with no
    authentication (probably read-only, depending on Jenkins settings)
    """
    url = get_jenkins_url(settings)
    username = getattr(settings, 'JENKINS_USERNAME', None)
    password = getattr(settings, 'JENKINS_PASSWORD', None)
    credentials = getattr(settings, 'JENKINS_CREDENTIALS', {})
    user_auth = credentials.get(nick, {})

    # favor user creds first, fallback to simple creds, and ultimately
    # fallback to None which is allowed
    user = user_auth.get('username', username)
    pass_ = user_auth.get('token', password)

    connection = Jenkins(
        url,
        username=user,
        password=pass_,
    )
    connection.password = pass_
    return connection


@command('jenkins', aliases=['ci'], help='Control Jenkins. See !jenkins help (or !ci help)', priority=0)
def helga_jenkins(client, channel, nick, message, cmd, args):
    try:
        conn = connect(nick)
    except RuntimeError as error:
        return str(error)

    sub_commands = {
        # XXX commented out because they need trimming
        #'status': status,
        #'jobs': jobs,
        'health': health,
        'builds': builds,
        'build': build,
        'enable': enable,
        'disable': disable,
    }

    sub_command = args[0]
    if len(args) == 1 and 'help' not in args:
        return 'need more arguments for sub command: %s' % sub_command
    try:
        return sub_commands[sub_command](conn, *args, client=client, channel=channel, nick=nick)
    except (JenkinsException, RuntimeError) as error:
        return str(error)
    except KeyError:
        if sub_command == 'help':
            if len(args) == 1:  # we just got 'help' so give a few examples of how to use it
                return "'help' is available for subcommands. For example: !ci help health. Available: %s" % str(sub_commands.keys())
            if len(args) > 1:  # we got asked for a specific command:
                try:
                    func = sub_commands[args[1]]
                except KeyError:
                    return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
                return [i.strip() for i in func.__doc__.strip().split('\n')]
        return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
