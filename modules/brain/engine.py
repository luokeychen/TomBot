# coding: utf-8
import logging
import os
from abc import abstractmethod

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream
import threading

import re


_home = os.getenv('TOMBOT_HOME')
_push_ipc_file = 'ipc://{0}/run/push.ipc'.format(_home)
_route_ipc_file = 'ipc://{0}/run/route.ipc'.format(_home)

logger = logging.getLogger('')
def regex(arg):
    arg = arg.encode('utf-8')
    regexp = re.compile(arg, re.I)
    def _regex(func):
        def __regex(*args, **kwargs):
            matches = re.match(regexp, args[1].content)
            return func(args[0], args[1], matches)
        return __regex
    return _regex

class Message(object):
    def __init__(self, message, socket):
        '''message is in json
        '''
        self.msg = message
        self.content, self.id, self.type = message
        self.socket = socket

    def send(self, content):
        self.socket.send_multipart([content, self.id, self.type])
        logging.debug('push message to adapter: {0}'.format((content, self.id, self.type)))

class Engine(object):
    '''
    插件应继承此类，并重写respond方法'''

    def __init__(self):
        self.topics = []

    # TODO 是否增加超时机制
    @abstractmethod
#    @regex('.*')
    def respond(self, message, matches):
        pass

    def _recv(self, msg):
        try:
            [_content, _id, _type] = msg
            logger.debug('received data from forwarder: {0}'.format((_content, _id, _type)))
            self.respond(Message((_content, _id, _type), self.push))
        except zmq.ZMQError as e:
            logger.error(e)
        except Exception as e:
            logger.error('异常了！！！')
            logger.error(e)

    def run(self):
        ioloop.install()
        # context 必须在run方法里创建
        # http://lists.zeromq.org/pipermail/zeromq-dev/2013-November/023670.html
        context = zmq.Context()
        self.push = context.socket(zmq.PUSH)
        self.push.connect(_push_ipc_file)

        subscriber = context.socket(zmq.SUB)
#        self.subscriber.setsockopt(zmq.IDENTITY, 'Engine')
        subscriber.connect(_route_ipc_file)
        stream = zmqstream.ZMQStream(subscriber)
        stream.on_recv(self._recv)

        for topic in self.topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, topic)

        loop = ioloop.IOLoop.instance()
#        loop.make_current()
        logger.info('{0}脚本开始监听'.format(self.__class__.__name__))
        loop.start()

    @staticmethod
    def run_in_thread(target=None, args=()):
        t = threading.Thread(target=target, args=args)
        t.daemon = True
        t.start()

    def poweroff(self):
        pass

    @staticmethod
    def gbk2utf8(string):
        return string.decode('GBK').encode('UTF-8')

