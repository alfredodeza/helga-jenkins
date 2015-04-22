from helga.plugins import command
from helga import log, settings
import jenkins

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

    # FIXME: need to call assert_job_exists()
    # to get some validation done here instead of assuming
    # input is right
    name = args.pop(0)  # get rid of the name
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

    return [
        '%s: %s' % (split_name(i), info[i]['url']) for i in keys
    ]


def parse_args(args):
    """
    Translate args that may look like::

        ["command", "sub-command"]

    """

def build(conn, *args):
    args = list(args)
    args.pop(0)  # get rid of the command

    # FIXME: need to call assert_job_exists()
    # to get some validation done here instead of assuming
    # input is right
    name = args.pop(0)  # get rid of the name
    pass


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
    user_auth = credentials.get(nick)

    # favor user creds first, fallback to simple creds, and ultimately
    # fallback to None which is allowed
    user = user_auth.get('username', username)
    pass_ = user_auth.get('password', username)

    return jenkins.Jenkins(
        url,
        username=user,
        password=_pass,
    )


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
    }

    sub_command = args[0]
    return sub_commands[sub_command](conn, *args)
