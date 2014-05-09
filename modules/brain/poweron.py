# coding: utf-8
import os

from backend import Backend
import config
from helpers import init_logger

import zmq

logger = init_logger()
_path = os.path.abspath(os.path.dirname(__file__))

context = zmq.Context()

def run():
    backend = Backend()

if __name__ == '__main__':
    run()
