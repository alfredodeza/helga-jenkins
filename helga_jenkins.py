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
    args.pop([0]) # get rid of the command
    info = conn.get_job_info(args.pop[1])
    sub_commands = {
        'last': 'lastBuild',
        'failed': 'lastFailedBuild',
        'successful': 'lastSuccessfulBuild',
        'ok': 'lastSuccessfulBuild',
        'good': 'lastSuccessfulBuild',
        'pass': 'lastSuccessfulBuild',
    }


    if args:  # we got asked for a specific one
        keys = sub_commands.get(args[0]) or []
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


@command('jenkins', aliases=['ci'], help='control jenkins', priority=0)
def helga_jenkins(client, channel, nick, message, cmd, args):
    username = getattr(settings, 'JENKINS_USERNAME', None)
    password = getattr(settings, 'JENKINS_PASSWORD', None)
    url = getattr(settings, 'JENKINS_URL')
    if not url:
        return 'no JENKINS_URL is configured, cannot continue'

    sub_commands = {
        # XXX commented out because they need trimming
        #'status': status,
        #'jobs': jobs,
        #'health': health,
        'builds': builds,
    }

    sub_command = args[0]

    conn = jenkins.Jenkins(url, username=username, password=password)

    return sub_commands[sub_command](conn, *args)
