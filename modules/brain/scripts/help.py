#coding: utf-8
import os
import json
import imp
from engine import Engine
from engine import regex

_path = os.path.abspath(os.path.dirname(__file__))

class Help(Engine):
    '''Tom help [filter]'''

    def __init__(self):
        super(Help, self).__init__()
        self.add_topic('help')
        self.help_list = list()
        self.get_helps()

    def get_helps(self):
        fp = open(_path + '/../scripts.json')
        scripts = json.load(fp).items()
        fp.close()

        for script in scripts:
            class_name = script[0]
            m = imp.load_source(script[0], _path + '/' + script[1])
            script_class = getattr(m, class_name)
            self.help_list.append(script_class.__doc__)

    @regex('help (.*)$')
    def respond(self, message, matches):
        res = '\n'.join(self.help_list)
        message.send(res)
