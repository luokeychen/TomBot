#coding: utf-8
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import absolute_import


import re
import imp
import logging
import os
import sys

import zmq.green as zmq
import gevent
from gevent import monkey
monkey.patch_all(thread=False)
import json

from engine import Engine


logger = logging.getLogger('')
_path = os.path.abspath(os.path.dirname(__file__))

def get_scripts():
    # 载入enabled_scripts.json中定义的脚本
    fp = open(_path + '/scripts.json')
    scripts = json.load(fp).items()
    fp.close()
    return scripts

def load_scripts(scripts):

    # 载入对应文件的类
    for script in scripts:
        class_name = script[0]
        m = imp.load_source(script[0], _path + '/scripts/' + script[1])

        script_class = getattr(m, class_name)
        logger.info('Loading script: %s', class_name)
        _instance = script_class()
        gevent.spawn(_instance.start)


def forwarding():
    name = 'Tom'
    context = zmq.Context.instance()
    frontend = context.socket(zmq.SUB)
    frontend.setsockopt(zmq.IDENTITY, 'Frontend')
    # 订阅以机器人名字开头的消息，包括小写、大写、首字母大写

    frontend.setsockopt(zmq.SUBSCRIBE, '@' + name)
    frontend.setsockopt(zmq.SUBSCRIBE, name.lower())
    frontend.setsockopt(zmq.SUBSCRIBE, name.upper())
    frontend.setsockopt(zmq.SUBSCRIBE, name.capitalize())
    frontend.bind('ipc:///tmp/publish.ipc')

    backend = context.socket(zmq.PUB)
    backend.setsockopt(zmq.IDENTITY, 'Backend')
    backend.bind('ipc:///tmp/route.ipc')
    # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
    pattern = re.compile('^' + name, flags=re.IGNORECASE)
    while True:
        try:
            [_content, _id, _type] = frontend.recv_multipart(zmq.NOBLOCK)
            logging.info('received message from adapter : %s', (_content, _id, _type))
            _content = pattern.sub('', _content, 1).strip()
            backend.send_multipart([_content, _id, _type])
            logging.info('publish message to scripts: %s', (_content, _id, _type))
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                gevent.sleep(0)
            else:
                raise

def run():
    scripts = get_scripts()
    load_scripts(scripts)
    strm_out = logging.StreamHandler(sys.__stdout__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')
    strm_out.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(strm_out)
    gevent.spawn(forwarding).join()

if __name__ == '__main__':
    run()
