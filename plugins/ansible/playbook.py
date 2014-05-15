# coding=utf-8

from ansible import playbook

from tombot import botcmd
from tombot import AnsibleEngine
from tombot import log

logger = log.logger


class PlayBook(AnsibleEngine):
    @botcmd
    def playbook_run(self, message, args):
        """Run a playbook"""
        logger.debug(type(args))
        if isinstance(args, str) or isinstance(args, unicode):
            arg = args
        elif isinstance(args, list):
            arg = args[0]
        else:
            message.error('参数类型错误')
            return
        message.send('Starting to execute playbook: {}'.format(arg))
        pb = playbook.PlayBook(playbook=arg)
        pb.basedir = 'playbooks'
        pb.check = True
        results = pb.run()

        return results

    @botcmd
    def playbook_install(self, message, args):
        """Install playbook from Github"""
        pass
