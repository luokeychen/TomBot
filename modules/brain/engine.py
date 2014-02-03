#coding: utf-8
import logging

import zmq.green as zmq
import gevent

import re

context = zmq.Context.instance()
push = context.socket(zmq.PUSH)
push.bind('ipc:///tmp/push.ipc')

logger = logging.getLogger('')
def regex(arg):
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

class Engine(object):
    def __init__(self):
        self._http_client = None
        self.subscriber = context.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.IDENTITY, 'Engine')
        self.subscriber.connect('ipc:///tmp/route.ipc')
        self.data = None

    def send(self, message):
        msg = Message(message)
        msg.send(message)

    # TODO 是否增加超时机制
    @regex('.*')
    def respond(self, message, matches):
        pass

    def add_topic(self, topic):
        self.subscriber.setsockopt(zmq.SUBSCRIBE, topic)

    def _recv(self):
        while True:
            [content, id, type] = self.subscriber.recv_multipart()
            logger.info('received data from forwarder: %s', (content, id, type))
            # response 可能是一个耗时的任务，因此单独spawn出来去执行
            gevent.spawn(self.respond, Message((content, id, type)))

    def run(self):
        gevent.spawn(self._recv)
#        self._recv()

    def poweroff(self):
        pass

    def http(url, callback=None):
        if not self._http_client:
            self._http_client = AsyncHTTPClient()
        self._http_client.fetch(url, callback=callback)
