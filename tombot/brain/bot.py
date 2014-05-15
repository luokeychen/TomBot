# -*- coding:utf-8 -*-
import os
import gc
from datetime import datetime
import inspect
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream

ioloop.install()

from tombot.brain.backend import Backend
from tombot.brain.storage import StoreMixin
from tombot.brain.engine import botcmd
from tombot.brain.engine import Message
from tombot.common import config
from tombot.brain import holder
from tombot.common import log
from tombot.common.utils import tail, format_timedelta
from tombot.brain.session import Session, store
from tombot.brain.plugin import (
    get_all_active_plugin_names, deactivate_all_plugins, get_all_active_plugin_objects,
    get_all_plugins, global_restart, get_all_plugin_names, deactivate_plugin_by_name, activate_plugin_by_name,
    get_plugin_obj_by_name, reload_plugin_by_name, update_plugin_places, get_plugin_by_name
)

BL_PLUGINS = b'bl_plugins'

logger = log.logger


def get_class_that_defined_method(meth):
    for cls in inspect.getmro(type(meth.__self__)):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


__author__ = 'Konglx'


class TomBot(Backend, StoreMixin):
    __tomdoc__ = """ Commands related to the bot administration """
    startup_time = datetime.now()

    def __init__(self, *args, **kwargs):
        self.loop = ioloop.IOLoop().instance()
        data_dir = config.home + '/run/'
        self.open_storage(data_dir + 'bot.db')
        self.prefix = config.name
        self.all_candidates = None
        super(TomBot, self).__init__(*args, **kwargs)

        # def update_dynamic_plugins(self):
        # all_candidates, errors = update_plugin_places([self.plugin_dir + os.sep + d for d in self.get(REPOS, {}).keys()])
        # self.all_candidates = all_candidates
        # return errors
        self.update_dynamic_plugins()
        self.inject_commands_from(self)

    def serve_forever(self):
        stream = zmqstream.ZMQStream(holder.broker_socket)

        stream.on_recv(self.callback_message)

        try:
            self.loop.start()
        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt, program will exit now.')
            self.shutdown()

    def send_message(self, mess):
        # super(TomBot, self).send_message(mess)
        # Act only in the backend tells us that this message is OK to broadcast
        for bot in get_all_active_plugin_objects():
            #noinspection PyBroadException
            try:
                bot.callback_message(mess)
            except Exception as _:
                logger.exception("Crash in a callback_message handler")

    def callback_message(self, message):
        logger.debug('Receive message from client: {}'.format(message[0]))
        logger.debug('Full message body: {}'.format(message))
        msg_obj = Message(message, holder.broker_socket)
        session_id = Session.generate_session_id(msg_obj.id, msg_obj.user)
        self.sessions[session_id] = self.sessions.get(session_id) or Session(msg_obj.id, msg_obj.user)
        current_session = self.sessions[session_id]
        logger.debug('Global Sessions: {}'.format(self.sessions))
        logger.debug('Current session: {}'.format(current_session._data))
        msg_obj.session = current_session

        if super(TomBot, self).callback_message(msg_obj):
            # Act only in the backend tells us that this message is OK to broadcast
            for plugin in get_all_active_plugin_objects():
                #noinspection PyBroadException
                try:
                    logger.debug('Callback %s' % plugin)
                    plugin.callback_message(msg_obj)
                except Exception as _:
                    logger.exception("Crash in a callback_message handler")

    def activate_non_started_plugins(self):
        logger.info('Activating all the user...')
        errors = ''
        for pluginInfo in get_all_plugins():
            try:
                if self.is_plugin_blacklisted(pluginInfo.name):
                    errors += ('Notice: %s is blacklisted, use ' + self.prefix + 'load %s to unblacklist it\n') % (
                        pluginInfo.name, pluginInfo.name)
                    continue
                if hasattr(pluginInfo, 'is_activated') and not pluginInfo.is_activated:
                    logger.info('Activate plugin: %s' % pluginInfo.name)
                    activate_plugin_by_name(pluginInfo.name)
            except Exception as e:
                logger.exception("Error loading %s" % pluginInfo.name)
                errors += 'Error: %s failed to start : %s\n' % (pluginInfo.name, e)
        if errors:
            self.warn_admins(errors)
            logger.exception(errors)
        return errors

    def activate_plugin(self, name):
        try:
            if name in get_all_active_plugin_names():
                return "Plugin already in active list"
            if name not in get_all_plugin_names():
                return "I don't know this %s plugin" % name
            activate_plugin_by_name(name)
        except Exception as e:
            logger.exception("Error loading %s" % name)
            return '%s failed to start : %s\n' % (name, e)
        get_plugin_obj_by_name(name).callback_connect()
        return "Plugin %s activated" % name

    def deactivate_plugin(self, name):
        if name not in get_all_active_plugin_names():
            return "Plugin %s not in active list" % name
        deactivate_plugin_by_name(name)
        return "Plugin %s deactivated" % name

    # plugin blacklisting management
    def get_blacklisted_plugin(self):
        return self.get(BL_PLUGINS, [])

    def is_plugin_blacklisted(self, name):
        return name in self.get_blacklisted_plugin()

    def blacklist_plugin(self, name):
        if self.is_plugin_blacklisted(name):
            logger.warning('Plugin %s is already blacklisted' % name)
            return 'Plugin %s is already blacklisted' % name
        self[BL_PLUGINS] = self.get_blacklisted_plugin() + [name]
        logger.info('Plugin %s is now blacklisted' % name)
        return 'Plugin %s is now blacklisted' % name

    def unblacklist_plugin(self, name):
        if not self.is_plugin_blacklisted(name):
            logger.warning('Plugin %s is not blacklisted' % name)
            return 'Plugin %s is not blacklisted' % name
        l = self.get_blacklisted_plugin()
        l.remove(name)
        self[BL_PLUGINS] = l
        logger.info('Plugin %s removed from blacklist' % name)
        return 'Plugin %s removed from blacklist' % name

    def update_dynamic_plugins(self):
        all_candidates, errors = update_plugin_places(config.plugin_dirs)
        self.all_candidates = all_candidates
        return errors

    def signal_connect_to_all_plugins(self):
        for plugin in get_all_active_plugin_objects():
            if hasattr(plugin, 'callback_connect'):
                #noinspection PyBroadException
                try:
                    logger.debug('Callback %s' % plugin)
                    plugin.callback_connect()
                except Exception as _:
                    logger.exception("callback_connect failed for %s" % plugin)

    def connect_callback(self):
        logger.info('Activate internal commands')
        loading_errors = self.activate_non_started_plugins()
        logger.info(loading_errors)
        logger.info('Notifying connection to all the user...')
        self.signal_connect_to_all_plugins()
        logger.info('Plugin activation done.')
        self.inject_commands_from(self)

    def disconnect_callback(self):
        self.remove_commands_from(self)
        logger.info('Disconnect callback, deactivating all the user.')
        deactivate_all_plugins()

    def shutdown(self):
        logger.info('Shutting down...')
        deactivate_all_plugins()
        self.close_storage()
        store.shelf.close()
        self.loop.stop()
        logger.info('Shutdown complete. Bye')

    @staticmethod
    def formatted_plugin_list(active_only=True):
        """
        Return a formatted, plain-text list of loaded user.

        When active_only=True, this will only return user which
        are actually active. Otherwise, it will also include inactive
        (blacklisted) user.
        """
        if active_only:
            all_plugins = get_all_active_plugin_names()
        else:
            all_plugins = get_all_plugin_names()
        return "\n".join(("• " + plugin for plugin in all_plugins))

    #noinspection PyUnusedLocal
    @botcmd
    def status(self, mess, args):
        """ If I am alive I should be able to respond to this one
        """
        all_blacklisted = self.get_blacklisted_plugin()
        all_loaded = get_all_active_plugin_names()
        all_attempted = sorted([p.name for p in self.all_candidates])
        plugins_statuses = []
        for name in all_attempted:
            if name in all_blacklisted:
                if name in all_loaded:
                    plugins_statuses.append(('BL', get_plugin_by_name(name).category, name))
                else:
                    plugins_statuses.append(('BU', name))
            elif name in all_loaded:
                plugins_statuses.append(('L', get_plugin_by_name(name).category, name))
            elif get_plugin_obj_by_name(name) is not None:
                plugins_statuses.append(('C', get_plugin_by_name(name).category, name))
            else:
                plugins_statuses.append(('U', name))

        #noinspection PyBroadException
        try:
            from posix import getloadavg

            loads = getloadavg()
        except Exception as _:
            loads = None

        # plugins_statuses = sorted(plugins_statuses, key=lambda c: c[2])
        return {'plugins': plugins_statuses, 'loads': loads, 'gc': gc.get_count()}

    #noinspection PyUnusedLocal
    @botcmd
    def echo(self, mess, args):
        """ A simple echo command. Useful for encoding tests etc ...
        """
        if 'DBG' in args or 'dbg' in args:
            return 'Do you mean the super-hero DBG?'
        return args.encode('utf-8')

    #noinspection PyUnusedLocal
    @botcmd
    def uptime(self, mess, args):
        """ Return the uptime of the bot
        """
        return "Tom have been up for %s %s (since %s)" % (args, format_timedelta(datetime.now() - self.startup_time),
                                                          datetime.strftime(self.startup_time, '%A, %b %d at %H:%M'))

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def restart(self, mess, args):
        """ restart the bot """
        mess.send("Deactivating all the plugins...")
        deactivate_all_plugins()
        mess.send("Restarting")
        self.shutdown()
        global_restart()
        return "I'm restarting..."

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def blacklist(self, mess, args):
        """Blacklist a plugin so that it will not be loaded automatically during bot startup"""
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        return self.blacklist_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def unblacklist(self, mess, args):
        """Remove a plugin from the blacklist"""
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugins are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        return self.unblacklist_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def load(self, mess, args):
        """load a plugin"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugin to reload:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugin are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args in get_all_active_plugin_names():
            return "{} is already loaded".format(args)

        reload_plugin_by_name(args)
        r = self.activate_plugin(args)
        return r

    @botcmd
    def more(self, mess, args):
        """
        command to implement paging
        :param mess:
        :param args:
        """
        pass

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def unload(self, mess, args):
        """unload a plugin"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugin to reload:\n"
                    "{}".format(self.formatted_plugin_list(active_only=False)))
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin name. The current plugin are:\n"
                    "{}".format(args, self.formatted_plugin_list(active_only=False)))
        if args not in get_all_active_plugin_names():
            return "{} is not currently loaded".format(args)

        return self.deactivate_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def reload(self, mess, args):
        """reload a plugin"""
        args = args.strip()
        if not args:
            yield ("Please tell me which of the following plugin to reload:\n"
                   "{}".format(self.formatted_plugin_list(active_only=False)))
            return
        if args not in get_all_plugin_names():
            yield ("{} isn't a valid plugin name. The current plugin are:\n"
                   "{}".format(args, self.formatted_plugin_list(active_only=False)))
            return

        yield self.deactivate_plugin(args)  # Not needed but keeps the feedback to user consistent
        reload_plugin_by_name(args)
        yield self.activate_plugin(args)

    #noinspection PyUnusedLocal
    def get_doc(self, command):
        """Get command documentation
        """
        if not command.__doc__:
            return '(undocumented)'
        if self.prefix == '!':
            return command.__doc__
        return command.__doc__.replace('!', self.prefix)

    def get_command_classes(self):
        return (get_class_that_defined_method(command) for command in self.commands.values())

    @botcmd
    def help(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        usage = ''
        if not args:
            description = 'Available help topics:\n'
            command_classes = sorted(set(self.get_command_classes()), key=lambda c: c.__name__)
            usage = '\n'.join(
                '%s: %s' % (clazz.__name__, clazz.__tomdoc__ or '(undocumented)') for clazz in
                command_classes)
        elif args == 'all':
            description = 'Available commands:'

            clazz_commands = {}
            for (name, command) in self.commands.items():
                clazz = get_class_that_defined_method(command)
                commands = clazz_commands.get(clazz, [])
                # if not config.hide_restrict_command or self.check_command_access(mess, name)[0]:
                if not config.hide_restrict_command:
                    commands.append((name, command))
                    clazz_commands[clazz] = commands

            for clazz in sorted(set(clazz_commands), key=lambda c: c.__name__):
                usage += '\n\n%s: %s\n' % (clazz.__name__, clazz.__tomdoc__ or '')
                usage += '\n'.join(sorted([
                    '\t' + self.prefix + ' %s: %s' % (name.replace('_', ' ', 1),
                                                      (self.get_doc(command).strip()).split('\n', 1)[0])
                    for (name, command) in clazz_commands[clazz]
                    if name != 'help' and not command._tom_command_hidden
                    # and (not config.hide_restrict_command or self.check_command_access(mess, name)[0])
                    and (not config.hide_restrict_command)
                ]))
            usage += '\n\n'
        elif args in (clazz.__name__ for clazz in self.get_command_classes()):
            # filter out the commands related to this class
            commands = [(name, command) for (name, command) in self.commands.items() if
                        get_class_that_defined_method(command).__name__ == args]
            description = 'Plugin %s contains commands:\n\n' % args
            usage += '\n'.join(sorted([
                '\t' + self.prefix + ' %s: %s' % (name.replace('_', ' ', 1),
                                                  (self.get_doc(command).strip()).split('\n', 1)[0])
                for (name, command) in commands
                if not command._tom_command_hidden and (not config.hide_restrict_command)
                # and (not config.hide_restrict_command or self.check_command_access(mess, name)[0])
            ]))
        else:
            return super(TomBot, self).help(mess, '_'.join(args.strip().split(' ')))

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    #noinspection PyUnusedLocal
    @botcmd(historize=False)
    def history(self, mess, args):
        """display the command history"""
        answer = []
        user_cmd_history = self.cmd_history[self.get_sender_username(mess)]
        l = len(user_cmd_history)
        for i in range(0, l):
            c = user_cmd_history[i]
            answer.append('%2i:%s%s %s' % (l - i, self.prefix, c[0], c[1]))
        return '\n'.join(answer)

    #noinspection PyUnusedLocal
    @botcmd
    def about(self, mess, args):
        """   Returns some information about this Tom instance"""

        result = 'Tom version %s \n\n' % config.version
        result += 'Authors: Konglx <konglx@ffcs.cn>'
        return result

    #noinspection PyUnusedLocal
    @botcmd
    def apropos(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            return 'Usage: ' + self.prefix + 'apropos search_term'

        description = 'Available commands:\n'

        clazz_commands = {}
        for (name, command) in self.commands.items():
            clazz = get_class_that_defined_method(command)
            clazz = str.__module__ + '.' + clazz.__name__  # makes the fuul qualified name
            commands = clazz_commands.get(clazz, [])
            # if not config.hide_restrict_command or self.check_command_access(mess, name)[0]:
            if not config.hide_restrict_command:
                commands.append((name, command))
                clazz_commands[clazz] = commands

        usage = ''
        for clazz in sorted(clazz_commands):
            usage += '\n'.join(sorted([
                '\t' + self.prefix + '%s: %s' % (
                    name.replace('_', ' ', 1), (command.__doc__ or '(undocumented)').strip().split('\n', 1)[0])
                for (name, command) in clazz_commands[clazz] if
                args is not None and command.__doc__ is not None and args.lower() in command.__doc__.lower() and name != 'help' and not command._tom_command_hidden
            ]))
        usage += '\n\n'

        top = self.top_of_help_message()
        bottom = self.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom])).strip()

    #noinspection PyUnusedLocal
    @botcmd
    def log_tail(self, mess, args):
        """ Display a tail of the log of n lines or 40 by default
        use : !log tail 10
        """
        #admin_only(mess) # uncomment if paranoid.
        n = 40
        if args.isdigit():
            n = int(args)
            if n > 50:
                return 'Only SB can do this...'
        with open(config.home + os.sep + 'log' + os.sep + 'tom.log', 'r') as f:
            return tail(f, n)
