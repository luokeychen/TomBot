#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#  Copyright (C) 2014 konglx
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY konglx ''AS IS'' AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL konglx BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : enging.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : engine for TomBot


import json
import inspect
import sys
from Queue import Queue, Empty
import textwrap
import logging
import os
from threading import Timer, current_thread

from helpers import make_msg
from session import Session
from brain import StoreMixin
from utils import PLUGINS_SUBDIR, recurse_check_structure
from brain import StoreMixin, StoreNotOpenError
import holder
import const
import log
import config

logger = log.logger

respond_handlers = {}

def botcmd(*args, **kwargs):
    def decorate(func, hidden=False, name=None, split_args_with='', admin_only=False, historize=True, template=None):
        if not hasattr(func, '_tom_command'):  # don't override generated functions
            setattr(func, '_tom_command', True)
            setattr(func, '_tom_re_command', False)
            setattr(func, '_tom_command_hidden', hidden)
            setattr(func, '_tom_command_name', name or func.__name__)
            setattr(func, '_tom_command_split_args_with', split_args_with)
            setattr(func, '_tom_command_admin_only', admin_only)
            setattr(func, '_tom_command_historize', historize)
            setattr(func, '_tom_command_template', template)
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)


def re_botcmd(*args, **kwargs):
    def decorate(func, pattern, flags=0, prefixed=True, hidden=False, name=None, admin_only=False, historize=True, template=None):
        if not hasattr(func, '_tom_command'):  # don't override generated functions
            setattr(func, '_tom_command', True)
            setattr(func, '_tom_re_command', True)
            setattr(func, '_tom_command_re_pattern', re.compile(pattern, flags=flags))
            setattr(func, '_tom_command_prefix_required', prefixed)
            setattr(func, '_tom_command_hidden', hidden)
            setattr(func, '_tom_command_name', name or func.__name__)
            setattr(func, '_tom_command_admin_only', admin_only)
            setattr(func, '_tom_command_historize', historize)
            setattr(func, '_tom_command_template', template)
        return func

    if len(args):
        return decorate(args[0], **kwargs)
    else:
        return lambda func: decorate(func, **kwargs)

