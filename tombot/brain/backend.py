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
#  File        : backend.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : TomBot Backend用于处理消息及插件
import difflib
import os
import inspect
from collections import defaultdict, deque
import zmq
from zmq.eventloop import ioloop
import traceback

from tombot.brain import holder
from tombot.common import log, config
from tombot.common.threadpool import WorkRequest
from tombot.common.utils import split_string_after


ioloop.install()

from session import Room, RoomManager
from engine import botcmd

_path = os.path.abspath(os.path.dirname(__file__))

logger = log.logger


class ACLViolation(Exception):
    pass


# def check_command_access(self, mess, cmd):
#     """
#     Check command against ACL rules
#
#     Raises ACLViolation() if the command may not be executed in the given context
#     """
#     usr = str(get_jid_from_message(mess))
#     typ = mess.getType()
#
#     if cmd not in ACCESS_CONTROLS:
#         ACCESS_CONTROLS[cmd] = ACCESS_CONTROLS_DEFAULT
#
#     if 'allowusers' in ACCESS_CONTROLS[cmd] and usr not in ACCESS_CONTROLS[cmd]['allowusers']:
#         raise ACLViolation("You're not allowed to access this command from this user")
#     if 'denyusers' in ACCESS_CONTROLS[cmd] and usr in ACCESS_CONTROLS[cmd]['denyusers']:
#         raise ACLViolation("You're not allowed to access this command from this user")
#     if typ == 'groupchat':
#         stripped = mess.getFrom().getStripped()
#         if 'allowmuc' in ACCESS_CONTROLS[cmd] and ACCESS_CONTROLS[cmd]['allowmuc'] is False:
#             raise ACLViolation("You're not allowed to access this command from a chatroom")
#         if 'allowrooms' in ACCESS_CONTROLS[cmd] and stripped not in ACCESS_CONTROLS[cmd]['allowrooms']:
#             raise ACLViolation("You're not allowed to access this command from this room")
#         if 'denyrooms' in ACCESS_CONTROLS[cmd] and stripped in ACCESS_CONTROLS[cmd]['denyrooms']:
#             raise ACLViolation("You're not allowed to access this command from this room")
#     else:
#         if 'allowprivate' in ACCESS_CONTROLS[cmd] and ACCESS_CONTROLS[cmd]['allowprivate'] is False:
#             raise ACLViolation("You're not allowed to access this command via private message to me")
#
#     f = self.commands[cmd] if cmd in self.commands else self.re_commands[cmd]
#
#     if f._err_command_admin_only:
#         if typ == 'groupchat':
#             raise ACLViolation("You cannot administer the bot from a chatroom, message the bot directly")
#         if usr not in BOT_ADMINS:
#             raise ACLViolation("This command requires bot-admin privileges")


