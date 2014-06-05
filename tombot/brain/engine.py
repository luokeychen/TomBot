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
import Queue
import json
import textwrap
import logging
import os
import re
from uuid import uuid1
from threading import Timer, current_thread

from helpers import make_msg
import holder
from tombot.common import log, config
from storage import StoreMixin, StoreNotOpenError
import const


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
    def decorate(func, pattern, flags=re.IGNORECASE, prefixed=True, hidden=False, name=None, admin_only=False,
                 historize=True,
                 template=None):
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


class InvalidMessageError(Exception):
    pass


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    '''

    #retcode: 0 normal 101 warn 102 error 1001 null
    def __init__(self, message):
        self.msg = message
        if len(message) < 2:
            raise InvalidMessageError('Message length is {}, expect 2'.format(len(message)))
        self.identity = message[0]
        self._data = json.loads(message[1]) if isinstance(message[1], str) else message[1]

        self._data['message_id'] = str(uuid1())

        # could be plain or html, default plain
        self.html = None
        self._data['html'] = None
        self._data['style'] = self._data.get('style') or const.DEFAULT_STYLE
        self.socket = holder.broker_socket
        self.session = None


    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, item):
        return self._data.get(item)

    def get_input(self, tip=None):
        if tip:
            self.info(tip)
        self.session['is_wait'] = True
        try:
            user_input = self.session.queue.get(timeout=10)
        except Queue.Empty:
            self.warn('Input timeout, task canceled')
            return None
        finally:
            self.session['is_wait'] = False

        return user_input

    def send_next(self):
        if not self.session['outbox']:
            self.info('No more content to display.')
        else:
            try:
                out_msg = self.session['outbox'].next()
                # out_msg += '\nType more to see more details.'
                self.send(out_msg)
            except StopIteration:
                self.warn('No more content to display.')

    def send(self, content, retcode=0):
        # if not isinstance(self.content, str) or not isinstance(self.content, unicode):
        #     logger.warn('Message content is not `str` or `unicode`, can not be send!')
        #     return
        if not content:
            content = '执行结果为空'
            style = const.ERROR_STYLE

        # for QQ, too long message may block by tencent
        # elif len(content) > 4096:
        #     warn_msg = make_msg(1, '消息过长，只显示部分内容', self.user,
        #                         self.msg_type, self.id, const.WARNING_STYLE)
        #
        #     self.socket.send_multipart([self.identity,
        #                                 json.dumps(warn_msg)])
        #     content = content[:4096]
        # msg = make_msg(retcode=retcode, content=content, user=self.user,
        #                type_=self.msg_type, id_=self.id, style=self.style)
        self._data['content'] = str(content)
        self._data['retcode'] = retcode
        self.socket.send_multipart([self.identity,
                                    json.dumps(self._data)])

        logger.info('Push message to Client: {0!r}'.format(self._data))

    def ok(self, content):
        self.send(content, retcode=0)

    def info(self, content):
        self.send(content)

    def warn(self, content):
        self.send(content, retcode=101)

    def error(self, content):
        self.send(content, retcode=102)

    def code(self, content):
        self.send(content)


class EngineBase(StoreMixin):
    """
     This class handle the basic needs of bot plugin like loading, unloading and creating a storage
     It is the main contract between the user and the bot
    """

    def __init__(self):
        #self.plugin_dir = holder.bot.plugin_dir
        self.is_activated = False
        self.current_pollers = []
        self.current_timers = []
        super(EngineBase, self).__init__()

    def activate(self):
        """
            Override if you want to do something at initialization phase (don't forget to super(Gnagna, self).activate())
        """
        data_dir = config.home + '/run/'

        classname = self.__class__.__name__
        logging.debug('Init storage for %s' % classname)
        filename = data_dir + os.sep + 'plugins' + os.sep + classname + '.db'
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

        logging.info('Programming the polling of %s every %i seconds with args %s and kwargs %s' % (
            method.__name__, interval, str(args), str(kwargs)))
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
        t = Timer(interval=interval, function=self.poller,
                  kwargs={'interval': interval, 'method': method, 'args': args, 'kwargs': kwargs})
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

    def callback_message(self, message):
        """
            Override to get a notified on *ANY* message.
            If you are interested only by chatting message you can filter for example message.getType() in ('groupchat', 'chat')
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
    # this is basically the contract between the user and the main bot

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
        return holder.bot.send(user, in_reply_to, message_type)

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
            Get the current installed plugin repos in a dictionary of names / url
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


class BuiltinEngine(EngineBase):
    """Only used to make difference with user plugin and ansible plugin"""

    def __init__(self):
        super(BuiltinEngine, self).__init__()

    def callback_connect(self):
        """
            Override to get a notified when the bot is connected
        """
        pass

    def callback_message(self, message):
        """
            Override to get a notified on *ANY* message.
            If you are interested only by chatting message you can filter for example message.getType() in ('groupchat', 'chat')
            Threre's no threading support with this, so dont put any block code here.
        """
        pass

    def start_poller(self, interval, method, args=None, kwargs=None):
        """
            Start to poll a method at specific interval in seconds.
            Note : it will call the method with the initial interval delay for the first time
            Also, you can program
            for example : self.program_poller(self,30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin
        """
        super(BuiltinEngine, self).start_poller(interval, method, args, kwargs)

    def stop_poller(self, method=None, args=None, kwargs=None):
        """
            stop poller(s).
            if the method equals None -> it stops all the pollers
            you need to regive the same parameters as the original start_poller to match a specific poller to stop
        """
        super(BuiltinEngine, self).stop_poller(method, args, kwargs)


class AnsibleEngine(EngineBase):
    def __init__(self):
        super(AnsibleEngine, self).__init__()

    def callback_connect(self):
        """
            Override to get a notified when the bot is connected
        """
        pass

    def callback_message(self, message):
        """
            Override to get a notified on *ANY* message.
            If you are interested only by chatting message you can filter for example message.getType() in ('groupchat', 'chat')
        """
        pass

    def start_poller(self, interval, method, args=None, kwargs=None):
        """
            Start to poll a method at specific interval in seconds.
            Note : it will call the method with the initial interval delay for the first time
            Also, you can program
            for example : self.program_poller(self,30, fetch_stuff)
            where you have def fetch_stuff(self) in your plugin
        """
        super(AnsibleEngine, self).start_poller(interval, method, args, kwargs)

    def stop_poller(self, method=None, args=None, kwargs=None):
        """
            stop poller(s).
            if the method equals None -> it stops all the pollers
            you need to regive the same parameters as the original start_poller to match a specific poller to stop
        """
        super(AnsibleEngine, self).stop_poller(method, args, kwargs)
