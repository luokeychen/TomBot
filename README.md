TomBot
=================
A chat robot written in Python

基础设施支持多种聊天工具的结合，只需写adapter

与Hubot不同的是一个服务端可以同时有多个聊天软件结合(现在还只支持一个)

虽然是用python写的，但是性能仍然很好

用到的技术
=================
用zeromq来支持进程间通信和程序内通信(SUB/PUB, PULL/PUSH),受益于zeromq，adapter与服务端主程序的通信是实时且异步的

用tornado支持异步并发
update: 2013-3-8 换成gevent以后，如果第三方库没有兼容gevent，容易出现莫名其妙的问题，换回tornado

Adapter
=================
adapter用zeromq实现通信,事实上adapter的编写很简单，因为zeromq支持40+种语言，所以语言不受限制，adapter只要开启两个后台线程，一个通过Publish/Subscribe模式发送消息到服务端，另一个线程用PULL/PUSH模式接收服务端消息， 并进行处理。

Adapter可以单独运行

Plugin
=================
可以编写插件拓展功能，自带几个插件：flow.py qiubai.py help.py calc.py ping.py
编写插件
----------
继承Engine, 类的docstring会被help.py读取并显示在help中，被`respond_handler`修饰的方法会在收到消息时自动调用，并匹配正则，matches参数可以使用matches.group(1)这样的方式获取括号中的匹配项
详见scripts目录下的template.py

Inspired by Hubot!

配置
===============
配置用yaml格式（其好处是可读性极强，且可以直接转换为python对象，使用方便

更新记录
===============
 * 2014-3-8 gevent对第三方库要求高，一不小心就容易出问题，换回tornado
 * 2014-3-8 twqq自身已添加讨论组功能，废除自己fork的版本
 * 2014-3-8 修改了客户端机制，应该能长时间在线了（参考了`paul_bot`)
 * 2014-3-8 初步添加针对房间的属性管理
 * 2014-3-9 内部通信改为纯json，因此废除了topic机制（因为没办法用了。。。）

TODO
==============
 * 统一unicode编码（除zmq收发消息外） done
 * 发送提醒邮件及http方式输入验证码（参考`paul_bot`)
 * 添加数据库支持
 * 发送消息支持定义字体风格
 * 完善插件异常处理机制
 * 增加权限管理
 * 添加易用的运维功能 
 * 添加多机命令执行功能 done
 * SSH
 * 考虑增强zmq的安全性
