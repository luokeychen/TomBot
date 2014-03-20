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
#  File        : backend.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : TomBot Backend用于处理消息及插件

import re
import logging
import os
from multiprocessing import Process
import sys

from importlib import import_module
from threading import Thread
from inspect import isclass

import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop import zmqstream
from zmq.eventloop import ioloop
ioloop.install()

from session import Room, RoomManager
from engine import Message
from utils import make_msg
import config

_path = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger('Backend')


class BackendManager(object):
    def __init__(self):
        self.backends = []
        self.count = 0

    def add(self):
        b = Backend(self.count)
        p = Process(target=b.start)
        p.daemon = False
        p.start()
        self.backends.append(p)
        self.count += 1
        logger.debug('Backends: {0}'.format(self.backends))

    def delete(self):
        '''不允许指定删除的backend序号'''
        p = self.backends[self.count]
        p.terminate()
        self.backends.remove(self.count)
        self.count -= 1


class Backend(object):
    def __init__(self, identify):
        self.identity = identify
        self.pm = None

    def start(self):
        '''
        转发函数，订阅消息，并把正确的消息过滤完后送给scripts
        '''
        context = zmq.Context(1)
        # 所有插件都应该使用这个socket，否则会自动负载均衡，破坏逻辑
        # TODO 统一封装获取socket的函数
        self.brokersock = context.socket(zmq.DEALER)
        self.brokersock.connect('ipc://{0}/broker.ipc'.format(config.ipc_path))

        backend = context.socket(zmq.PUB)
        backend.bind('ipc://{0}/backend_{1}.ipc'.format(config.ipc_path,
                                                        self.identity))

        # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
        rm = RoomManager()

        logger.info('开始载入脚本...')
        self.pm = PluginManager(self.identity, pushsock=self.brokersock)
        self.pm.load_scripts('plugin')
        self.pm.load_scripts('ansible')
        self.pm.start()
        logger.info('脚本载入完成')
        logger.info('backend准备开始监听')

        def callback(msg):
            logging.debug('从adapter收到消息: {0}'.format(msg))
            # 处理消息信封，如果只有一层的话，那么第一帧是zmq.IDENTITY或UUID，第二帧为消息内容
            identity = msg[0]
            msg_body = json.loads(msg[1])
            #这里无需处理retcode
            _id = msg_body.get('id')
            _content = msg_body.get('content').strip()
            _type = msg_body.get('type')

            #若该房间不在字典中，则添加一个
            if not rm.get_room(_id):
                room = Room(_id)
                rm.add_room(room)
                room.rtype = _type
            else:
                room = rm.get_room(_id)

            #模式切换特殊处理
            if _content == 'tom mode cmd':
                room.mode = 'command'
                logger.info('切换到command模式')
                msg = make_msg(0,
                               'notify Tom已切换到command模式，' +
                               '所有英文开头的指令都将被当作命令执行',
                               _id, _type)
                backend.send_multipart([identity, json.dumps(msg)])
                return
            if _content == 'tom mode normal':
                room.mode = 'normal'
                logger.info('切换到normal模式')
                msg = make_msg(0,
                               'notify Tom已切换到normal模式',
                               _id, _type)
                backend.send_multipart([identity, json.dumps(msg)])
                return
            if _content == 'tom mode easy':
                room.mode = 'easy'
                logger.info('切换到easy模式')
                msg = make_msg(0, 'notify Tom已切换到easy模式，' +
                               '指令将不需要Tom前缀，但会忽略中文',
                               _id, _type)
                backend.send_multipart([identity, json.dumps(msg)])
                return

            #命令模式自动补exec让脚本能够正常处理
            if room.mode == 'command':
                #非英文开头直接忽略
                if re.compile('^[a-z]').match(_content):
                    _content = 'exec ' + _content
                else:
                    return
            elif room.mode == 'easy':
                if not re.compile('^[a-z\?]').match(_content):
                    return
            elif room.mode == 'normal':
                pattern = re.compile('^{0}'.format(config.name),
                                     flags=re.IGNORECASE)
                if pattern.match(_content):
                    _content = pattern.sub('', _content, 1).strip()
                else:
                    return
            else:
                logger.warn('无效的房间类型{0}'.format(room.mode))
            msg = make_msg(0, _content, _id, _type)
            logging.debug('发布消息给scripts: {0!r}'.format(msg))
            backend.send_multipart([identity, json.dumps(msg)])

        stream = zmqstream.ZMQStream(self.brokersock)
        stream.on_recv(callback)

        loop = ioloop.IOLoop.instance()
        try:
            loop.start()
        except KeyboardInterrupt:
            logger.info('收到退出信号，程序退出...')
            self.pushsocket.close()
            backend.close()
            context.term()
            ioloop.IOLoop.instance().stop()


class PluginManager(Thread):
    '''插件管理器'''
    def __init__(self, identity=None, pushsock=None):
        super(PluginManager, self).__init__()
        self.pushsock = pushsock
        self.identity = identity
        self.actives = {}

        self.daemon = False

    def load_scripts(self, type_):
        '''载入插件
        '''
        scripts = None
        if type_ == 'plugin':
            scripts = config.plugins
        if type_ == 'ansible':
            scripts = config.ansibles

        if scripts is None:
            return

        for plugin in scripts:
            self.run_script(plugin)

    def run_script(self, plugin):
        sys.path.append('scripts')
        sys.path.append('{0}/modules/ansible/'.format(config.home))

        try:
            m = import_module(plugin)
        except ImportError as e:
            logging.error('{0}插件载入失败，错误信息：{1}'.format(plugin, e))
            return 1

        for item in dir(m):
            attr = getattr(m, item)
            # 载入所有插件类
            if isclass(attr) and hasattr(attr, '__plugin__'):
                _instance = attr()
                #TODO multi handle class support
                self.actives[plugin] = _instance, m
                logger.info('实例化脚本{0}的{1}类...'.format(plugin, attr.__name__))

    def recv_callback(self, msg):
        logger.debug('PLUGINMANAGER收到消息:{0}'.format(msg))
        identity = msg[0]
        msg_body = json.loads(msg[1])
        id_ = msg_body.get('id')
        content = msg_body.get('content')
        type_ = msg_body.get('type')

        msg = Message((identity, content, id_, type_),
                      self.pushsock
                      )
        self.parse_command(msg)

    def parse_command(self, msg):
        logger.info('开始匹配')
        match_result = {}
        for name, (instance, module) in self.actives.iteritems():
            logger.debug('name:{0}, respond map:{1}'.format(name, module.respond.respond_map))

            for pattern, handler in module.respond.respond_map.iteritems():
                #只会执行一次，无需编译
#                 pattern = re.compile(pattern)
                matches = re.match(pattern, msg.content)
                match_result[name] = matches
                # 获取注册的函数名
                func_name = module.respond.get_respond(pattern)
                # 获取函数示例
                # FIXME 这种机制可能有问题
                func = getattr(instance, func_name)
                if matches:
                    t = Thread(target=func,
                               args=(msg, matches))
                    t.daemon = False
                    t.start()
                else:
                    msg.warn('Tom检测到您似乎输入的是一个命令，但未找到任何匹配')

        logger.info('匹配结果：{0}'.format(match_result))

    def run(self):
        context = zmq.Context(1)
        backsock = context.socket(zmq.SUB)
        backsock.setsockopt(zmq.SUBSCRIBE, '')
        backsock.connect('ipc://{0}/backend_{1}.ipc'.format(config.ipc_path,
                                                            self.identity))

        stream = zmqstream.ZMQStream(backsock)
        stream.on_recv(self.recv_callback)
