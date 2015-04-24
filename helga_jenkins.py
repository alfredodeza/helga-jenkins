from helga.plugins import command
from helga import log, settings
from jenkins import Jenkins, JenkinsException

logger = log.getLogger(__name__)


def status(conn, name, *args):
    logger.debug('user requested name: %s' % name)
    return conn.get_job_info(name)


def jobs(conn, *args):
    return conn.get_jobs()


def health(conn, *args):
    info = conn.get_job_info(args[1])
    return info['healthReport'][0]['description']


def builds(conn, *args):
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


def build(conn, *args):
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))

    next_build_number = conn.get_job_info(name)['nextBuildNumber']

    params = args_to_dict(args)
    conn.build_job(name, parameters=params, token=conn.password)

    conn.get_build_info(name, next_build_number)
    from time import sleep; sleep(1)

    build_info = conn.get_build_info(name, next_build_number)
    return '%s build started at: %s' % (name, build_info['url']),


def get_name(conn, name):
    if conn.job_exists(name):
        return name
    raise RuntimeError('%s does not exist (or could not be found) in Jenkins' % name)


def enable(conn, *args):
    args = list(args)
    args.pop(0)  # get rid of the command
    name = get_name(conn, args.pop(0))
    conn.enable_job(name)
    return 'enabled job: %s' % name


def disable(conn, *args):
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
    url = getattr(settings, 'JENKINS_URL')
    if not url:
        raise RuntimeError('no JENKINS_URL is configured, cannot continue')
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


@command('jenkins', aliases=['ci'], help='control jenkins', priority=0)
def helga_jenkins(client, channel, nick, message, cmd, args):
    try:
        conn = connect(nick)
    except RuntimeError as error:
        return str(error)

    sub_commands = {
        # XXX commented out because they need trimming
        #'status': status,
        #'jobs': jobs,
        #'health': health,
        'builds': builds,
        'build': build,
        'enable': enable,
        'disable': disable,
    }

    sub_command = args[0]
    if len(args) == 1:
        return 'need more arguments for sub command: %s' % sub_command
    try:
        return sub_commands[sub_command](conn, *args)
    except (JenkinsException, RuntimeError) as error:
        return str(error)
    except KeyError:
        if sub_command == 'help':
            if args:  # we got asked for a specific command:
                try:
                    func = sub_commands[args[0]]
                except KeyError:
                    return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
                return [i.strip() for i in func.__doc__.strip().split('\n')]
        return '%s is not a command, valid ones are: %s' % (sub_command, str(sub_commands.keys()))
