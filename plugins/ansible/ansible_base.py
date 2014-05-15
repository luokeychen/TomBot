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
from common import inventory


class AnsibleBase(AnsibleEngine):
    """Commands for basic Ansible controls"""

    @botcmd
    def list_host(self, message, args):
        """List hosts with group configured in Ansible inventory file"""
        message.info(self.print_hosts())

    def print_hosts(self):
        groups = inventory.get_groups()
        hosts_list = []
        for group in groups:
            hosts_list.append('***{0}***'.format(group.name))
            [hosts_list.append(' ' + host.name) for host in group.hosts]
        return '\n'.join(hosts_list)

    @botcmd
    def list_group(self, message, args):
        """List group configured in Ansible inventory file"""
        message.info('\n'.join([group.name for group in inventory.get_groups()]))
