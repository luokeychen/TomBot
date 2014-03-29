#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#  Copyright (C) 2014 konglx
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY konglx ''AS IS'' AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL konglx BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : utils.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : some useful code

import threading
import logging

import const
import config

logger = logging.getLogger('')


"""
Code to timeout with processes.

>>> @timeout(.5)
... def sleep(x):
...     print "ABOUT TO SLEEP {0} SECONDS".format(x)
...     time.sleep(x)
...     return x

>>> sleep(1)
Traceback (most recent call last):
   ...
TimeoutException: timed out after 0 seconds

>>> sleep(.2)
0.2

>>> @timeout(.5)
... def exc():
...     raise Exception('Houston we have problems!')

>>> exc()
Traceback (most recent call last):
   ...
Exception: Houston we have problems!

"""
import multiprocessing
import time
import logging
#logger = multiprocessing.log_to_stdout()
#logger.setLevel(logging.INFO)


class TimeoutException(Exception):
    pass


class RunableProcessing(multiprocessing.Process):
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func,) + args
        multiprocessing.Process.__init__(self, target=self.run_func,
                                         args=args,
                                         kwargs=kwargs)

    def run_func(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self.queue.put((True, result))
        except Exception as e:
            self.queue.put((False, e))

    def done(self):
        return self.queue.full()

    def result(self):
        return self.queue.get()


def timeout(seconds, force_kill=True):
    def wrapper(function):
        def inner(*args, **kwargs):
            now = time.time()
            proc = RunableProcessing(function, *args, **kwargs)
            proc.start()
            proc.join(seconds)
            if proc.is_alive():
                if force_kill:
                    proc.terminate()
                runtime = int(time.time() - now)
                raise TimeoutException('timed out after {0} seconds'.format(runtime))
            assert proc.done()
            success, result = proc.result()
            if success:
                return result
            else:
                raise result
        return inner
    return wrapper


if __name__ == '__main__':
    import doctest
    doctest.testmod()


def run_in_thread(target=None, args=()):
    t = threading.Thread(target=target, args=args)
    t.daemon = True
    t.start()


def gbk2utf8(string):
    return string.decode('GBK').encode('UTF-8')


def make_msg(retcode, content=None, id_=None, type_=None,
             style=const.DEFAULT_STYLE):

    msg = dict(retcode=retcode,
               content=content,
               style=style,
               id=id_,
               type=type_)
    return msg


def init_logger():
    '''初始化logger
    '''
    import tornado.log

    if not config.debug:
        fmt = logging.Formatter('%(asctime)s %(module)s %(levelname)s %(message)s')

        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        fh = logging.FileHandler('{0}/log/tom.log'.format(config.home))
        fh.setFormatter(fmt)

        logger.addHandler(fh)
        logger.addHandler(ch)
    else:
        tornado.log.enable_pretty_logging()

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
    return logger
