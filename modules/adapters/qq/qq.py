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
import logging
import zmq
from zmq.eventloop import zmqstream, ioloop

import sys
import os
sys.path.append('./twqq')
from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler, discu_message_handler
from twqq.requests import buddy_message_handler, register_request_handler
from twqq.requests import PollMessageRequest


logger = logging.getLogger('client')
ioloop.install()

context = zmq.Context(1)
pub = context.socket(zmq.PUB)
_home = os.getenv('TOMBOT_HOME')
pub.connect('ipc://{0}/run/publish.ipc'.format(_home))
pull = context.socket(zmq.PULL)
pull.bind('ipc://{0}/run/push.ipc'.format(_home))


class Client(WebQQClient):
    def handle_verify_code(self, path, r, uin):
        logger.info(u'验证码本地路径为: {0}'.format(path))
        check_code = None
        while not check_code:
            check_code = raw_input('输入验证码: ')
        self.enter_verify_code(check_code, r, uin)


    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == 'verify_required':
            self.hub.accept_verify(from_uin, account, account)

    @discu_message_handler
    def handle_discu_message(self, member_uin, content, did,
                             send_uin, source):
        pub.send_multipart([content.encode('utf-8'), str(did), 'discu'])
#        self.hub.send_discu_msg(did, u'{0}'.format(content))

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        pub.send_multipart([content.encode('utf-8'), str(group_code), 'group'])
#        self.hub.send_group_msg(group_code, u'{0}'.format(content))

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        pub.send_multipart([content.encode('utf-8'), str(from_uin), 'buddy'])
#        self.hub.send_buddy_msg(from_uin, content)


    # @register_request_handler(PollMessageRequest)
    # def handle_qq_errcode(self, request, resp, data):
    #     if data and data.get('retcode') in [121, 100006]:
    #         logger.error(u'获取登出消息 {0!r}'.format(data))
    #         exit()


if __name__ == '__main__':
    import sys
    import tornado.log

    tornado.log.enable_pretty_logging()

    webqq = Client(int(sys.argv[1]), sys.argv[2])

    def zmq_handler(msg):
        _content, _id,  _type = msg
        _content = _content.decode('utf-8').encode('utf-8')
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

