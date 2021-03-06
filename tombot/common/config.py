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
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : config.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : configurations


import os
import yaml

home = os.getenv('TOMBOT_HOME')

if not home:
    print('TOMBOT_HOME not configured, use $HOME/project/TomBot instead')
    home = os.getenv('HOME') + os.sep + 'project' + os.sep + 'TomBot'

# _path = os.path.abspath(os.path.dirname(__file__))
config_file = file('{0}/conf/config.yaml'.format(home))

try:
    yaml_dict = yaml.load(config_file)
except Exception as e:
    print('配置文件载入错误:{0}'.format(e))
    exit(1006)
version = yaml_dict.get('version')
names = yaml_dict.get('names')
main_name = 'Tom'
home = yaml_dict.get('home')

log_level = yaml_dict['backend'].get('log_level')
plugins = yaml_dict.get('user')
debug = yaml_dict['backend'].get('debug')
runners = yaml_dict.get('runners')

ipc_path = yaml_dict['backend'].get('ipc_path')
server_socket = yaml_dict['backend'].get('server_socket')
use_tcp = yaml_dict['backend'].get('use_tcp')

use_proxy = yaml_dict.get('use_proxy')
proxy_host = yaml_dict.get('proxy_host')
proxy_port = yaml_dict.get('proxy_port')

default_mode = yaml_dict['backend'].get('default_mode')
hide_restrict_command = yaml_dict['backend'].get('hide_restrict_command')
backend_count = yaml_dict['backend'].get('workers')
capture = yaml_dict['broker'].get('capture')

max_message_size = yaml_dict['backend'].get('max_message_size')

plugin_dirs = yaml_dict['plugin'].get('plugin_dirs')
# TODO make possible to assign multiple plugin dir
# plugin_dirs.append('user')
# plugin_dirs = ['/home/konglx/project/TomBot/tombot/user']

admins = yaml_dict['backend'].get('admins') or 'konglx'
prefix = yaml_dict['backend'].get('prefix') or '!'
bot_alt_separators = yaml_dict['backend'].get('bot_alt_separators')

#TODO generate md5 string and save it to file after first start
admin_pass = 'test'
