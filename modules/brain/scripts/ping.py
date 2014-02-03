#coding: utf-8
from engine import Engine
from engine import regex
import random

class Ping(Engine):
    '''Tom? 将得到随机应答，用来确认Tom是否在工作'''
    def __init__(self):
        super(Ping, self).__init__()
        self.add_topic('?')
        self.greets = [
                '在，主人！',
                '是的！主人！',
                'May I help you, sir?',
                '妈蛋, 别吵我',
                '我还活着！',
                '来了，来了',
                '哈哈哈哈哈!!!',
                '从我眼前走过的老鼠有很多只，但能停留在我心中的只有你这么一只！'
                ]
    
    @regex('\?$')
    def respond(self, message, matches):
        message.send(random.sample(self.greets, 1)[0])
