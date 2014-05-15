from pika import BlockingConnection
from pika import URLParameters
from pika import BasicProperties
import json
import time
import logging

import tornado
import tornado.log
import tornado.ioloop

# logging.getLogger('pika').setLevel(logging.DEBUG)

# from engine import Engine, respond_handler

# AMQ_ROUTINGKEY = 'itm.agent.{0}'.format('100000000013444')
AMQ_ROUTINGKEY = 'itm.agent.jagent_chenp-192.168.35.172.192.168.35.172:20555'
AMQ_EXCHANGE = 'itm.p2p'
AMQ_EXCHANGE_TYPE = 'direct'
AMQ_RETURN_WAIT_SECOND = '120'
INSPECT_SESSION_ID = 'tom'

tornado.log.enable_pretty_logging()


class AutoInspect(object):
    params = URLParameters('amqp://guest:guest@192.168.35.172:20555/%2F?heartbeat_interval=1')
    properties = BasicProperties(content_type='application/json',
                                 app_id='tom',
                                 delivery_mode=1)


    def auto_inspect(self):
        neid = '100000000013414'
        inspect_session_id = INSPECT_SESSION_ID

        #         inspect_msg = Message(channel, properties={
        #                 'content-type': 'application/json'
        #                 })

        #         conn = Connection(
        #             userid='guest', password='guest',
        #             virtual_host='/', host='192.168.35.172',
        #             port=20555)
        items = [{"executive": "kmScript", "ctrlColId": "1000", "function": "LINUX_MAINFRAME_linux_mainframe_cmd_check",
                  "configneid": "", "param": ""}, {"executive": "kmScript", "ctrlColId": "1005",
                                                   "function": "LINUX_LOGICALVOLUME_linux_logicalvolume_cmd_check",
                                                   "configneid": "", "param": ""},
                 {"executive": "kmScript", "ctrlColId": "1009",
                  "function": "LINUX_SWAPPARTITION_linux_swapparttion_cmd_check", "configneid": "", "param": ""},
                 {"executive": "kmScript", "ctrlColId": "1010",
                  "function": "LINUX_VOLUMEGROUP_linux_volumegroup_cmd_check", "configneid": "", "param": ""}]

        body = {"msgtype": "request",
                "business": "kmCheckScript",
                "body":
                    {
                        "neid": "900000012103258",
                        "inspectSessionId": "{0}".format(inspect_session_id),
                        "items": items
                    },
                "replyto": "itm.tom"
        }

        #         body = {"msgtype":"request",
        #                 "business":"cmdCtrl",
        #                 "body":
        #                 {
        #                         "neid":"{0}".format(neid),
        #                         "inspectSessionId":"{0}".format(inspect_session_id),
        #                         "items": "[{0}]".format(items)
        #                         }
        #                 }
        conn = BlockingConnection(self.params)
        channel = conn.channel()
        for i in xrange(10):
            result = channel.basic_publish(exchange=AMQ_EXCHANGE, routing_key=AMQ_ROUTINGKEY, body=json.dumps(body),
                                           properties=self.properties)
            if result:
                logging.info('delivery comfirmed')
                logging.info('publish result: {0}'.format(result))
            else:
                logging.info('delivery not confirmed')
                #         time.sleep(40)
        channel.close()
        conn.close()


#     @respond_handler('inspect (.*)$')
#     def auto_inspect(self, message, matches):
#         pass


if __name__ == '__main__':
    inspect = AutoInspect()
    inspect.auto_inspect()
