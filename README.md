TomBot
=================
A chat robot written in Python

基础设施支持多种聊天工具的结合，只需写adapter

与Hubot不同的是一个服务端可以同时有多个聊天软件结合

虽然是用python写的，但是性能仍然很好

用到的技术
=================
用zeromq来支持进程间通信和程序内通信(SUB/PUB, PULL/PUSH),受益于zeromq，adapter与服务端主程序的通信是实时且异步的

用gevent支持异步并发

Adapter
=================
adapter用zeromq实现通信,事实上adapter的编写很简单，因为zeromq支持40+种语言，所以语言不受限制，adapter只要开启两个后台线程，一个通过Publish/Subscribe模式发送消息到服务端，另一个线程用PULL/PUSH模式接收服务端消息， 并进行处理。

Adapter可以单独运行，并且可以同时运行多个

Plugin
=================
可以编写插件拓展功能，自带几个插件：help.py calc.py ping.py
编写插件
----------
继承Engine, 类的docstring会被help.py读取并显示在help中，重写respond方法，用regex修饰器来匹配输入，正则被修饰器预处理，respond的matches参数可以使用matches.group(1)这样的方式获取括号中的匹配项

Inspired by Hubot!
