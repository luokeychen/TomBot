#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description: collect all rest here
import tornado

__author__ = 'Konglx'

from tornado.web import asynchronous
from tornado.web import RequestHandler
from tornado.web import Application
from tornado.httpserver import HTTPServer
from tornado.escape import json_decode
import tornado.ioloop

from tombot.common import log
from tombot.common.version import BOT_VERSION
from tombot.brain.engine import Message
from tombot.rest.webproxy import WebProxy


logger = log.logger


class MainHandler(RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(MainHandler, self).__init__(application, request, **kwargs)
        global proxy
        proxy = WebProxy(self)

        def recv_callback(message):
            logger.debug('API message:{0}'.format(message))
            msg = json_decode(message[0])
            proxy.request.write(msg['content'])
            proxy.request.finish()

        proxy.stream.on_recv(recv_callback)

    def get(self, *args, **kwargs):
        self.finish("Tom's API server is running.")


class VersionHandler(MainHandler):
    @asynchronous
    def get(self, *args, **kwargs):
        response = {
            'version': BOT_VERSION
        }
        self.finish(response)


class SendHandler(MainHandler):
    @asynchronous
    def post(self, *args, **kwargs):
        msg = json_decode(self.request.body)
        msg_obj = Message(msg)
        msg_obj.send(msg_obj.content)


class ChatHandler(MainHandler):
    @asynchronous
    def post(self, *args, **kwargs):
        msg = json_decode(self.request.body)
        proxy.send(msg)

    @asynchronous
    def get(self, *args, **kwargs):
        self.finish('this is the URL for chat api.')


def start_api_server():
    app = Application([
        (r'/', MainHandler),
        (r'/send', SendHandler),
        (r'/chat', ChatHandler),
        (r'/version', VersionHandler)
    ])

    api_server = HTTPServer(app)
    api_server.listen('8000')
    loop = tornado.ioloop.IOLoop.current()
    try:
        loop.start()
    except Exception as e:
        logger.exception(e)


def threaded_api_server():
    import threading

    t = threading.Thread(target=start_api_server)
    t.daemon = True
    t.start()