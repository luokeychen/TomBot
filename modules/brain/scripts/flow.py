#coding: utf-8
from engine import Engine
from engine import regex

class Flow(Engine):
    '''Tom query flow id  查询服务流程单号'''
    def __init__(self):
        super(Flow, self).__init__()
        self.add_topic('query')
    
    @regex('query flow (\d+)$')
    def respond(self, message, matches):
        flow_id = matches.group(1)
        message.send(flow_id)
