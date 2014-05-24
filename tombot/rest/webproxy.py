#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:

__author__ = 'Konglx'

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream


class WebProxy(object):
    def __init__(self, request):
        context = zmq.Context(1)
        self.dealer = context.socket(zmq.DEALER)
        self.dealer.setsockopt(zmq.IDENTITY, 'WEBPROXY')
        self.dealer.connect('tcp://127.0.0.1:4445')

        self.request = request

        # self.loop = IOLoop.current()
        self.stream = ZMQStream(self.dealer)

    def add_callback(self, callback, *args, **kwargs):
        self.loop.add_callback(callback, args, kwargs)

    def on_recv(self, callback):
        self.stream.on_recv(callback)

    def send(self, json_msg):
        self.dealer.send_json(json_msg)