def plugin(cls):
    cls.__plugin__ = True
    return cls


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    :param socket: pull模式的zmq socket
    '''

    #retcode: 0 normal 101 warn 102 error 1001 null
    def __init__(self, message, socket):
        self.msg = message
        self.identity = message[0]
        self.content, self.id_, self.type_, self.user = message[1:]
        self.socket = socket

    def _split_chunk(self, string, length):
        if length >= 4096:
            logger.warn('分页长度过长，可能无法发送')

        lines = textwrap.wrap(string, width=length)
        return lines

    def _get_input(self):
        session = Session(self.msg.id_, self.msg.user)
        session['iswait'] = True

        try:
            message = queue.get(timeout=10)
            user_input = message.content
            session['iswait'] = False
            session.save()
            return user_input
        except Empty:
            session['iswait'] = False
            session.save()

        session['iswait'] = False
        session.save()
        msg.send('由于未知原因，无法读取用户输入')

    def get_type(self):
        return self.type_
    
    def get_from(self):
        return self.id_

    def get_body(self):
        return self.content

    def send(self, content, style=const.DEFAULT_STYLE, retcode=0, user=None, split=0):
        if not content:
            content = '执行结果为空'
            style = const.ERROR_STYLE

        if split > 0:
            lines = self._split_chunk(content, split)
            for line in lines:
                pass
        elif len(content) > 4096:
            warn_msg = make_msg(1, '消息过长，只显示部分内容',
                                self.id_, self.type_, self.user, const.WARNING_STYLE)

            self.socket.send_multipart([self.identity,
                                        json.dumps(warn_msg)])
            content = content[:4096]
        msg = make_msg(retcode, content, self.id_, self.type_, self.user, style)

        self.socket.send_multipart([self.identity,
                                    json.dumps(msg)])

        logger.info('推送消息到adapter: {0!r}'.format(msg))

    def ok(self, content):
        self.send(content, style=const.OK_STYLE, retcode=0)

    def info(self, content):
        self.send(content, style=const.INFO_STYLE)

    def warn(self, content):
        self.send(content, style=const.WARNING_STYLE, retcode=101)

    def error(self, content):
        self.send(content, style=const.ERROR_STYLE, retcode=102)

    def code(self, content):
        self.send(content, style=const.CODE_STYLE)


class Respond(object):
    '''
    响应器，用于注册及获取响应函数
    '''
    def __init__(self):
        self.respond_map = {}
        self.plugin = self._get_caller_module()
        logger.error(self.plugin)

    def register(self, pattern):
        '''消息响应装饰器

        :param pattern: pattern应是一个合法的正则表达式
        '''
        # BUG 无法获取wrap前的函数名，functools也不行
        def wrapper(func, *args, **kwargs):
            queue = Queue(1)
            self.respond_map[pattern] = func, queue
            return func
        return wrapper

    def get_respond(self, pattern):
        func = self.respond_map.get(pattern, None)
        if func is None:
            logger.warn('未注册响应器:{0}'.format(pattern))
        else:
            return func

    # FIXME 这种方式可能导致不同Python实现的移植问题
    @staticmethod
    def _get_caller_module():
        stack = inspect.stack()
        parentframe = stack[2][0]

        module = inspect.getmodule(parentframe)

        return module

    # FIXME 这种方式可能导致不同Python实现的移植问题
    @staticmethod
    def _get_caller(skip=2):
        stack = inspect.stack()
        start = 0 + skip
        if len(stack) < start + 1:
            return ''
        parentframe = stack[start][0]
        name = None
        codename = parentframe.f_code.co_name

        if codename != '<module>': # top level usually
            name = codename
        del parentframe
        return name

    def get_input(self, msg):
#         session_id = Session.generate_session_id(msg.id_, msg.user)
        session = Session(msg.id_, msg.user)
        # get caller
        caller = self._get_caller()
        # get caller instance
        instance = inspect.currentframe().f_back.f_locals['self']
        caller = getattr(instance, caller)
        # set session
        session['iswait'] = True

        for pattern, (func, queue) in self.respond_map.items():
            if func == caller:
                session['last'] = [pattern for (pattern, func) in self.respond_map.iteritems() if func == func][0]
                session.save()
                try:
                    logger.info('服务器正在等待用户输入')
                    message = queue.get(timeout=5)
                    user_input = message.content
                    session['iswait'] = False
                    session.save()
                    return user_input
                except Empty:
                    session['iswait'] = False
                    session.save()
                    msg.send(u'输入超时，任务取消')
                    return None

        session['iswait'] = False
        session.save()
        msg.send('由于未知原因，无法读取用户输入')


class EngineBase(StoreMixin):
    """
     This class handle the basic needs of bot plugins like loading, unloading and creating a storage
     It is the main contract between the plugins and the bot
    """

    def __init__(self):
        self.plugin_dir = holder.bot.plugin_dir
        self.is_activated = False
        self.current_pollers = []
        self.current_timers = []
        super(EngineBase, self).__init__()

    def activate(self):
        """
            Override if you want to do something at initialization phase (don't forget to super(Gnagna, self).activate())
        """
        data_dir = config.home + '/run/data'

        classname = self.__class__.__name__
        logging.debug('Init storage for %s' % classname)
        filename = data_dir + os.sep + PLUGINS_SUBDIR + os.sep + classname + '.db'
        logging.debug('Loading %s' % filename)
        self.open_storage(filename)
        holder.bot.inject_commands_from(self)
        self.is_activated = True

    def deactivate(self):
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        if self.current_pollers:
            logging.debug('You still have active pollers at deactivation stage, I cleaned them up for you.')
            self.current_pollers = []
            for timer in self.current_timers:
                timer.cancel()

        try:
            self.close_storage()
        except StoreNotOpenError:
            pass
        holder.bot.remove_commands_from(self)
        self.is_activated = False

    def start_poller(self, interval, method, args=None, kwargs=None):
        if not kwargs:
            kwargs = {}
        if not args:
            args = []

        logging.debug('Programming the polling of %s every %i seconds with args %s and kwargs %s' % (method.__name__, interval, str(args), str(kwargs)))
        #noinspection PyBroadException
        try:
            self.current_pollers.append((method, args, kwargs))
            self.program_next_poll(interval, method, args, kwargs)
        except Exception as _:
            logging.exception('failed')

    def stop_poller(self, method, args=None, kwargs=None):
        if not kwargs:
            kwargs = {}
        if not args:
            args = []
        logging.debug('Stop polling of %s with args %s and kwargs %s' % (method, args, kwargs))
        self.current_pollers.remove((method, args, kwargs))

    def program_next_poll(self, interval, method, args, kwargs):
        t = Timer(interval=interval, function=self.poller, kwargs={'interval': interval, 'method': method, 'args': args, 'kwargs': kwargs})
        self.current_timers.append(t)  # save the timer to be able to kill it
        t.setName('Poller thread for %s' % type(method.__self__).__name__)
        t.setDaemon(True)  # so it is not locking on exit
        t.start()

    def poller(self, interval, method, args, kwargs):
        previous_timer = current_thread()
        if previous_timer in self.current_timers:
            logging.debug('Previous timer found and removed')
            self.current_timers.remove(previous_timer)

        if (method, args, kwargs) in self.current_pollers:
            #noinspection PyBroadException
            try:
                method(*args, **kwargs)
            except Exception as _:
                logging.exception('A poller crashed')
            self.program_next_poll(interval, method, args, kwargs)


class Engine(EngineBase):
    @property
    def min_err_version(self):
        """ If your plugin has a minimum version of err it needs to be on in order to run, please override accordingly this method.
        returning a string with the dotted minimum version. it MUST be in a 3 dotted numbers format or None
        for example: "1.2.2"
        """
        return None

    @property
    def max_err_version(self):
        """ If your plugin has a maximal version of err it needs to be on in order to run, please override accordingly this method.
        returning a string with the dotted maximal version. it MUST be in a 3 dotted numbers format or None
        for example: "1.2.2"
        """
        return None

    def get_configuration_template(self):
        """ If your plugin needs a configuration, override this method and return a configuration template.
        for example a dictionary like:
        return {'LOGIN' : 'example@example.com', 'PASSWORD' : 'password'}
        Note : if this method returns None, the plugin won't be configured
        """
        return None

    def check_configuration(self, configuration):
        """ By default, this method will do only a BASIC check. You need to override it if you want to do more complex checks.
        It will be called before the configure callback. Note if the config_template is None, it will never be called
        It means recusively:
        1. in case of a dictionary, it will check if all the entries and from the same type are there and not more
        2. in case of an array or tuple, it will assume array members of the same type of first element of the template (no mix typed is supported)

        In case of validation error it should raise a errbot.utils.ValidationException

        """
        recurse_check_structure(self.get_configuration_template(), configuration)  # default behavior

    def configure(self, configuration):
        """ By default, it will just store the current configuation in the self.config field of your plugin
        If this plugin has no configuration yet, the framework will call this function anyway with None
        This method will be called before activation so don't expect to be activated at that point
        """
        self.config = configuration

    def activate(self):
        """
            Override if you want to do something at initialization phase (don't forget to super(Gnagna, self).activate())
        """
        super(Engine, self).activate()

    def deactivate(self):
        """
            Override if you want to do something at tear down phase (don't forget to super(Gnagna, self).deactivate())
        """
        super(Engine, self).deactivate()

    def callback_connect(self):
        """
            Override to get a notified when the bot is connected
        """
        pass

    def callback_message(self, conn, mess):
        """
            Override to get a notified on *ANY* message.
            If you are interested only by chatting message you can filter for example mess.getType() in ('groupchat', 'chat')
        """
        pass

    def callback_botmessage(self, mess):
        """
            Override to get a notified on messages from the bot itself (emitted from your plugin sisters and brothers for example).
        """
        pass

    def callback_contact_online(self, conn, pres):
        """
            Override to get a notification when a contact becomes online.
        """
        pass

    def callback_contact_offline(self, conn, pres):
        """
            Override to get notified when a contact becomes offline.
        """
        pass

    def callback_user_joined_chat(self, conn, pres):
        """
            Override to get notified when any user joins a chatroom or an equivalent.
        """
        pass

    def callback_user_left_chat(self, conn, pres):
        """
            Override to get notified when any user leaves a chatroom or an equivalent.
        """
        pass

    # Proxyfy some useful tools from the motherbot
    # this is basically the contract between the plugins and the main bot

    def warn_admins(self, warning):
        """
            Sends a warning to the administrators of the bot
        """
        return holder.bot.warn_admins(warning)

    def send(self, user, text, in_reply_to=None, message_type='chat'):
        """
            Sends asynchronously a message a room or a user.
             if it is a room message_type needs to by 'groupchat' and user the room.
        """
        return holder.bot.send(user, text, in_reply_to, message_type)

    def bare_send(self, xmppy_msg):
        """
            A bypass to send directly a crafted xmppy message.
              Usefull to extend to bot in not forseen ways.
        """
        c = holder.bot.connect()
        if c:
            return c.send(xmppy_msg)
        logging.warning('Ignored a message as the bot is not connected yet')
        return None  # the bot is not connected yet

    def join_room(self, room, username=None, password=None):
        """
            Make the bot join a room
        """
        return holder.bot.join_room(room, username, password)

    def invite_in_room(self, room, jids_to_invite):
        """
            Make the bot invite a list of jids to a room
        """
        return holder.bot.invite_in_room(room, jids_to_invite)


    def get_installed_plugin_repos(self):
        """
            Get the current installed plugin repos in a dictionary of name / url
        """
        return holder.bot.get_installed_plugin_repos()

    def start_poller(self, interval, method, args=None, kwargs=None):
        """
            Start to poll a method at specific interval in seconds.
            Note : it will call the method with the initial interval delay for the first time
            Also, you can program
            for example : self.program_poller(self,30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin
        """
        super(Engine, self).start_poller(interval, method, args, kwargs)

    def stop_poller(self, method=None, args=None, kwargs=None):
        """
            stop poller(s).
            if the method equals None -> it stops all the pollers
            you need to regive the same parameters as the original start_poller to match a specific poller to stop
        """
        super(Engine, self).stop_poller(method, args, kwargs)

