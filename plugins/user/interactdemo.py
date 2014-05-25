#!/usr/bin/env python
# -*- coding:utf-8 -*-
from tombot import botcmd
from tombot import Engine


class Interact(Engine):
    @botcmd
    def ask(self, message, args):
        user_input = message.get_input('type something')
        message.send(u'User input:{0}'.format(user_input))
