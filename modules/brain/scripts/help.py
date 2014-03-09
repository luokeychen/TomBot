#coding: utf-8
from engine import Engine, respond_handler


class Help(Engine):
    '''Tom help \t[filter]'''

    def __init__(self):
        # 帮助写死了，为了那么点方便搞这么麻烦不值得
        self.helps = '=======================指令列表======================\n'\
                'Tom help                 显示此信息\n'\
                'Tom?                     获取随机应答\n'\
                'Tom calc 1+1             计算器，支持四则运算、位运算等等\n'\
                'Tom flow 单号|标题       查询部门服务流程\n'\
                'Tom exec df -h           执行命令，服务器需预先配置\n'\
                'Tom 中文                 [联网]调戏用，智能回答，来自simsimi\n'\
                'Tom make me laugh        [联网]随机发送一则来自糗百的笑话\n'\
                'Tom mode cmd|normal|easy 切换命令模式与正常模式'

    @respond_handler('help')
    def respond(self, message, matches):
        message.send(self.helps)
