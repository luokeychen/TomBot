#coding: utf-8
from __future__ import division

import re

from tombot.common.utils import timelimit, TimeoutError
from tombot import botcmd
from tombot import Engine


class Calculator(Engine):
    @botcmd
    def calc(self, message, args):
        """Calculate expression, supports many types of operation"""
        expression = args.encode('utf-8')
        try:
            result = self.calculate(expression)
            message.send(result)
        except OverflowError:
            message.error('数字太大了，我算不出来！')
        except SyntaxError:
            message.error('这种格式汤姆不能理解！')
        except ZeroDivisionError:
            message.warn('不要调戏我！')
        except TimeoutError:
            message.error('太复杂了，要花太多时间，不干了。')

    @timelimit(2)
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
