#coding: utf-8
import logging
from abc import abstractmethod

import zmq.green as zmq
import gevent
import threading

import re

context = zmq.Context.instance()
push = context.socket(zmq.PUSH)
push.bind('ipc:///tmp/push.ipc')

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
    def __init__(self, message):
        '''message is in json
        '''
        self.msg = message
        self.content, self.id, self.type = message

    def send(self, content):
        push.send_multipart([content, self.id, self.type])
        logging.info('push message to adapter: %s', (content, self.id, self.type))

class Engine(threading.Thread):
    def __init__(self):
        super(Engine, self).__init__()
        self.setDaemon(True)
        self._http_client = None
        self.subscriber = context.socket(zmq.SUB)
#        self.subscriber.setsockopt(zmq.IDENTITY, 'Engine')
        self.subscriber.connect('ipc:///tmp/route.ipc')
        self.data = None

    def send(self, message):
        msg = Message(message)
        msg.send(message)

    # TODO 是否增加超时机制
    @abstractmethod
#    @regex('.*')
    def respond(self, message, matches):
        pass

    def add_topic(self, topic):
        self.subscriber.setsockopt(zmq.SUBSCRIBE, topic)

    def _recv(self):
        while True:
            try:
                [content, id, type] = self.subscriber.recv_multipart(zmq.NOBLOCK)
                logger.info('received data from forwarder: %s', (content, id, type))
                self.respond(Message((content, id, type)))
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    gevent.sleep(0.1)
            gevent.sleep(0.1)

    def run(self):
#        gevent.spawn(self._recv)
#        gevent.sleep(0)
        try:
            self._recv()
        except KeyboardInterrupt:
            exit(0)

    def poweroff(self):
        pass

    def http(url, callback=None):
        if not self._http_client:
            self._http_client = AsyncHTTPClient()
        self._http_client.fetch(url, callback=callback)

    def gbk2utf8(self, string):
        return string.decode('GBK').encode('UTF-8')
