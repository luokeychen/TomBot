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
import logging
import yaml


_path = os.path.abspath(os.path.dirname(__file__))
config_file = file('{0}/../../conf/config.yaml'.format(_path))

logger = logging.getLogger('')

try:
    yaml_dict = yaml.load(config_file)
except Exception:
    logger.error('配置文件载入错误！')
    exit(1006)
name = yaml_dict.get('name')
home = yaml_dict.get('home')

log_level = yaml_dict.get('log_level')
plugins = yaml_dict.get('plugins')
debug = yaml_dict.get('debug')
ansibles = yaml_dict.get('ansibles')

ipc_path = yaml_dict.get('ipc_path')
sub_socket = yaml_dict.get('sub_socket')
push_socket = yaml_dict.get('push_socket')
use_tcp = yaml_dict.get('use_tcp')

use_proxy = yaml_dict.get('use_proxy')
proxy_host = yaml_dict.get('proxy_host')
proxy_port = yaml_dict.get('proxy_port')

default_mode = yaml_dict.get('default_mode')
