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


import json
import inspect
import sys
from Queue import Queue, Empty

from helpers import make_msg
from session import Session
import const
import log

logger = log.logger

respond_handlers = {}


def plugin(cls):
    cls.__plugin__ = True
    return cls


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    :param socket: pull模式的zmq socket
    '''

    #retcode: 0 normal 101 warn 102 error 1001 null
    def __init__(self, message, socket):
        self.msg = message
        self.identity = message[0]
        self.content, self.id_, self.type_, self.user = message[1:]
        self.socket = socket

    def send(self, content, style=const.DEFAULT_STYLE, retcode=0, user=None):
        if not content:
            content = '执行结果为空'
            style = const.ERROR_STYLE

        elif len(content) > 4096:
            warn_msg = make_msg(1,
                                '消息过长，只显示部分内容',
                                self.id_, self.type_, self.user, const.WARNING_STYLE)

            self.socket.send_multipart([self.identity,
                                        json.dumps(warn_msg)])
            content = content[:4096]
        msg = make_msg(retcode, content, self.id_, self.type_, self.user, style)

        self.socket.send_multipart([self.identity,
                                    json.dumps(msg)])

        logger.info('推送消息到adapter: {0!r}'.format(msg))

    def ok(self, content):
        self.send(content, style=const.OK_STYLE, retcode=0)

    def info(self, content):
        self.send(content, style=const.INFO_STYLE)

    def warn(self, content):
        self.send(content, style=const.WARNING_STYLE, retcode=101)

    def error(self, content):
        self.send(content, style=const.ERROR_STYLE, retcode=102)

    def code(self, content):
        self.send(content, style=const.CODE_STYLE)


class Respond(object):
    '''
    响应器，用于注册及获取响应函数
    '''
    def __init__(self):
        self.respond_map = {}
        self.plugin = self._get_caller_module()
        logger.error(self.plugin)

    def register(self, pattern):
        '''消息响应装饰器

        :param pattern: pattern应是一个合法的正则表达式
        '''
        # BUG 无法获取wrap前的函数名，functools也不行
        def wrapper(func, *args, **kwargs):
            queue = Queue(1)
            self.respond_map[pattern] = func, queue
            return func
        return wrapper

    def get_respond(self, pattern):
        func = self.respond_map.get(pattern, None)
        if func is None:
            logger.warn('未注册响应器:{0}'.format(pattern))
        else:
            return func

    # FIXME 这种方式可能导致不同Python实现的移植问题
    @staticmethod
    def _get_caller_module():
        stack = inspect.stack()
        parentframe = stack[2][0]

        module = inspect.getmodule(parentframe)

        return module

    # FIXME 这种方式可能导致不同Python实现的移植问题
    @staticmethod
    def _get_caller(skip=2):
        stack = inspect.stack()
        start = 0 + skip
        if len(stack) < start + 1:
            return ''
        parentframe = stack[start][0]
        name = None
        codename = parentframe.f_code.co_name

        if codename != '<module>': # top level usually
            name = codename
        del parentframe
        return name

    def get_input(self, msg):
#         session_id = Session.generate_session_id(msg.id_, msg.user)
        session = Session(msg.id_, msg.user)
        # get caller
        caller = self._get_caller()
        # get caller instance
        instance = inspect.currentframe().f_back.f_locals['self']
        caller = getattr(instance, caller)
        # set session
        session['iswait'] = True

        for pattern, (func, queue) in self.respond_map.items():
            if func == caller:
                session['last'] = [pattern for (pattern, func) in self.respond_map.iteritems() if func == func][0]
                session.save()
                try:
                    logger.info('服务器正在等待用户输入')
                    message = queue.get(timeout=5)
                    user_input = message.content
                    session['iswait'] = False
                    session.save()
                    return user_input
                except Empty:
                    session['iswait'] = False
                    session.save()
                    msg.send(u'输入超时，任务取消')
                    return None

        session['iswait'] = False
        session.save()
        msg.send('由于未知原因，无法读取用户输入')
