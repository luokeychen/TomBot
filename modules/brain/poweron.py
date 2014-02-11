# coding: utf-8
from multiprocessing import Process
import logging
from gevent.monkey import patch_all
patch_all(thread=False)
import geventhttpclient.httplib
geventhttpclient.httplib.patch()
from forwarder import init_logger, load_scripts, forwarding


def run():
    logger = init_logger()
    logger.info('开始载入脚本...')
    load_scripts()
    logger.info('脚本载入完成')
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
