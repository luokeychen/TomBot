import os
import sys
import zmq
import threading

_home = os.getenv('TOMBOT_HOME')
_prompt = 'TomBot> '

context = zmq.Context(1)
dealer = context.socket(zmq.DEALER)
dealer.setsockopt(zmq.IDENTITY, 'SHELL')
dealer.connect('tcp://127.0.0.1:4445')


class Shell(object):
    def __init__(self):
        self.lock = True

    def prompt(self):
        user_input = raw_input(_prompt)
        if user_input == 'exit':
            sys.exit(0)
        elif user_input == '':
            self.lock = True
        else:
            _ = ' '
            msg = dict(content=user_input,
                       type=_,
                       id=_,
                       user=_
                       )
            dealer.send_json(msg)

    def run(self):

        t = threading.Thread(target=self.recv)
        t.daemon = True
        t.start()

        while True:
            if self.lock:
                self.lock = False
                try:
                    self.prompt()
                except KeyboardInterrupt:
                    pass
                except EOFError:
                    sys.exit(0)

    def recv(self):
        while True:
            msg = dealer.recv_json()
            self.zmq_handler(msg)
            self.lock = True

    def zmq_handler(self, msg):
        _content = msg.get('content')
        print(_content)


if __name__ == '__main__':
    shell = Shell()
    shell.run()
