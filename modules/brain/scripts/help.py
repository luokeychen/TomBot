#coding: utf-8
import imp
from inspect import isclass, getfile
from engine import Engine, respond_handler
from forwarder import config

class Help(Engine):
    '''Tom help \t[filter]'''

    def __init__(self):
        self.topics = ['help']
        self.helps = []
        self.get_helps()

    def get_helps(self):

        # 载入对应文件的类
        for plugin in config.plugins:
            m = imp.load_source(plugin, '{0}/modules/brain/scripts/{1}.py'.format(config.home, plugin))
            for item in dir(m):
                attr = getattr(m, item)
                if isclass(attr) and plugin in getfile(attr):
                    if attr.__doc__:
                        self.helps.append(attr.__doc__)

    @respond_handler('help$')
    def respond(self, message, matches):
        res = '\n'.join(self.helps)
        message.send(res)
