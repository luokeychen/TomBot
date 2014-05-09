#coding: utf-8
from engine import Respond, plugin
import random

respond = Respond()


@plugin
class Ping(object):
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

    @respond.register('\?$')
    def respond(self, message, matches):
        message.send(random.choice(self.greets))
        return True