class Backend(object):
    cmd_history = defaultdict(lambda: deque(maxlen=10))

    MSG_ERROR_OCCURRED = '消息处理发生异常'
    MESSAGE_SIZE_LIMIT = config.max_message_size
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". ' \
                          'Type "' + config.main_name + 'help" for available commands.'
    MSG_HELP_TAIL = 'Type help <command names> to get more info ' \
                    'about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'That command is not defined.'

    def __init__(self, *args, **kwargs):
        context = zmq.Context(1)
        # 所有插件都应该使用这个socket，否则会自动负载均衡，破坏逻辑
        # TODO put broker_socket in holder
        if not holder.broker_socket:
            self.broker_socket = context.socket(zmq.DEALER)
            self.broker_socket.connect('ipc://{0}/broker.ipc'.format(config.ipc_path))
            holder.broker_socket = self.broker_socket
        else:
            self.broker_socket = holder.broker_socket

        self.names = tuple(name.lower() for name in config.names)

        self.room_manager = RoomManager()

        logger.info('Starting to load user...')

        if config.backend_count:
            from ..common.threadpool import ThreadPool

            self.thread_pool = ThreadPool(config.backend_count)
            logger.debug('Created the thread pool {0}'.format(self.thread_pool))

        self.commands = {}
        self.re_commands = {}
        self.sessions = {}
        self.admins = []

    def check_command_access(self, message, cmd):
        f = self.commands[cmd] if cmd in self.commands else self.re_commands[cmd]
        if f._tom_command_admin_only:
            if self.auth_admin(message):
                return True
            else:
                # message.warn('Command need admin privileges, please give me correct password!')
                raise ACLViolation('Command need admin privileges')

    def auth_admin(self, message):
        password = message.get_input('Please give me your pass code.')
        if password == config.admin_pass:
            self.admins.append(message.user)
            return True
        else:
            return False

    def get_commands(self):
        return self.commands

    def get_re_commands(self):
        return self.re_commands

    def unknown_command(self, mess, cmd, args):
        """ Override the default unknown command behavior
        """
        full_cmd = cmd + ' ' + args.split(' ')[0] if args else None
        if full_cmd:
            part1 = 'Command "%s" / "%s" not found.' % (cmd, full_cmd)
        else:
            part1 = 'Command "%s" not found.' % cmd
        underscore_keys = [m.replace('_', ' ') for m in self.commands.keys()]
        matches = difflib.get_close_matches(cmd, underscore_keys)
        if full_cmd:
            matches.extend(difflib.get_close_matches(full_cmd, underscore_keys))
        matches = set(matches)
        if matches:
            return part1 + '\n\nDid you mean "' + config.main_name + ' ' + ('" or "' + config.main_name + ' ').join(
                matches) + '" ?'
        else:
            return part1

    @staticmethod
    def send_simple_reply(message, text):
        message.send(text)

    def get_sender_username(self, mess):
        """
        override for special username convertion
        :param mess: Message object
        """
        # TODO Make it possible to convert from uin to QQ number.
        return mess.user

    def callback_message(self, mess):
        """
        Needs to return False if we want to stop further treatment
        """
        # Prepare to handle either private chats or group chats

        msg_type = mess.msg_type
        user = mess.user
        message_id = mess.message_id
        content = mess.content
        username = self.get_sender_username(mess)
        user_cmd_history = self.cmd_history[username]

        # 3 types of QQ chat, there's sess msg_type for non-friend talk, but with security issue, don't use it
        if msg_type not in ('buddy', 'group', 'discu', 'api'):
            logger.warn("unhandled message msg_type %s" % mess)
            return False

        logger.debug("*** Message_ID = %s" % message_id)
        logger.debug("*** user = %s" % user)
        # logger.debug("*** username = %s" % username)
        logger.debug("*** msg_type = %s" % msg_type)
        logger.debug("*** content = %s" % content)

        # If a message format is not supported (eg. encrypted),
        # txt will be None
        if not content:
            return False

        suppress_cad_not_found = False

        prefixed = False  # Keeps track whether content was prefixed with a bot prefix
        only_check_re_command = False  # Becomes true if content is determed to not be a regular command
        tomatch = content.lower()
        if len(self.names) > 0 and tomatch.startswith(self.names):
            # Yay! We were called by one of our alternate prefixes. Now we just have to find out
            # which one... (And find the longest matching, in case you have 'err' and 'errbot' and
            # someone uses 'errbot', which also matches 'err' but would leave 'bot' to be taken as
            # part of the called command in that case)
            prefixed = True
            longest = 0
            for name in self.names:
                l = len(name)
                if tomatch.startswith(name) and l > longest:
                    longest = l
            logger.debug("Called with alternate name '{}'".format(content[:longest]))
            content = content[longest:]

            # Now also remove the separator from the content
            for sep in config.bot_alt_separators:
                # While unlikely, one may have separators consisting of
                # more than one character
                l = len(sep)
                if content[:l] == sep:
                    content = content[l:]
        elif not content.startswith(config.prefix):
            only_check_re_command = True
        if content.startswith(config.prefix):
            content = content[len(config.prefix):]
            prefixed = True

        content = content.strip()
        text_split = content.split(' ')
        cmd = None
        command = None
        args = ''
        if not only_check_re_command:
            if len(text_split) > 1:
                command = (text_split[0] + '_' + text_split[1]).lower()
                if command in self.commands:
                    cmd = command
                    args = ' '.join(text_split[2:])

            if not cmd:
                command = text_split[0].lower()
                args = ' '.join(text_split[1:])
                if command in self.commands:
                    cmd = command
                    if len(text_split) > 1:
                        args = ' '.join(text_split[1:])

            if content == '!':  # we did "!!" so recall the last command
                if len(user_cmd_history):
                    cmd, args = user_cmd_history[-1]
                else:
                    return False  # no command in history
            elif content and content.isdigit():  # we did "!#" so we recall the specified command
                index = int(content)
                if len(user_cmd_history) >= index:
                    cmd, args = user_cmd_history[-index]
                else:
                    return False  # no command in history

        # Try to match one of the regex commands if the regular commands produced no match
        matched_on_re_command = False
        if not cmd:
            if prefixed:
                commands = self.re_commands
            else:
                commands = {k: self.re_commands[k] for k in self.re_commands
                            if not self.re_commands[k]._tom_command_prefix_required}

            for name, func in commands.items():
                match = func._tom_command_re_pattern.search(content)
                if match:
                    logger.debug(u"Matching '{}' against '{}' produced a match"
                                 .format(content, func._tom_command_re_pattern.pattern))
                    matched_on_re_command = True
                    self._process_command(mess, name, content, match)
                else:
                    logger.debug(u"Matching '{}' against '{}' produced no match"
                                 .format(content, func._tom_command_re_pattern.pattern))
        if matched_on_re_command:
            return True

        if cmd:
            self._process_command(mess, cmd, args, match=None)
        elif not only_check_re_command:
            logger.debug("Command not found")
            if suppress_cad_not_found:
                logger.debug("Surpressing command not found feedback")
            else:
                reply = self.unknown_command(mess, command, args)
                if reply is None:
                    reply = self.MSG_UNKNOWN_COMMAND % {'command': command}
                if reply:
                    self.send_simple_reply(mess, reply)

        return True

    def _process_command(self, mess, cmd, args, match):
        """Process and execute a bot command"""
        logger.info(u"Processing command {} with parameters '{}'".format(cmd, args))

        user = mess.user
        username = self.get_sender_username(mess)
        user_cmd_history = self.cmd_history[username]

        if (cmd, args) in user_cmd_history:
            user_cmd_history.remove((cmd, args))  # Avoids duplicate history items

        # FIXME There's no ACL control at this time
        try:
            self.check_command_access(mess, cmd)
        except ACLViolation as e:
            self.send_simple_reply(mess, str(e))
            return

        f = self.re_commands[cmd] if match else self.commands[cmd]

        if f._tom_command_admin_only:
            self.thread_pool.wait()  # If it is an admin command, wait that the queue is completely depleted so we don't have strange concurrency issues on load/unload/updates etc ...

        if f._tom_command_historize:
            user_cmd_history.append((cmd, args))  # add it to the history only if it is authorized to be so
            mess.session['history'].append((cmd, args))

        # Don't check for None here as None can be a valid argument to split.
        # '' was chosen as default argument because this isn't a valid argument to split()
        if not match and f._tom_command_split_args_with != '':
            args = args.split(f._tom_command_split_args_with)
        wr = WorkRequest(self._execute_and_send,
            [], {'cmd': cmd, 'args': args, 'match': match, 'mess': mess, 'user': user})
        self.thread_pool.put_request(wr)
        if f._tom_command_admin_only:
            self.thread_pool.wait()  # Again wait for the completion before accepting a new command that could generate weird concurrency issues

    def _execute_and_send(self, cmd, args, match, mess, user):
        """Execute a bot command and send output back to the caller

        cmd: The command that was given to the bot (after being expanded)
        args: Arguments given along with cmd
        match: A re.MatchObject if command is coming from a regex-based command, else None
        mess: The message object
        jid: The jid of the person executing the command
        template_name: The names of the template which should be used to render
            html-im output, if any

        """

        def process_reply(reply):
            # integrated templating
            # if template_name:
            #     reply = tenv().get_template(template_name + '.html').render(**reply)

            # Reply should be all text at this point (See https://github.com/gbin/err/issues/96)
            return str(reply)

        def send_reply(reply):
            if mess.msg_type == 'api' or (reply) <= self.MESSAGE_SIZE_LIMIT:
                self.send_simple_reply(mess, reply)
            else:
                mess.session['outbox'] = split_string_after(reply, self.MESSAGE_SIZE_LIMIT)
                mess.send_next()

        commands = self.re_commands if match else self.commands
        try:
            if inspect.isgeneratorfunction(commands[cmd]):
                replies = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                for reply in replies:
                    if reply:
                        send_reply(process_reply(reply))
            else:
                reply = commands[cmd](mess, match) if match else commands[cmd](mess, args)
                if reply:
                    send_reply(process_reply(reply))
        except Exception as e:
            tb = traceback.format_exc()
            logger.exception('An error happened while processing '
                             'a message ("%s") from %s: %s"' %
                             (mess.content, mess.user, tb))
            send_reply(self.MSG_ERROR_OCCURRED + ':\n %s' % e)

    def serve_forever(self):
        """
        Must be override

        :raise NotImplementedError:
        """
        raise NotImplementedError

    def create_room(self, rid, rtype):
        """
        create room if not exist

        :param rid: room id
        :param rtype: room type
        :return: Room instance
        """
        if not self.room_manager.get_room(rid):
            room = Room(rid)
            self.room_manager.add_room(room)
            room.rtype = rtype
        else:
            room = self.room_manager.get_room(rid)

        return room

    def inject_commands_from(self, instance_to_inject):
        """

        :param instance_to_inject: instance that contain @botcmd decorated commands, can be `self`
                                    user can use holder.bot.inject_commands_from(self)  to inject commands for current
                                    class instance
        """
        classname = instance_to_inject.__class__.__name__
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_tom_command', False):
                commands = self.re_commands if getattr(value, '_tom_re_command') else self.commands
                name = getattr(value, '_tom_command_name')

                if name in commands:
                    f = commands[name]
                    new_name = (classname + '-' + name).lower()
                    self.warn_admins('%s.%s clashes with %s.%s so it has been renamed %s' % (
                        classname, name, type(f.__self__).__name__, f.__name__, new_name))
                    name = new_name
                commands[name] = value

                if getattr(value, '_tom_re_command'):
                    logger.debug('Adding regex command : %s -> %s' % (name, value.__name__))
                    self.re_commands = commands
                else:
                    logger.debug('Adding command : %s -> %s' % (name, value.__name__))
                    self.commands = commands

    def remove_commands_from(self, instance_to_inject):
        for name, value in inspect.getmembers(instance_to_inject, inspect.ismethod):
            if getattr(value, '_tom_command', False):
                name = getattr(value, '_tom_command_name')
                if getattr(value, '_tom_re_command') and name in self.re_commands:
                    del (self.re_commands[name])
                elif not getattr(value, '_tom_re_command') and name in self.commands:
                    del (self.commands[name])

    def warn_admins(self, warning):
        pass
        # for admin in config.admins:
        #     self.send(admin, warning)

    def top_of_help_message(self):
        """Returns a string that forms the top of the help message

        Override this method in derived class if you
        want to add additional help text at the
        beginning of the help message.
        """
        return ""

    def bottom_of_help_message(self):
        """Returns a string that forms the bottom of the help message

        Override this method in derived class if you
        want to add additional help text at the end
        of the help message.
        """
        return ""
