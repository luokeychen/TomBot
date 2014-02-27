# coding: utf-8
from multiprocessing import Process
import logging
from inspect import isclass, getfile
import imp
import os

from gevent.monkey import patch_all
#patch_all(thread=False)

from forwarder import init_logger, load_scripts, forwarding
_path = os.path.abspath(os.path.dirname(__file__))

from forwarder import config

logger = logging.getLogger('')

def load_runners():
    '''载入插件
    '''
    for ansible in config.ansibles:
        m = imp.load_source(ansible, '{0}/../ansible/{1}.py'.format(_path, ansible))
        for item in dir(m):
            attr = getattr(m, item)
            if isclass(attr) and ansible in getfile(attr):
                if hasattr(attr, 'run'):
                    _instance = attr()
                    logger.info('正在实例化ansible脚本{0}的{1}类...'.format(ansible, attr.__name__))
                    try:
                            p = Process(target=_instance.run)
                    except AttributeError as e:
                        logger.warn('ansible脚本载入失败，错误信息：{0}'.format(e))
                        continue
                    p.start()

def run():
    logger = init_logger()
    logger.info('开始载入脚本...')
    load_scripts()
    load_runners()
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
