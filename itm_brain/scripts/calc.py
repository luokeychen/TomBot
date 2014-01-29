#coding: utf-8
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import tornado.web

def get_vars():
    return {'route': r'/calc'}

class Caculator(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        expression = self.get_argument('expression')
        print(expression)
        try:
            result = self.calculate(expression)
            self.write(result)
            self.finish()
        except OverflowError:
            self.write({'result': 'Value too large to calculate!'})
            self.finish()

    def calculate(self, exp):
        exp = exp.replace(' ', '+')
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
            res = '%E' % res
        return {'result': str(res)}



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
