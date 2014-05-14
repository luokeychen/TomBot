# coding=utf-8
import logging

from tombot.common import config

logger = logging.getLogger('TOM')


def init_logger():
    """初始化logger """
    import tornado.log

    fmt = logging.Formatter('%(asctime)s %(module)s %(levelname)s %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    fh = logging.FileHandler('{0}/log/tom.log'.format(config.home))
    fh.setFormatter(fmt)

    if not config.debug:

        logger.addHandler(fh)
        logger.addHandler(ch)
    else:
        tornado.log.enable_pretty_logging()
        logger.addHandler(fh)

    if config.log_level == 'debug':
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    elif config.log_level == 'info':
        logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.INFO)
    elif config.log_level == 'warn':
        logger.setLevel(logging.WARN)
        logging.basicConfig(level=logging.WARN)
    elif config.log_level == 'error':
        logger.setLevel(logging.ERROR)
        logging.basicConfig(level=logging.ERROR)
    elif config.log_level == 'critical':
        logger.setLevel(logging.CRITICAL)
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.error('错误的日志级别，请设置成debug, info, warning, error, critical中的一个')


init_logger()
