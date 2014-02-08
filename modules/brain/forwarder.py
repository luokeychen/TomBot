# coding: utf-8
from __future__ import print_function

import re
import imp
import logging
import os
import sys

from inspect import isclass, getfile

import yaml
import zmq.green as zmq
import gevent
from multiprocessing import Process

_path = os.path.abspath(os.path.dirname(__file__))

import types
sys.modules['config'] = types.ModuleType('config')
import config

config_file = file('{0}/../../conf/config.yaml'.format(_path))

yaml_dict = yaml.load(config_file)
config.name = yaml_dict.get('name')
config.home = yaml_dict.get('home')
config.ipc_path = yaml_dict.get('ipc_path')
config.log_level = yaml_dict.get('log_level')
config.plugins = yaml_dict.get('plugins')
config.debug = yaml_dict.get('debug')

logger = logging.getLogger('tom_log')

def init_logger():
    '''初始化logger
    '''

    fmt = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    fh = logging.FileHandler('{0}/log/tom.log'.format(config.home))
    fh.setFormatter(fmt)

    logger.addHandler(fh)

    if config.log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif config.log_level == 'info':
        logger.setLevel(logging.INFO)
    elif config.log_level == 'warn':
        logger.setLevel(logging.WARN)
    elif config.log_level == 'error':
        logger.setLevel(logging.ERROR)
    elif config.log_level == 'critical':
        logger.setLevel(logging.CRITICAL)
    else:
        logging.error('错误的日志级别，请设置成debug, info, warning, error, critical中的一个')


    if config.debug:
        logger.addHandler(ch)
        logger.setLevel(logging.DEBUG)

def load_scripts():
    '''载入插件
    '''
    for plugin in config.plugins:
        m = imp.load_source(plugin, '{0}/scripts/{1}.py'.format(_path, plugin))
        for item in dir(m):
            attr = getattr(m, item)
            if isclass(attr) and plugin in getfile(attr):
                _instance = attr()
                logger.info('正在实例化脚本{0}的{1}类...'.format(plugin, attr.__name__))
                try:
                    p = Process(target=_instance.run)
                except AttributeError as e:
                    logger.warn('脚本载入失败，错误信息：{0}'.format(e))
                    continue
                p.start()


def forwarding():
    '''
    转发函数，订阅消息，并把正确的消息过滤完后送给scripts
    '''
    name = config.name
    context = zmq.Context(1)
    frontend = context.socket(zmq.SUB)
    frontend.setsockopt(zmq.IDENTITY, 'Frontend')
    # 订阅以机器人名字开头的消息，包括小写、大写、首字母大写

    frontend.setsockopt(zmq.SUBSCRIBE, '@' + name)
    frontend.setsockopt(zmq.SUBSCRIBE, name.lower())
    frontend.setsockopt(zmq.SUBSCRIBE, name.upper())
    frontend.setsockopt(zmq.SUBSCRIBE, name.capitalize())
    frontend.bind('ipc://{0}/publish.ipc'.format(config.ipc_path))

    backend = context.socket(zmq.PUB)
    backend.setsockopt(zmq.IDENTITY, 'Backend')
    backend.bind('ipc://{0}/route.ipc'.format(config.ipc_path))
    # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
    pattern = re.compile('^{0}'.format(name), flags=re.IGNORECASE)

    def _recv():
        while True:
                [_content, _id, _type] = frontend.recv_multipart()
                logging.debug('从adapter收到消息: {0}'.format((_content, _id, _type)))
                _content = pattern.sub('', _content, 1).strip()
                backend.send_multipart([_content, _id, _type])
                logging.debug('发布消息给scripts: {0}'.format((_content, _id, _type)))
                gevent.sleep(0)

    gevent.spawn(_recv).join()

def run():
    init_logger()
    logger.info('开始载入脚本...')
    load_scripts()
    logger.info('脚本载入完成')
    # forwarding 必须在子进程中运行，否则ioloop会有问题
    p = Process(target=forwarding)
    p.start()
    logger.info('forwarder 开始监听')
    p.join()

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        logging.shutdown()
        exit(0)
