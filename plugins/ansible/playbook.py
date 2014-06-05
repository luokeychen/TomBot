# coding=utf-8

from ansible import playbook
from ansible import callbacks
from ansible import utils

import common
from tombot import botcmd
from tombot import AnsibleEngine
from tombot import log


logger = log.logger


class PlayBook(AnsibleEngine):
    all_playbooks = common.get_all_playbooks()

    @botcmd
    def playbook_run(self, message, args):
        """Run a playbook"""
        if isinstance(args, str) or isinstance(args, unicode):
            arg = args
        elif isinstance(args, list):
            arg = args[0]
        else:
            message.error('参数类型错误')
            return
        message.send('Starting to execute playbook: {}'.format(arg))
        pb_dict = self.all_playbooks[arg]
        stats = callbacks.AggregateStats(),
        runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
        if pb_dict['hosts']:
            pb = playbook.PlayBook(playbook=pb_dict['path'],
                                   host_list=pb_dict['hosts'],
                                   stats=stats,
                                   callbacks=callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY),
                                   runner_callbacks=runner_cb
            )
        else:
            pb = playbook.PlayBook(playbook=pb_dict['path'], inventory=common.inventory)
        results = pb.run()

        return results

    @botcmd
    def playbook_install(self, message, args):
        """Install playbook from Github"""
        pass
