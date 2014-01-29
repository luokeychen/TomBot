#coding: utf-8
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import imp

import tornado.ioloop
import tornado.log
import json

def load_scripts():
    # 载入enabled_scripts.json中定义的脚本
    fp = open('./enabled_scripts.json')
    scripts = json.load(fp).items()

    # 载入对应文件的类，并指定路由
    for script in scripts:
        class_name = script[0]
        m = imp.load_source(script[0], './scripts/' + script[1])
        get_vars = getattr(m, 'get_vars')
        vars = get_vars()

        script_class = getattr(m, class_name)
        app = tornado.web.Application([
                (vars['route'], script_class)
                ], debug=True)
        return app

def test():
    app = load_scripts()
    tornado.log.enable_pretty_logging()
    app.listen(3000, '0.0.0.0')
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    test()
