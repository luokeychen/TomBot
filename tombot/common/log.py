# coding=utf-8
import logging

from tombot.common import config

logger = logging.getLogger('TOM')
yapsy_logger = logging.getLogger('yapsy')
broker_logger = logging.getLogger('BROKER')


def __init_yapsy_logger():
    fmt = logging.Formatter('%(asctime)s %(module)s %(levelname)s %(message)s')
    yapsy_fh = logging.FileHandler('{0}/log/yapsy.log'.format(config.home))
    yapsy_fh.setFormatter(fmt)
    yapsy_logger.setLevel(logging.DEBUG)
    yapsy_logger.addHandler(yapsy_fh)


def __init_logger(log_obj, logname):
    """初始化logger """
    import tornado.log

    fmt = logging.Formatter('%(asctime)s %(module)s %(levelname)s %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    fh = logging.FileHandler('{0}/log/{1}'.format(config.home, logname))
    fh.setFormatter(fmt)

    if not config.debug:

        log_obj.addHandler(fh)
        log_obj.addHandler(ch)
    else:
        tornado.log.enable_pretty_logging()
        log_obj.addHandler(fh)

    if config.log_level == 'debug':
        log_obj.setLevel(logging.DEBUG)
    elif config.log_level == 'info':
        log_obj.setLevel(logging.INFO)
    elif config.log_level == 'warn':
        log_obj.setLevel(logging.WARN)
    elif config.log_level == 'error':
        log_obj.setLevel(logging.ERROR)
    elif config.log_level == 'critical':
        log_obj.setLevel(logging.CRITICAL)
    else:
        logging.error('错误的日志级别，请设置成debug, info, warning, error, critical中的一个')


#init tom logger
__init_logger(logger, 'tom.log')
#init root logger
__init_logger(logging.getLogger(), 'all.log')
#init broker logger
__init_logger(broker_logger, 'broker.log')
__init_yapsy_logger()
