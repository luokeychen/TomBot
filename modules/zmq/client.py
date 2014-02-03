import zmq.green as zmq
import gevent

context = zmq.Context()

sync = context.socket(zmq.PULL)
sync.bind('ipc:///tmp/push.ipc')

publisher = context.socket(zmq.PUB)
publisher.connect('ipc:///tmp/publish.ipc')

#sync_request = sync.recv()

def send():
    while True:
        publisher.send_multipart(['tom?', '123456', 'type'])
        gevent.sleep(0.01)

def recv():
    while True:
        [content, id, type] = sync.recv_multipart()
        print(content, id, type)

send = gevent.spawn(send)
recv = gevent.spawn(recv)
gevent.joinall([send, recv])

