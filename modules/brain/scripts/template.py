# coding: utf-8
from engine import Engine, respond_handler

# 类名及脚本名写到config.yaml的plugins列表下，以启用脚本
# 在docstring定义的字符串，将会在help.py脚本中得到并展示出来
class Template(Engine):
    '''用法描述'''
    def __init__(self):
        '''订阅的消息过滤器，以此字符串开头的消息，才会传入到这个脚本
        必须添加至少一个topic，否则收不到消息,这也是zeromq的限制，如果topic中有空字符串，那么会收到所有消息
        最好根据实际情况定义， 以减少收到消息的量，
        在处理量大的时候，会有用
        可以添加多个topic，没有限制
        '''
        self.topics[ 'template' ]

        # 其他初始化


    @respond_handler('regexp here')
    def respond(self, message, matches):
        '''被respond_handler装饰的方法会在每次收到消息时自动调用，用来响应请求
        respond_handler接受一个正则表达式作为参数，可以用它过滤获取到的消息，未匹配到的话，不会执行
        如果正则表达式有进行分组，那么分组对象会传入给本方法，用matches.group(1)这样的方式访问

        可以有多个被respond_handler装饰的方法，会依次执行

        message是一个Message对象，定义在engine.py中，它进行了一点点封装，
        使得调用者不需要指定发送对象及类型，始终会回复到正确的消息来源

        如果这个方法里的处理逻辑会执行很久，希望控制超时时间，可以这样做：
        from utils import timout, TimeoutException
        @timeout(1)
        def long_execute_mthod(....)
        然后在调用该方法时捕获TimeoutException异常,参考calc.py
        这种时候方法会被放入一个单独的进程中执行，请控制这种方法的数量
        '''

        # 这里编写处理逻辑
        message.send('...')

# 你可以载入配置文件，请放在conf.d目录下
