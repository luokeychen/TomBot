# coding: utf-8
import logging
import re
from abc import abstractmethod

import inspect

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream
import threading

from router import config

logger = logging.getLogger('')


def respond_handler(arg):
    '''消息响应装饰器

    '''
    arg = arg.encode('utf-8')
    regexp = re.compile(arg, re.I)
    def _handler(func):
        def __handler(*args, **kwargs):
            matches = re.match(regexp, args[1].content)
            if matches:
                return func(args[0], args[1], matches)
            else:
                return None
        return __handler
    return _handler


class Message(object):
    '''包装消息，方便保存上下文
    
    :param message: 消息tuple
    '''
    def __init__(self, message, socket):
        self.msg = message
        self.content, self.id, self.type = message
        self.socket = socket

    def send(self, content):
        self.socket.send_multipart([content, self.id, self.type])
        logging.debug('推送消息到adapter: {0}'.format((content, self.id, self.type)))

class Engine(object):
    '''
    插件应继承此类

    '''

    def __init__(self):
        self.topics = []

    def setup_respond_handlers(self):
        '''
        获得被respond_handler装饰的函数列表
        '''
        respond_handlers = []
        for _, handler in inspect.getmembers(self, callable):
            # 这里用装饰过的函数名来判断被装饰过的函数列表，所以自己定义的任何callable对象，不能命名为__handler, 这个方式比较难看，不过挺管用。。。
            if handler.__name__ == '__handler':
                if handler not in respond_handlers:
                    respond_handlers.append(handler)
            else:
                continue

        self.respond_handlers = respond_handlers
        logger.debug('respond handlers: {0}'.format(self.respond_handlers))

    def _recv(self, msg):
        '''接收消息
        
        '''
        try:
            [_content, _id, _type] = msg
            logger.debug('从router收到消息: {0}'.format((_content, _id, _type)))
            for handler in self.respond_handlers:
                handler(Message((_content, _id, _type), self.push))
        except zmq.ZMQError as e:
            logger.error(e)
#        except Exception as e:
#            logger.error(e)

    def run(self):
        self.setup_respond_handlers()
        ioloop.install()
        # context 必须在run方法里创建
        # http://lists.zeromq.org/pipermail/zeromq-dev/2013-November/023670.html
        context = zmq.Context()
        self.push = context.socket(zmq.PUSH)
        self.push.connect('ipc://{0}/push.ipc'.format(config.ipc_path))

        subscriber = context.socket(zmq.SUB)
        subscriber.connect('ipc://{0}/route.ipc'.format(config.ipc_path))
        stream = zmqstream.ZMQStream(subscriber)
        stream.on_recv(self._recv)

        for topic in self.topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, topic)

        loop = ioloop.IOLoop.instance()
        logger.info('{0}脚本开始监听'.format(self.__class__.__name__))
        loop.start()

