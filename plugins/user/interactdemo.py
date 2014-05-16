#!/usr/bin/env python
# -*- coding:utf-8 -*-
from tombot import botcmd
from tombot import Engine


class Interact(Engine):
    @botcmd
    def ask(self, message, args):
        message.send('Type something')
        user_input = message.get_input()
        message.send(u'User input:{0}'.format(user_input))
