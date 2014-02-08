TomBot
=================
A chat robot written in Python

基础设施支持多种聊天工具的结合，只需写adapter

与Hubot不同的是一个服务端可以同时有多个聊天软件结合(现在还只支持一个)

虽然是用python写的，但是性能仍然很好

用到的技术
=================
用zeromq来支持进程间通信和程序内通信(SUB/PUB, PULL/PUSH),受益于zeromq，adapter与服务端主程序的通信是实时且异步的

用tornado支持异步并发(会考虑换成gevent)

Adapter
=================
adapter用zeromq实现通信,事实上adapter的编写很简单，因为zeromq支持40+种语言，所以语言不受限制，adapter只要开启两个后台线程，一个通过Publish/Subscribe模式发送消息到服务端，另一个线程用PULL/PUSH模式接收服务端消息， 并进行处理。

Adapter可以单独运行

Plugin
=================
可以编写插件拓展功能，自带几个插件：flow.py qiubai.py help.py calc.py ping.py
编写插件
----------
继承Engine, 类的docstring会被help.py读取并显示在help中，被respond_handler修饰的方法会在收到消息时自动调用，并匹配正则，matches参数可以使用matches.group(1)这样的方式获取括号中的匹配项
详见scripts目录下的template.py

Inspired by Hubot!

配置
===============
配置用yaml格式（其好处是可读性极强，且可以直接转换为python对象，使用方便
