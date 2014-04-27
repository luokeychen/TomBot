# coding: utf-8
import os

from backend import BackendManager
import config
from helpers import init_logger

import zmq

logger = init_logger()
_path = os.path.abspath(os.path.dirname(__file__))

context = zmq.Context()

def run():
    # tell engine to connect which route ipc
    logger.info('开始启动backend')
    backends = BackendManager()

    for i in xrange(config.backend_count):
        backends.add()

if __name__ == '__main__':
    run()
