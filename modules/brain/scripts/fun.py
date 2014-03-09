# coding: utf-8
from engine import Engine, respond_handler
import random

class Fun(Engine):
    def __init__(self):
        self.hello = [
                '你好~~~',
                'Hi~'
                ]
        self.zz = [
                '哦',
                '哦，总算没那么烦人了',
                '祝她一路顺风~',
                'zz是谁？'
                ]
        self.chenw = [
                '就是个二货',
                '朝三暮四的',
                '朝秦暮楚的',
                '不想评论他',
                '就是伟妹子吧？'
                ]
        self.lily = [
                '她是个腐女',
                '别跟我提她！！！',
                '她老清新了。。。'
                ]
        self.lzz = [
                '一个很二很二的人。。。'
                ]
        self.agan = [
                '我还没想好怎么描述他'
                ]

    @respond_handler('zz.*走.*$')
    def zzgone(self, message, matches):
        message.send(random.choice(self.zz))
    
    @respond_handler('who is (\w+)$')
    def who(self, message, matches):
        if matches.group(1) == 'lily':
            message.send(random.choice(self.lily))
        if matches.group(1) in ('lzz', 'zz', '珍珍'):
            message.send(random.choice(self.lzz))
        if matches.group(1) in ('chenw', 'chenwei', '陈伟', '伟妹子'):
            message.send(random.choice(self.chenw))


    @respond_handler('who are you.*$')
    def whotom(self, message, matches):
        message.send('我是无所不能的Tom~~~')

    @respond_handler('.*$')
    def hello(self, message, matches):
        message.send(self.hello)
    

