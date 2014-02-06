#coding: utf-8
from engine import Engine
from engine import regex
import random

class Bye(Engine):
    def __init__(self):
        self.topics = ['good', 'bye', '88']
        self.greets = [
                '8888',
                'See you~',
                'Good night',
                '晚安~'
                ]
    
    @regex('.*$')
    def respond(self, message, matches):
        message.send(random.choice(self.greets))
