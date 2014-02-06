# coding: utf-8
from __future__ import division
from __future__ import print_function


import re
import imp
import logging
import os
import sys

import zmq
from zmq.eventloop import ioloop
ioloop.install()
from zmq.eventloop import zmqstream
import json
from multiprocessing import Process

from engine import Engine

_home = os.getenv('TOMBOT_HOME')

_pub_ipc_file = 'ipc://{0}/run/publish.ipc'.format(_home)
_push_ipc_file = 'ipc://{0}/run/push.ipc'.format(_home)
_route_ipc_file = 'ipc://{0}/run/route.ipc'.format(_home)
logger = logging.getLogger('')
_path = os.path.abspath(os.path.dirname(__file__))


def get_scripts():
    # 载入enabled_scripts.json中定义的脚本
    fp = open('{0}/scripts.json'.format(_path))
    scripts = json.load(fp).items()
    fp.close()
    return scripts

def load_scripts(scripts):

    # 载入对应文件的类
    for script in scripts:
        class_name = script[0]
        m = imp.load_source(script[0], '{0}/scripts/{1}'.format(_path, script[1]))

        script_class = getattr(m, class_name)
        logger.info('正在载入脚本{0}'.format(class_name))
        _instance = script_class()
        p = Process(target=_instance.run)
        p.start()


def forwarding():
    name = 'Tom'
    context = zmq.Context(1)
    frontend = context.socket(zmq.SUB)
    frontend.setsockopt(zmq.IDENTITY, 'Frontend')
    # 订阅以机器人名字开头的消息，包括小写、大写、首字母大写

    frontend.setsockopt(zmq.SUBSCRIBE, '@' + name)
    frontend.setsockopt(zmq.SUBSCRIBE, name.lower())
    frontend.setsockopt(zmq.SUBSCRIBE, name.upper())
    frontend.setsockopt(zmq.SUBSCRIBE, name.capitalize())
    frontend.bind(_pub_ipc_file)

    backend = context.socket(zmq.PUB)
    backend.setsockopt(zmq.IDENTITY, 'Backend')
    backend.bind(_route_ipc_file)
    # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
    pattern = re.compile('^{0}'.format(name), flags=re.IGNORECASE)

    def _recv(msg):
        [_content, _id, _type] = msg
        logging.debug('received message from adapter : {0}'.format((_content, _id, _type)))
        _content = pattern.sub('', _content, 1).strip()
        backend.send_multipart([_content, _id, _type])
        logging.debug('publish message to scripts: {0}'.format((_content, _id, _type)))
        
    stream = zmqstream.ZMQStream(frontend)
    stream.on_recv(_recv)
    loop = ioloop.IOLoop.instance()
#    loop.make_current()
    loop.start()


def run():
    import tornado.log
    tornado.log.enable_pretty_logging()
    logger.setLevel(logging.DEBUG)
    logger.info('开始载入脚本...')
    scripts = get_scripts()
    load_scripts(scripts)
    logger.info('脚本载入完成')
    logger.info('主程序开始监听')
    # forwarding 必须在子进程中运行，否则ioloop会有问题
    p = Process(target=forwarding)
    p.start()
    p.join()

if __name__ == '__main__':
    run()
