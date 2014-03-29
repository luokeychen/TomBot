import os
import sys
import zmq
import threading
from zmq.eventloop import ioloop, zmqstream

_home = os.getenv('TOMBOT_HOME')
_prompt = 'TomBot> '

context = zmq.Context()
pub = context.socket(zmq.PUB)
pub.connect('ipc://{0}/run/publish.ipc'.format(_home))
pull = context.socket(zmq.PULL)
pull.bind('ipc://{0}/run/push.ipc'.format(_home))

def prompt():
    user_input = raw_input(_prompt)
    if user_input == 'exit':
        exit(0)
    elif user_input != '':
        _ = ' '
        pub.send_multipart([user_input, _, _])

def run():

    while True:
        try:
            command = prompt()
        except KeyboardInterrupt:
            pass

def _on_recv():
    while True:
        content, _, _ = pull.recv_multipart()
        print(content)
        command = prompt()


if __name__ == '__main__':
    run()
#    stream = zmqstream.ZMQStream(pull)
#    stream.on_recv(_on_recv)
#    loop = ioloop.IOLoop.instance()
#    loop.start()
