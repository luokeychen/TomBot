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
#  File        : broker.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-14
#  Description : 消息转发中间件

import threading
import zmq
import zmq.auth

from tombot.common import config


def main():
    try:
        #adapter to backend
        context = zmq.Context(1)

        capture = context.socket(zmq.PUSH)
        capture.bind('ipc://{0}/capture.ipc'.format(config.ipc_path))

        frontend = context.socket(zmq.ROUTER)
        frontend.bind(config.server_socket)

        if zmq.zmq_version_info() < (4, 0):
            print('WARNING: ZMQ version must be higher than 4.0 for security communication')

            # configure CURVE security
        #         auth_thread = ThreadAuthenticator(context=context, log=logger)
        #         auth_thread.configure_curve(location=config.home + '/certs')
        #         auth_thread.start()

        backend = context.socket(zmq.DEALER)
        backend.bind('ipc://{0}/broker.ipc'.format(config.ipc_path))

        t = threading.Thread(target=zmq.proxy, args=(frontend,
                                                     backend,
                                                     capture))
        t.daemon = False
        t.start()

        debug_socket = context.socket(zmq.PULL)
        debug_socket.connect('ipc://{0}/capture.ipc'.format(config.ipc_path))

        while True:
            msg = debug_socket.recv()
            print(msg)

    except KeyboardInterrupt:
        #         auth_thread.stop()
        frontend.close()
        backend.close()
        capture.close()
        context.term()
        exit(0)


if __name__ == '__main__':
    main()
