#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#  Copyright (C) 2014 konglx
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY konglx ''AS IS'' AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL konglx BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : simple_runner.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : Fri Feb 21 20:45:46 2014
#  Description : simple ansible runner for TomBot

import logging
import os
import re

import ansible.inventory

from helper.raw import raw_runner
from engine import Respond, plugin
respond = Respond()
logger = logging.getLogger(__name__)


@plugin
class SimpleRunner(object):
    '''Tom exec command    执行命令'''
    def __init__(self):
        inventory_file = os.path.split(os.path.realpath(__file__))[0] + '/inventory/hosts.conf'
        self.inventory = ansible.inventory.Inventory(inventory_file)

    @respond.register('exec (.*)')
    def handler(self, message, matches):

        accept_commands = ['uptime', 'ls', 'df', 'du', 'vmstat', 'iostat', 'netstat', 'sar',
                           'free', 'cat', 'base64', 'grep', 'find', 'id', 'which', 'whereis',
                           'locate', 'ipcs', 'locale', 'lsof', 'lsattr', 'lspci', 'lscpu', 'lspv',
                           'lsvg', 'lslv', 'vgdisplay', 'lvdisplay', 'pvdisplay', 'ps', 'pstree',
                           'ulimit', 'dmesg', 'head', 'tail', 'hostname', 'ifconfig', 'lsblk',
                           'uname', 'cd', 'pwd', 'java']

        inputs = matches.group(1)
        pattern = '*'
        if inputs.find(' on ') > 0:
            m = re.match('(.*?) on (.*)', inputs)
            logger.debug(m.groups())
            input_command = m.group(1)
            pattern = m.group(2)
        else:
            input_command = inputs
        logger.debug('input command:{0}'.format(input_command))

        for command in accept_commands:
            if re.match('(\w+)', input_command).group(1) == command:
                result = raw_runner(input_command, pattern, self.inventory)
                message.send(result)
                return
        message.error('禁止执行的命令!')
        return True
