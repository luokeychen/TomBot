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
import os
from multiprocessing import Process
from functools import partial

import zmq
import zmq.utils.jsonapi as json
from zmq.eventloop import zmqstream
from zmq.eventloop import ioloop
ioloop.install()

from session import Room, RoomManager, Session
from plugin import PluginManager
from engine import Message
from helpers import make_msg
import config
import log

_path = os.path.abspath(os.path.dirname(__file__))

logger = log.logger


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
        self.rm = None

    def create_room(self, rid, rtype):
        #若该房间不在字典中，则添加一个
        if not self.rm.get_room(rid):
            room = Room(rid)
            self.rm.add_room(room)
            room.rtype = rtype
        else:
            room = self.rm.get_room(rid)

        return room

    def start(self):
        '''
        转发函数，订阅消息，并把正确的消息过滤完后送给scripts
        '''
        context = zmq.Context(1)
        # 所有插件都应该使用这个socket，否则会自动负载均衡，破坏逻辑
        # TODO 统一封装获取socket的函数,合理的命名
        self.brokersock = context.socket(zmq.DEALER)
        self.brokersock.connect('ipc://{0}/broker.ipc'.format(config.ipc_path))

        # 经过改造，这里只有一对连接了，可以换成其他的模式
        backend = context.socket(zmq.PUB)
        backend.bind('ipc://{0}/backend_{1}.ipc'.format(config.ipc_path,
                                                        self.identity))

        # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
        self.rm = RoomManager()

        logger.info('开始载入脚本...')
        self.pm = PluginManager(self.identity, pushsock=self.brokersock)
        self.pm.load_scripts('plugin')
        self.pm.load_scripts('ansible')
        self.pm.backend = self
        self.pm.start()
        logger.info('脚本载入完成')
        logger.info('backend准备开始监听')

        def _special_hack():
            '''特殊情况处理'''
            pass

        def _change_mode(content, room):
            #模式切换特殊处理
            msg = None
            if content == 'tom mode cmd':
                room.mode = 'command'
                logger.info('切换到command模式')

                msg = self.make_simple_msg(content='notify Tom已切换到command模式，' +
                                    '所有英文开头的指令都将被当作命令执行')

            if content == 'tom mode normal':
                room.mode = 'normal'
                logger.info('切换到normal模式')
                msg = self.make_simple_msg(content='notify Tom已切换到normal模式')

            if content == 'tom mode easy':
                room.mode = 'easy'
                logger.info('切换到easy模式')
                msg = self.make_simple_msg(content='notify Tom已切换到easy模式，' +
                                    '指令将不需要Tom前缀，但会忽略中文')
            return msg

        def callback(msg):
            logger.debug('从adapter收到消息: {0}'.format(msg))
            # 处理消息信封，如果只有一层的话，那么第一帧是zmq.IDENTITY或UUID，第二帧为消息内容
            identity = msg[0]
            try:
                msg_body = json.loads(msg[1])
            except ValueError:
                logger.error('JSON格式错误！')
                return
            #这里无需处理retcode
            _id = msg_body.get('id')
            _content = msg_body.get('content').strip()
            _type = msg_body.get('type')
            _user = msg_body.get('user')
            self.make_simple_msg = partial(make_msg, retcode=0, id_=_id, type_=_type, user=_user)

            room = self.create_room(_id, _type)
            # 赋一个空的message对象，用来发送消息
            room.message = Message((identity, None, _id, _type, _user), self.brokersock)

#             user = room.users.setdefault(_user, User(_user))
            # NOTE 当需要写session时，必须创建对象
            session = Session(_id, _user)
            session['history'].append(_content)
            session.save()
            logger.debug('backend session:{0}'.format(session._data))
            if session['iswait']:
                msg = self.make_simple_msg(content=_content)
                logger.debug('发送用户输入消息给scripts: {0!r}'.format(msg))
                backend.send_multipart([identity, json.dumps(msg)])
                return

            change_msg = _change_mode(_content, room)

            if change_msg:
                backend.send_multipart([identity, json.dumps(change_msg)])
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
            msg = self.make_simple_msg(content=_content)
            logger.debug('发布消息给scripts: {0!r}'.format(msg))
            backend.send_multipart([identity, json.dumps(msg)])

        stream = zmqstream.ZMQStream(self.brokersock)
        stream.on_recv(callback)

        loop = ioloop.IOLoop.instance()

        try:
            loop.start()
        except KeyboardInterrupt:
            logger.info('收到退出信号，程序退出...')
            self.brokersock.close()
            backend.close()
            context.term()
            ioloop.IOLoop.instance().stop()
