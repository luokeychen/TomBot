#coding: utf-8
from engine import Respond, plugin

respond = Respond()


@plugin
class Notify(object):
    '''通用消息发送器'''

    @respond.register('notify (.*)')
    def respond(self, message, matches):
        message.info(matches.group(1).encode('utf-8'))
        return True
