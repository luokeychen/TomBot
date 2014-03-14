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
#  File        : enging.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : engine for TomBot

import logging
import re
import inspect

import zmq
from zmq.eventloop import zmqstream
import zmq.utils.jsonapi as json

from utils import make_msg
import config
import const

logger = logging.getLogger('')


def respond_handler(arg):
    '''消息响应装饰器

    :param arg: arg应是一个合法的正则表达式
    '''
    regexp = re.compile(arg, re.IGNORECASE)

    def wrapper(func):
        def __handler(*args, **kwargs):
            matches = re.match(regexp, args[1].content)
            if matches:
                logger.info(u'匹配到正则表达式: {0}'.format(matches.string))
                return func(args[0], args[1], matches)
            else:
                logger.info(u'消息被丢弃: {0}'.format(args[1].content))
                return None
        return __handler
    return wrapper


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    :param socket: pull模式的zmq socket
    '''

    #retcode: 0 normal 101 warn 102 error 1001 null
    def __init__(self, message, socket):
        self.msg = message
        self.identity = message[0]
        self.content, self.id_, self.type_ = message[1:]
        self.socket = socket

    def send(self, content, style=const.DEFAULT_STYLE, retcode=0):
        if len(content) > 4096:
            warn_msg = make_msg(1,
                                '消息过长，只显示部分内容'.encode('utf-8'),
                                self.id_, self.type_, const.WARNING_STYLE)

            self.socket.send_json(warn_msg)
            content = content[:4096]
        msg = make_msg(retcode, content, self.id_, self.type_, style)

        self.socket.send_multipart([self.identity,
                                    json.dumps(msg)])

        logging.info('推送消息到adapter: {0!r}'.format(msg))

    def warn(self, content):
        self.send(content, style=const.WARNING_STYLE, retcode=101)

    def error(self, content):
        self.send(content, style=const.ERROR_STYLE, retcode=102)

    def info(self, content):
        self.send(content, style=const.INFO_STYLE)

    def code(self, content):
        self.send(content, style=const.CODE_STYLE)


class Engine(object):
    '''
    插件应继承此类, 并定制topics

    '''
    def setup_respond_handlers(self):
        '''
        获得被respond_handler装饰的函数列表
        '''
        respond_handlers = []
        for _, handler in inspect.getmembers(self, callable):
            # FIXME 这里用装饰过的函数名来判断被装饰过的函数列表，
            # 所以自己定义的任何callable对象，不能命名为__handler
            if handler.__name__ == '__handler':
                if handler not in respond_handlers:
                    respond_handlers.append(handler)
            else:
                continue

        self.respond_handlers = respond_handlers
        logger.debug('respond handlers: {0}'.format(self.respond_handlers))

    def recv_callback(self, msg):
        '''接收消息

        :param msg: 从zmq收到的消息回调
        '''
        class_name = self.__class__.__name__
        logger.debug('{0}从backend收到消息: {1!r}'.format(class_name, msg))
        _identity = msg[0]
        msg_body = json.loads(msg[1])
        _id = msg_body.get('id')
        _content = msg_body.get('content')
        _type = msg_body.get('type')

        respond_results = {}
        for handler in self.respond_handlers:
            try:
                res = handler(Message((_identity, _content, _id, _type), self.push))
                respond_results[class_name] = res
            except Exception as e:
                logger.error('Handler处理失败')
                logger.exception(e)
                continue

        logging.info('Handler执行结果：{0}'.format(respond_results))

    def run(self, identify, socket):
        self.setup_respond_handlers()
        # context 必须在run方法里创建
        #http://lists.zeromq.org/pipermail/zeromq-dev/2013-November/023670.html
        context = zmq.Context(1)

        subscriber = context.socket(zmq.SUB)
        subscriber.connect('ipc://{0}/backend_{1}.ipc'.format(config.ipc_path,
                                                              identify))

        subscriber.setsockopt(zmq.SUBSCRIBE, '')

        self.push = socket

        logger.info('{0}脚本开始监听'.format(self.__class__.__name__))
        self.stream = zmqstream.ZMQStream(subscriber)
        self.stream.on_recv(self.recv_callback)

    def stop(self):
        self.stream.stop_on_recv()

    def waitfor(self):
        pass
