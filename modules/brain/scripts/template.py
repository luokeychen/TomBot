#coding: utf-8
from engine import Engine

# 类名及脚本名写到scripts.json中，以启用脚本
# 在docstring定义的字符串，将会在help.py脚本中得到并展示出来
class Template(Engine):
    '''用法描述'''
    def __init__(self):
        # 调用父类(Engine)的构造方法，第一个参数始终是类名
        super(Template, self).__init__()
        # 订阅的消息过滤器，以此字符串开头的消息，才会传入到这个脚本
        # 必须添加至少一个topic('')，否则收不到消息,这也是zeromq的限制，
        #最好根据实际情况定义， 以减少收到消息的量，
        #在处理量大的时候，会有用
        # 可以添加多个topic，没有限制
        self.add_topic('template')
        ...


    def respond(self, message, regexp=None):
        # 这个方法会在每次收到消息时自动调用，用来响应请求
        # regexp是正则表达式，可以用它过滤获取到的消息
        # message是一个Message对象，定义在engine.py中，它进行了一点点封装，
        # 使得调用者不需要指定发送对象及类型，始终会回复到正确的消息来源
        message.send(...)

# 你可以载入配置文件，请放在conf.d目录下
