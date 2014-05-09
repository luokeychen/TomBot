import zmq.green as zmq
import gevent
import os
import random
import time

context = zmq.Context(1)
pub = context.socket(zmq.PUB)
_home = os.getenv('TOMBOT_HOME')
pub.connect('ipc://{0}/run/publish.ipc'.format(_home))
pull = context.socket(zmq.PULL)
pull.bind('ipc://{0}/run/push.ipc'.format(_home))

msg_list = [
    'tom?',
    'tom help',
    #        'tom make me laugh',
    'tom calc 123^11'
]

send_num = 10000


def sender():
    msg_count = 0
    start = time.time()
    for i in xrange(send_num):
        pub.send_multipart([random.choice(msg_list), 'a', 'b'])
        msg_count += 1
        gevent.sleep(0.001)
    print('sended msg: {0}'.format(msg_count))
    end = time.time()
    print('speed: {0}'.format(msg_count / (end - start)))


def recver():
    msg_count = 0
    start = time.time()
    while True:
        a, b, c = pull.recv_multipart()
        msg_count += 1
        if msg_count == send_num:
            end = time.time()
            print('recv complete, speed:{0}'.format(send_num / (end - start)))
            exit(0)
        gevent.sleep(0)


def run():
    gevent.spawn(sender)
    gevent.spawn(recver).join()


if __name__ == '__main__':
    run()
