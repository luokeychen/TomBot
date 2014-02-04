#coding: utf-8
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals
from math import *

import re
import zmq

from engine import Engine
from engine import regex


class Caculator(Engine):
    '''Tom calc 表达式. 例如：tom calc 123^22/444+123.
            ps. 可以做位运算：tom calc 1<<3|2<<8&11|~123'''
    def __init__(self):
        super(Caculator, self).__init__()
        self.add_topic('calc')

    @regex('calc (.*)$')
    def respond(self, message, matches):
        expression= matches.group(1)
        try:
            result = self.calculate(expression)
            message.send(result)
        except OverflowError:
            message.send('数字太大了，我算不出来！')
        except SyntaxError:
            message.send('这种格式汤姆不能理解！')

    def calculate(self, exp):
        exp = exp.replace(' ', '')
        exp = exp.replace('^', '**')
        exp = exp.replace('（', '(')
        exp = exp.replace('）', ')')
        exp = exp.replace('×', '*')
        exp = exp.replace('x', '*')
        exp = exp.replace('﹢', '+')
        exp = exp.replace('÷', '/')
        exp = str(exp.replace('–', '-'))
        rex = re.compile('\d+\.*\d+%')
        for match in rex.finditer(exp):
            bfs = match.group()
            bfs = float(bfs[:-1]) / 100
            exp = exp.replace(match.group(), str(bfs))
        res = eval(exp)
        if len(str(res)) > 100:
            res = '%E' % float(res)
        return str(res)



def test():
    import tornado.log
    import tornado.ioloop
    app = tornado.web.Application([
            (r'/calc', Caculator)
            ], debug=True)
    tornado.log.enable_pretty_logging()
    app.listen(3000)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    test()
