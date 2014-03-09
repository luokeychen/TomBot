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
import json
from zmq.eventloop import zmqstream, ioloop

import sys
import os
sys.path.append('./twqq')
from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler, discu_message_handler
from twqq.requests import buddy_message_handler, kick_message_handler, register_request_handler, PollMessageRequest


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
        msg = {'content': content.encode('utf-8'),
               'id': str(did),
               'type': 'discu'}
        pub.send_json(msg)

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        msg = {'content': content.encode('utf-8'),
               'id': str(group_code),
               'type': 'group'}
        pub.send_json(msg)

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        msg = {'content': content.encode('utf-8'),
               'id': str(from_uin),
               'type': 'buddy'}
        pub.send_json(msg)

    @kick_message_handler
    def handle_kick(self, message):
        self.hub.relogin()

    @register_request_handler(PollMessageRequest)
    def handle_qq_errcode(self, request, resp, data):
        if data and data.get("retcode") in [100006]:
            logger.error(u"获取登出消息 {0!r}".format(data))
            self.hub.relogin()

        if data and data.get("retcode") in [103]:  # 103重新登陆不成功, 暂时退出
            logger.error(u"获取登出消息 {0!r}".format(data))
            exit()


if __name__ == '__main__':
    import sys
    import tornado.log

    tornado.log.enable_pretty_logging()

    webqq = Client(int(sys.argv[1]), sys.argv[2])
    webqq.hub.http.fetch_kwargs = {}

    def zmq_handler(msg):
        msg_body = json.loads(msg[0])
        logger.info('adapter收到消息：{0}'.format(msg_body))
        _content = msg_body.get('content')
        _id = msg_body.get('id')
        _style = msg_body.get('style')
        _type = msg_body.get('type')

#        _content = _content.decode('utf-8')
        if _type == 'buddy':
            webqq.hub.send_buddy_msg(int(_id), _content, _style)
        elif _type == 'group':
            webqq.hub.send_group_msg(int(_id), _content, _style)
        elif _type == 'discu':
            webqq.hub.send_discu_msg(int(_id), _content, _style)
        else:
            logger.error('zmq message format error')

    stream = zmqstream.ZMQStream(pull)
    stream.on_recv(zmq_handler)

try:
    webqq.run()
except KeyboardInterrupt:
    logger.info("收到退出信号，程序退出...")
