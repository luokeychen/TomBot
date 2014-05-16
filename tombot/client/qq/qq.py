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
import sys
import zmq
import json
import smtplib
from zmq.eventloop import zmqstream, ioloop

ioloop.install()
import yaml

import os
import traceback

sys.path.append('./twqq')
from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler, discu_message_handler
from twqq.requests import buddy_message_handler, kick_message_handler, register_request_handler, PollMessageRequest
from twqq.requests import FriendListRequest, BeforeLoginRequest, Login2Request

from server import http_server_run

from email.mime.text import MIMEText

logger = logging.getLogger('client')
logger.setLevel(logging.DEBUG)

fp = file('config.yaml')
config = yaml.load(fp)

SMTP_HOST = config.get('smtp_host')
SMTP_ACCOUNT = config.get('smtp_account')
SMTP_PASSWORD = config.get('smtp_password')
HTTP_HOST = config['verify'].get('http_host')
HTTP_PORT = config['verify'].get('http_port')
EMAIL = config['verify'].get('email')
USE_HTTP = config['verify'].get('use_http')

use_proxy = config.get('use_proxy')
proxy_host = config.get('proxy_host')
proxy_port = config.get('proxy_port')

req_socket = config.get('req_socket')

context = zmq.Context(1)
socket = context.socket(zmq.DEALER)
socket.setsockopt(zmq.IDENTITY, 'QQ')
_home = os.getenv('TOMBOT_HOME')
socket.connect(req_socket)


def send_notice_email():
    """ 发送提醒邮件
    """
    if not SMTP_HOST:
        return False

    postfix = ".".join(SMTP_HOST.split(".")[1:])
    me = "bot<{0}@{1}>".format(SMTP_ACCOUNT, postfix)

    msg = MIMEText(""" 你的WebQQ机器人需要一个验证码,
                   请打开你的服务器输入验证码:
                   http://{0}:{1}""".format(HTTP_HOST,
                                            HTTP_PORT),
                   _subtype="plain", _charset="utf-8")
    msg['Subject'] = u"WebQQ机器人需要验证码"
    msg["From"] = me
    msg['To'] = EMAIL
    try:
        server = smtplib.SMTP()
        server.connect(SMTP_HOST)
        server.login(SMTP_ACCOUNT, SMTP_PASSWORD)
        server.sendmail(me, [EMAIL], msg.as_string())
        server.close()
        return True

    except Exception as e:
        traceback.print_exc()
        return False


class Client(WebQQClient):
    def handle_verify_code(self, path, r, uin):
        self.verify_img_path = path

        if hasattr(self, "handler") and self.handler:
            self.handler.r = r
            self.handler.uin = uin

        # if USE_HTTP:
        #     logger.info("请打开 http://{0}:{1} 输入验证码"
        #                 .format(HTTP_HOST, HTTP_PORT))
        # else:
        logger.info(u"验证码本地路径为: {0}".format(self.hub.checkimg_path))
        check_code = None
        while not check_code:
            check_code = raw_input("输入验证码: ")
        self.enter_verify_code(check_code, r, uin)
        return

        if send_notice_email():
            logger.info("发送通知邮件成功")
        else:
            logger.warning("发送通知邮件失败")

    def enter_verify_code(self, code, r, uin, callback=None):
        super(Client, self).enter_verify_code(code, r, uin)
        self.verify_callback = callback
        self.verify_callback_called = False

    @register_request_handler(BeforeLoginRequest)
    def handle_verify_check(self, request, resp, data):
        if not data:
            self.handle_verify_callback(False, "没有数据返回验证失败, 尝试重新登录")
            return

        args = request.get_back_args(data)
        scode = int(args[0])
        if scode != 0:
            self.handle_verify_callback(False, args[4])

    def handle_verify_callback(self, status, msg=None):
        if hasattr(self, "verify_callback") and callable(self.verify_callback) \
                and not self.verify_callback_called:
            self.verify_callback(status, msg)
            self.verify_callback_called = True

    @register_request_handler(Login2Request)
    def handle_login_errorcode(self, request, resp, data):
        if not resp.body:
            return self.handle_verify_callback(False, u"没有数据返回, 尝试重新登录")

        if data.get("retcode") != 0:
            return self.handle_verify_callback(False, u"登录失败: {0}"
                                               .format(data.get("retcode")))

    @register_request_handler(FriendListRequest)
    def handle_frind_info_erro(self, request, resp, data):
        if not resp.body:
            self.handle_verify_callback(False, u"获取好友列表失败")
            return

        if data.get("retcode") != 0:
            self.handle_verify_callback(False, u"好友列表获取失败: {0}"
                                        .format(data.get("retcode")))
            return
        self.handle_verify_callback(True)

    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == 'verify_required':
            self.hub.accept_verify(from_uin, account, account)

    @discu_message_handler
    def handle_discu_message(self, did, from_uin, content, source):
        msg = {'content': content.encode('utf-8'),
               'id': str(did),
               'type': 'discu',
               'user': from_uin}
        socket.send_json(msg)

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             from_uin, source):
        msg = {'content': content.encode('utf-8'),
               'id': str(group_code),
               'type': 'group',
               'user': from_uin}
        socket.send_json(msg)

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        msg = {'content': content.encode('utf-8'),
               'id': str(from_uin),
               'type': 'buddy',
               'user': from_uin}
        socket.send_json(msg)

    @kick_message_handler
    def handle_kick(self, message):
        self.hub.relogin()

    @register_request_handler(PollMessageRequest)
    def handle_qq_errcode(self, request, resp, data):
        if data and data.get("retcode") in [100006]:
            logger.error(u"获取登出消息 {0!r}".format(data))
            self.hub.relogin()

        if data and data.get("retcode") in [103]:  # 103重新登陆不成功,或被系统T掉，重新登录
            logger.error(u"获取登出消息 {0!r}".format(data))
            self.hub.relogin()

    def run(self, handler=None):
        self.handler = handler
        super(Client, self).run()


if __name__ == '__main__':
    import sys
    import tornado.log

    tornado.log.enable_pretty_logging()

    webqq = Client(int(sys.argv[1]), sys.argv[2])
    if use_proxy:
        webqq.hub.http.set_proxy(proxy_host, proxy_port)

    def zmq_handler(msg):
        logger.info(msg)
        try:
            msg_body = json.loads(msg[0])
        except ValueError as e:
            logger.warn('消息解析失败:{0}'.format(e))
        logger.info('adapter收到消息：{0}'.format(msg_body))
        _content = msg_body.get('content')
        _id = msg_body.get('id')
        _style = msg_body.get('style')
        _type = msg_body.get('type')
        _user = msg_body.get('user')

        #        _content = _content.decode('utf-8')
        if _type == 'buddy':
            webqq.hub.send_buddy_msg(int(_id), _content, _style)
        elif _type == 'group':
            webqq.hub.send_group_msg(int(_id), _content, _style)
        elif _type == 'discu':
            webqq.hub.send_discu_msg(int(_id), _content, _style)
        else:
            logger.error('zmq message format error')

    stream = zmqstream.ZMQStream(socket)
    stream.on_recv(zmq_handler)

    try:
        if USE_HTTP:
            http_server_run(webqq)
        else:
            webqq.run()
    except KeyboardInterrupt:
        logger.info("收到退出信号，程序退出...")
