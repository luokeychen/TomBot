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
#  File        : shell.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-29
#  Description : shell client


import os
import sys
import zmq
import threading

_home = os.getenv('TOMBOT_HOME')
_prompt = 'TomBot> '

context = zmq.Context(1)
dealer = context.socket(zmq.DEALER)
dealer.setsockopt(zmq.IDENTITY, 'SHELL')
dealer.connect('tcp://127.0.0.1:4445')


class Shell(object):
    def __init__(self):
        self.lock = True

    def prompt(self):
        user_input = raw_input(_prompt)
        if user_input == 'exit':
            sys.exit(0)
        elif user_input == '':
            self.lock = True
        else:
            _ = ' '
            msg = dict(content=user_input,
                       type=_,
                       id='1',
                       user='222'
                       )
            dealer.send_json(msg)

    def run(self):

        t = threading.Thread(target=self.recv)
        t.daemon = True
        t.start()

        while True:
            if self.lock:
                self.lock = False
                try:
                    self.prompt()
                except KeyboardInterrupt:
                    pass
                except EOFError:
                    sys.exit(0)

    def recv(self):
        while True:
            msg = dealer.recv_json()
            self.zmq_handler(msg)
            self.lock = True

    def zmq_handler(self, msg):
        _content = msg.get('content')
        print(_content)


if __name__ == '__main__':
    shell = Shell()
    shell.run()
