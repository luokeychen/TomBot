#coding: utf-8
from engine import Engine
from engine import respond_handler
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
    
    @respond_handler('.*$')
    def respond(self, message, matches):
        message.send(random.choice(self.greets))
