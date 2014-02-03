import zmq
import json

context = zmq.Context()

subscriber = context.socket(zmq.SUB)
#subscriber.setsockopt(zmq.IDENTITY, 'Hello')
subscriber.bind('ipc:///tmp/publish.ipc')
#subscriber.bind('tcp://*:5555')
subscriber.setsockopt(zmq.SUBSCRIBE, '')

#sync = context.socket(zmq.PUSH)
#sync.bind('tcp://*:5564')
#sync.send('')

while True:
    data = subscriber.recv()
    print(data)
