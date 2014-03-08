#!/usr/bin/env python
# coding: utf-8
#
#   Author  :   konglx
#   E-mail  :   jayklx@gmail.com
#   Date    :   2014-02-05 18:31:22
#   Desc    :   qq adapter for TomBot
#
'''
    usage:
        python qq.py [qq] [password]
'''
import geventhttpclient.httplib
geventhttpclient.httplib.patch()
import logging
import zmq
from zmq.eventloop import zmqstream, ioloop

import sys
import os
sys.path.append('./twqq')
from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler, discu_message_handler
from twqq.requests import buddy_message_handler, kick_message_handler


logger = logging.getLogger('client')
ioloop.install()

context = zmq.Context(1)
pub = context.socket(zmq.PUB)
_home = os.getenv('TOMBOT_HOME')
# pub.connect('ipc://{0}/run/publish.ipc'.format(_home))
pub.connect('tcp://192.168.3.107:4445')
pull = context.socket(zmq.PULL)
# pull.connect('ipc://{0}/run/push.ipc'.format(_home))
pull.connect('tcp://192.168.3.107:4444')


class Client(WebQQClient):
    def handle_verify_code(self, path, r, uin):
        logger.info(u'验证码本地路径为: {0}'.format(path))
        check_code = None
        while not check_code:
            check_code = raw_input(u'输入验证码: ')
        self.enter_verify_code(check_code, r, uin)

    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == 'verify_required':
            self.hub.accept_verify(from_uin, account, account)

    @discu_message_handler
    def handle_discu_message(self, did, from_uin, content, source):
        pub.send_multipart([content.encode('utf-8'), str(did), 'discu'])

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        pub.send_multipart([content.encode('utf-8'), str(group_code), 'group'])

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        pub.send_multipart([content.encode('utf-8'), str(from_uin), 'buddy'])

    @kick_message_handler
    def handle_kick(self, message):
        self.hub.relogin()


if __name__ == '__main__':
    import sys
    import tornado.log

    tornado.log.enable_pretty_logging()

    webqq = Client(int(sys.argv[1]), sys.argv[2])

    def zmq_handler(msg):
        _content, _id,  _type = msg
        _content = _content.decode('utf-8')
        if _type == 'buddy':
            webqq.hub.send_buddy_msg(int(_id), _content)
        elif _type == 'group':
            webqq.hub.send_group_msg(int(_id), _content)
        elif _type == 'discu':
            webqq.hub.send_discu_msg(int(_id), _content)
        else:
            logger.error('zmq message format error')

    stream = zmqstream.ZMQStream(pull)
    stream.on_recv(zmq_handler)

    webqq.run()

