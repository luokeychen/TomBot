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
#  are those of the authors and should not be interpreted as representing                                                                                   
#  official policies, either expressedor implied, of konglx.
#
#  File        : simple_runner.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : Fri Feb 21 20:45:46 2014
#  Description : simple ansible runner for TomBot

import ansible.runner
import ansible.inventory
import sys
import os

from engine import Engine, respond_handler


class SimpleRunner(Engine):
    '''Tom exec command    执行命令'''
    def __init__(self):
        self.topics = ['exec']
        inventory_file = os.path.split(os.path.realpath(__file__))[0] + '/inventory/hosts.conf'
        self.inventory = ansible.inventory.Inventory(inventory_file)

# construct the ansible runner and execute on all hosts
    @respond_handler('exec (.*)$')
    def handler(self, message, matches):

        accept_commands = ['uptime', 'ls', 'df', 'du', 'vmstat', 'iostat', 'netstat', 'sar',
                           'free', 'cat', 'base64', 'grep', 'find', 'id', 'which', 'whereis',
                           'locate', 'ipcs', 'locale', 'lsattr', 'lspci', 'lscpu', 'lspv',
                           'lsvg', 'lslv', 'vgdisplay', 'lvdisplay', 'pvdisplay', 'ps', 'pstree',
                           'ulimit', 'dmesg', 'head', 'tail', 'hostname', 'ifconfig', 'lsblk',
                           'uname']

        for command in accept_commands:
            if command in matches.group(1):
                runner = ansible.runner.Runner(
                    pattern='*',
                    timeout=5,
                    module_name='command',
                    module_args=matches.group(1),
        #            remote_user='temp',
                    inventory=self.inventory
                )
                results = runner.run()

                if results is None:
                    print "No hosts found"
                    sys.exit(1)

                for (hostname, result) in results['contacted'].items():
                    if not 'failed' in result:
                        print "%s >>> %s" % (hostname, result['stdout'])
                        message.send('[{0}] result==>\n{1}'.format(hostname, result['stdout']))

                for (hostname, result) in results['contacted'].items():
                    if 'failed' in result:
                        print "%s >>> %s" % (hostname, result['msg'])
                        message.send('{0}, result:\n{1}'.format(hostname, result['msg']))

                for (hostname, result) in results['dark'].items():
                    print "%s >>> %s" % (hostname, result)
                    message.send('{0}, result:\n{1}'.format(hostname, result))
                return 0

        message.send('禁止执行的命令!')
        return 1
        
