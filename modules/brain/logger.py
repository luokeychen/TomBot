import logging
import sys

def init_log(default_level = logging.DEBUG):
    logger = logging.getLogger('')
    strm_out = logging.StreamHandler(sys.__stdout__)
    logger.setLevel(default_level)
    logger.addHandler(strm_out)

