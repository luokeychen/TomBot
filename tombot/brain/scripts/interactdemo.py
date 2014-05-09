#!/usr/bin/env python
# -*- coding:utf-8 -*-

from engine import Respond, plugin

respond = Respond()


@plugin
class Interact(object):
    @respond.register('ask')
    def respond(self, message, matches):
        message.send('选择1或2')
        user_input = respond.get_input(message)
        message.send(u'用户选择了:{0}'.format(user_input))
