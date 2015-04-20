import os
import socket
from helga.plugins import command
from helga import log, settings

logger = log.getLogger(__name__)


@command('jenkins', aliases=['ci'], help='control jenkins', priority=0)
def helga_jenkins(client, channel, nick, message, cmd, args):
    username = getattr(settings, 'JENKINS_USERNAME')
    password = getattr(settings, 'JENKINS_PASSWORD')
    pass
