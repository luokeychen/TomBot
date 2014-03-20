#coding: utf-8
from __future__ import division
from math import *

import re

# from engine import Engine
# from engine import respond_handler
from engine import Respond, plugin
from utils import timeout, TimeoutException

respond = Respond()


#TODO 用plugin修饰的会自动运行
@plugin
class Caculator(object):
    '''Tom calc 表达式 例如：tom calc 123^22/444+123.可以做位运算：tom calc 1<<3|&11|~123'''

    @respond.register('calc (.*)$')
    def respond(self, message, matches):
        expression = matches.group(1).encode('utf-8')
        try:
            result = self.calculate(expression)
            message.send(result)
        except OverflowError:
            message.error('数字太大了，我算不出来！')
        except SyntaxError:
            message.error('这种格式汤姆不能理解！')
        except ZeroDivisionError:
            message.warn('不要调戏我！')
        except TimeoutException:
            message.error('太复杂了，要花太多时间，不干了。')

        return True

    @timeout(1)
    def calculate(self, exp):
        exp = exp.replace(' ', '')
        exp = exp.replace('^', '**')
        exp = exp.replace('（', '(')
        exp = exp.replace('）', ')')
        exp = exp.replace('×', '*')
        exp = exp.replace(',', '')
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
