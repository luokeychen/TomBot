#coding: utf-8
from engine import Engine, respond_handler


class Notify(Engine):
    '''通用消息发送器'''

    @respond_handler('notify (.*)')
    def respond(self, message, matches):
        message.send_info(matches.group(1).encode('utf-8'))
        return True
