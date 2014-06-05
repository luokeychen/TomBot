#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:

__author__ = 'Konglx'

import os
import ansible.inventory
import logging

from tombot.common import config


inventory_file = os.path.split(os.path.realpath(__file__))[0] + '/inventory/hosts.conf'
inventory = ansible.inventory.Inventory(inventory_file)


def get_all_playbooks():
    playbook_dir = config.home + '/plugins/ansible/playbooks/'
    subdirs = os.walk(playbook_dir).next()[1]
    logging.debug('subdirs : {}'.format(subdirs))
    playbooks = {pb: {'path': playbook_dir + os.sep + pb + os.sep + 'site.yml'} for pb in subdirs}
    for pb in playbooks:
        try:
            fp = file(playbook_dir + pb + os.sep + 'hosts')
            playbooks[pb]['hosts'] = playbook_dir + pb + os.sep + 'hosts'
        except IOError as _:
            playbooks[pb]['hosts'] = None
    return playbooks

