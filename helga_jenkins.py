from helga.plugins import command
from helga import log, settings
import jenkins

logger = log.getLogger(__name__)


def status(conn, name):
    return conn.get_job_info(name)


def jobs(conn, *args):
    return conn.get_jobs()


@command('jenkins', aliases=['ci'], help='control jenkins', priority=0)
def helga_jenkins(client, channel, nick, message, cmd, args):
    username = getattr(settings, 'JENKINS_USERNAME')
    password = getattr(settings, 'JENKINS_PASSWORD')
    url = getattr(settings, 'JENKINS_URL')
    if not url:
        return 'no JENKINS_URL is configured, cannot continue'

    sub_commands = {
        'status': status,
        'jobs': jobs,
    }

    sub_command = args[0]

    conn = jenkins.Jenkins(url, username=username, password=password)

    return sub_commands[sub_command](conn, *args)
