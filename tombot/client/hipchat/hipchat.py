#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:
import json
import os
import re
from urllib import urlencode
from urllib2 import Request, urlopen
import yaml
import zmq
import threading
from tombot.common.utils import REMOVE_EOL, utf8, mess_2_embeddablehtml

__author__ = 'Konglx'

from sleekxmpp import ClientXMPP
from hypchat import HypChat
from tombot.common.log import logger
from tornado.web import escape

# hipchat automatically sent history unless JID resource is bot
JABBER_ID = '94499_883553@chat.hipchat.com/bot'
PASSWORD = 'jay19880821'
ROOM_ID = '94499_ffcs@conf.hipchat.com'
NICK_NAME = 'tom bot'

HIPCHAT_FORCE_PRE = re.compile(r'<body>', re.I)
HIPCHAT_FORCE_SLASH_PRE = re.compile(r'</body>', re.I)
HIPCHAT_EOLS = re.compile(r'</p>|</li>', re.I)
HIPCHAT_BOLS = re.compile(r'<p [^>]+>|<li [^>]+>', re.I)

HIPCHAT_MESSAGE_URL = 'https://api.hipchat.com/v1/rooms/message'
TOKEN = 'DZttvKCWeU4GpXxoqwJc4IG8bH636MjaCmLNZqc8'


def xhtml2hipchat(xhtml):
    # Hipchat has a really limited html support
    retarded_hipchat_html_plain = REMOVE_EOL.sub('', xhtml)  # Ignore formatting
    retarded_hipchat_html_plain = HIPCHAT_EOLS.sub('<br/>',
                                                   retarded_hipchat_html_plain)  # readd the \n where they probably fit best
    retarded_hipchat_html_plain = HIPCHAT_BOLS.sub('', retarded_hipchat_html_plain)  # zap every tag left
    retarded_hipchat_html_plain = HIPCHAT_FORCE_PRE.sub('<body><pre>', retarded_hipchat_html_plain)  # fixor pre
    retarded_hipchat_html_plain = HIPCHAT_FORCE_SLASH_PRE.sub('</pre></body>',
                                                              retarded_hipchat_html_plain)  # fixor /pre
    return retarded_hipchat_html_plain


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
        # self.register_plugin('xep_0071')

        self.auto_authorize = True
        self.auto_subscribe = True
        self.whitespace_keepalive = True
        self.whitespace_keepalive_interval = 60
        self.end_session_on_disconnect = False

        self.ca_certs = '/etc/ssl/certs/ca-certificates.crt'

        self.add_event_handler('session_start', self.session_start)
        self.add_event_handler('message', self.handle_message)
        self.add_event_handler('groupchat_invite', self.auto_accept_invite)

        zmq_thread = threading.Thread(target=self.zmq_handler)
        zmq_thread.daemon = True
        zmq_thread.start()

        self.rooms = []

        self.api_conn = HypChat(TOKEN)

        self.rooms_in_hipchat = self.api_conn.rooms(expand='items')

        with file('./rooms.json', 'r') as fp:
            try:
                self.rooms = json.load(fp)
            except ValueError as _:
                self.rooms = []

        self.recovery_rooms_on_startup(self.rooms)

    def send_api_message(self, room_id, fr, message, message_format='html'):
        base = {'format': 'json', 'auth_token': self.token}
        red_data = {'room_id': room_id, 'from': fr, 'message': utf8(message), 'message_format': message_format}
        req = Request(url=HIPCHAT_MESSAGE_URL + '?' + urlencode(base), data=urlencode(red_data))
        return json.load(urlopen(req))

    def recovery_rooms_on_startup(self, rooms):
        for room in rooms:
            muc = self.plugin['xep_0045']
            muc.joinMUC(room, nick=NICK_NAME, wait=True)

    def auto_accept_invite(self, message):
        room = message['from']
        muc = self.plugin['xep_0045']
        muc.joinMUC(room, nick=NICK_NAME, wait=True)
        self.rooms.append(str(room))
        logger.debug('Rooms: {}'.format(self.rooms))
        with open('./rooms.json', 'w') as fp:
            json.dump(self.rooms, fp)

    def session_start(self, event):
        self.get_roster()
        self.send_presence()

    def handle_message(self, message):
        type = message['type']
        if type not in ('chat', 'groupchat'):
            return
        content = message['body']
        message['from'] = re.sub(r'/.*$', '', str(message['from']))
        id = str(message['from'])
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
            # xmppmsg = self.Message()
            message = socket.recv_json()
            # message = json.loads(message[0])
            if message['html']:
                logger.debug('hipchat receive html message {}'.format(message))
                # content = xhtml2hipchat(message['html'])
                room = self.get_room_by_jid(message['id'])
                content = message['content']
                room.notification(content, color='random', notify=True, format='html')
            else:
                logger.debug('hipchat receive message {}'.format(message))
                self.send_message(mto=message['id'],
                                  mbody=message['content'],
                                  mtype=message['type'])

    def get_room_by_jid(self, room_jid):
        for r in self.rooms_in_hipchat['items']:
            if r['xmpp_jid'] == room_jid:
                return r
        return None


if __name__ == "__main__":
    hc = HipChat(JABBER_ID, PASSWORD)
    hc.connect()
    hc.process(block=False)

