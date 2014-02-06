# coding: utf-8
from engine import Engine
from engine import regex
import random

class Who(Engine):
    def __init__(self):
        self.topics = ['who']
        self.lily = [
                '她是个腐女',
                '别跟我提她！！！'
                ]
        self.lzz = [
                '一个很二很二的人。。。'
                ]
        self.agan = [
                '我还没想好怎么描述他'
                ]
    
    @regex('who is (\w+)$')
    def respond(self, message, matches):
        if matches.group(1) == 'lily':
            message.send(random.choice(self.lily))
        if matches.group(1) == 'lzz':
            message.send(random.choice(self.lzz))
