# coding: utf-8
import logging
import os

from forwarder import init_logger, load_scripts, load_runners, forwarding
_path = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger('')


def run():
    logger = init_logger()
    logger.info('开始载入脚本...')
    load_scripts()
    load_runners()
    logger.info('脚本载入完成')
    logger.info('forwarder 准备开始监听')
    forwarding()

if __name__ == '__main__':
    run()
