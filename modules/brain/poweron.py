# coding: utf-8
import logging
import os

from forwarder import init_logger, forwarding
from forwarder import config
from plugin_manager import load_scripts

import zmq

_path = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger('')


context = zmq.Context()
push = context.socket(zmq.PUSH)
if config.use_tcp:
    push.bind(config.pullpush_socket)
else:
    push.bind('ipc://{0}/push.ipc'.format(config.ipc_path))

def run():
    logger = init_logger()
    logger.info('开始载入脚本...')
    load_scripts('scripts', push)
    load_scripts('ansible', push)
    logger.info('脚本载入完成')
    logger.info('forwarder 准备开始监听')
    forwarding()

if __name__ == '__main__':
    run()
