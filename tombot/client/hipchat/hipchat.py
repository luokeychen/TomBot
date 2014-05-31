#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:
import json
import os
import yaml
import zmq
import threading

__author__ = 'Konglx'

from sleekxmpp import ClientXMPP
from tombot.common.log import logger


JABBER_ID = '94499_883553@chat.hipchat.com'
PASSWORD = 'jay19880821'
ROOM_ID = '94499_ffcs@conf.hipchat.com'
NICK_NAME = 'tom bot'

context = zmq.Context(1)
socket = context.socket(zmq.DEALER)
socket.setsockopt(zmq.IDENTITY, 'HipChat')
_home = os.getenv('TOMBOT_HOME')
req_socket = yaml.load(file('./hipchat.yaml'))['req_socket']
logger.debug(req_socket)
socket.connect(req_socket)


class HipChat(ClientXMPP):
    def __init__(self, jid, password):
        super(HipChat, self).__init__(jid, password)
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0004')  # Multi-User Chat backward compability (necessary for join room)
        self.register_plugin('xep_0199')  # XMPP Ping
        self.register_plugin('xep_0203')  # XMPP Delayed messages
        self.register_plugin('xep_0249')  # XMPP direct MUC invites
        self.register_plugin('xep_0060')  # PubSub

        self.auto_authorize = True
        self.auto_subscribe = True
        self.whitespace_keepalive = True
        self.whiteapace_keepalive_interval = 5

        self.ca_certs = '/etc/ssl/certs/ca-certificates.crt'

        self.add_event_handler('session_start', self.session_start)
        # self.add_event_handler('groupchat_message', self.handle_message)
        self.add_event_handler('message', self.handle_message)
        self.add_event_handler('groupchat_invite', self.auto_accept_invite)

        zmq_thread = threading.Thread(target=self.zmq_handler)
        zmq_thread.daemon = True
        zmq_thread.start()

    def auto_accept_invite(self, message):
        room = message['from']
        muc = self.plugin['xep_0045']
        muc.joinMUC(room, nick=NICK_NAME, wait=True)

        # muc.joinMUC(room, JABBER_ID, PASSWORD, wait=True)

    def session_start(self, event):
        self.get_roster()
        self.send_presence()
        # self.plugin['xep_0045'].join_room(ROOM_ID)

    def handle_message(self, message):
        type = message['type']
        if type not in ('chat', 'groupchat'):
            return
        content = message['body']
        id = unicode(message['from'])
        # xmpp only, qq is different
        user = id

        msg = {'content': content.encode('utf-8'),
               'id': id,
               'type': type,
               'user': user}
        socket.send_json(msg)
        logger.info('send message to server: {}'.format(msg))

    def zmq_handler(self):
        while True:
            message = socket.recv_json()
            # message = json.loads(message[0])
            logger.debug('hipchat receive message {}'.format(message))
            self.send_message(mto=message['id'],
                              mbody=message['content'],
                              mtype=message['type'])


if __name__ == "__main__":
    hc = HipChat(JABBER_ID, PASSWORD)
    hc.connect()
    hc.process(block=False)

