import zmq
import config

plugin_manager = None
bot = None

context = zmq.Context(1)
broker_socket = context.socket(zmq.DEALER)
broker_socket.connect('ipc://{0}/broker.ipc'.format(config.ipc_path))
