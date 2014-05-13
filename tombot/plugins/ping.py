#coding: utf-8
import random

from tombot import Engine
from tombot import re_botcmd, botcmd


class Ping(Engine):
    '''Tom? 将得到随机应答，用来确认Tom是否在工作'''
    greets = [
        '在，主人！',
        '是的！主人！',
        'May I help you, sir?',
        '我还活着！',
        '来了，来了!',
        ' 咚咚（猫摔下楼梯）',
        'Jerry!',
        '哈哈哈哈哈!!!',
        '从我眼前走过的老鼠有很多只，但能停留在我心中的只有你这么一只！'
    ]

    @botcmd
    def respond(self, message, args):
        message.send(random.choice(self.greets))
        message.send('Parameter: {}'.format(args))

    @botcmd
    def res(self, message, args):
        message.send("I'm alive")
