#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:

__author__ = 'Konglx'

from tombot import botcmd
from tombot import AnsibleEngine
from raw import raw_runner
from common import inventory


class AnsibleBase(AnsibleEngine):
    """Commands for basic Ansible controls"""

    @botcmd
    def list_host(self, message, args):
        """List hosts with group configured in Ansible inventory file"""
        message.info(self.print_hosts(args))

    def print_hosts(self, pattern=None):
        groups = inventory.get_groups()
        if pattern:
            groups = [inventory.get_group(pattern)]
        hosts_list = []
        for group in groups:
            hosts_list.append('---- {0} ----'.format(group.name))
            if not group.hosts:
                hosts_list.append('No host in this group')
                continue
            [hosts_list.append('Host: ' + host.name + '    [Port: {0} User: {1}]'.format(host.vars['ansible_ssh_port'],
                                                                                         host.vars['ansible_ssh_user']))
             for
             host in group.hosts]
        return '\n'.join(hosts_list)

    @botcmd
    def list_group(self, message, args):
        """List group configured in Ansible inventory file"""
        message.info('\n'.join([group.name for group in inventory.get_groups()]))

    @botcmd
    def cmd(self, message, args):
        """Command to run simple command on configured ansible hosts"""
        accept_commands = ['uptime', 'ls', 'df', 'du', 'vmstat', 'iostat', 'netstat', 'sar',
                           'free', 'cat', 'base64', 'grep', 'find', 'id', 'which', 'whereis',
                           'locate', 'ipcs', 'locale', 'lsof', 'lsattr', 'lspci', 'lscpu', 'lspv',
                           'lsvg', 'lslv', 'vgdisplay', 'lvdisplay', 'pvdisplay', 'ps', 'pstree',
                           'ulimit', 'dmesg', 'head', 'tail', 'hostname', 'ifconfig', 'lsblk',
                           'uname', 'cd', 'pwd', 'java']

        if not len(args):
            from pprint import pformat

            return '参数错误,请输入以下命令之一：\n{0}'.format(pformat(accept_commands))
        pattern = '*'
        if args.find(' on ') > 0:
            m = re.match(r'(.*?) on (.*)', args)
            input_command = m.group(1)
            pattern = m.group(2)
        else:
            input_command = args

        if args.split()[0] in accept_commands:
            result = raw_runner(input_command, pattern, inventory)
            return result
        else:
            return '禁止执行的命令!'
