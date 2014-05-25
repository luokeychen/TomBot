#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:
from datetime import datetime
import gc
import os
import inspect
from pprint import pformat

from tombot import botcmd
from tombot.brain.plugin import get_all_active_plugin_names, get_plugin_by_name, get_plugin_obj_by_name
from tombot.brain.plugin import deactivate_all_plugins, global_restart, get_all_plugin_names, reload_plugin_by_name
from tombot.brain import holder
from tombot.common import config
from tombot.common.utils import tail, format_timedelta
from tombot import BuiltinEngine


__author__ = 'Konglx'


def get_class_that_defined_method(meth):
    for cls in inspect.getmro(type(meth.__self__)):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


class BotAdmin(BuiltinEngine):
    """Commands relate to TomBot administration"""

    @botcmd
    def auth(self, message, args):
        """ To perform a admin authentication, and keep it until restart. """
        password = message.get_input('Please give me your pass code.')
        if password.strip() == config.admin_pass:
            holder.bot.admins.append(message.user)
            message.info('Authentication success!')
        else:
            message.warn('Authentication failed!!!')

    #noinspection PyUnusedLocal
    @botcmd
    def status(self, mess, args):
        """ If I am alive I should be able to respond to this one
        """
        all_blacklisted = holder.bot.get_blacklisted_plugin()
        all_loaded = get_all_active_plugin_names()
        all_attempted = sorted([p.name for p in holder.bot.all_candidates])
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
        return pformat({'plugins': plugins_statuses, 'loads': loads, 'gc': gc.get_count()})

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
        return "Tom have been up for %s %s (since %s)" \
               % (args, format_timedelta(datetime.now() - holder.bot.startup_time),
                  datetime.strftime(holder.bot.startup_time, '%A, %b %d at %H:%M'))

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def restart(self, mess, args):
        """ Restart the bot """
        mess.send("Deactivating all the plugins...")
        deactivate_all_plugins()
        mess.send("Restarting")
        holder.bot.shutdown()
        global_restart()
        return "I'm restarting..."

    @botcmd
    def list_plugin(self, message, args):
        """ List all plugins """
        return holder.bot.formatted_plugin_list(active_only=False)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def blacklist(self, mess, args):
        """Blacklist a plugin so that it will not be loaded automatically during bot startup"""
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin names. The current plugins are:\n"
                    "{}".format(args, holder.bot.formatted_plugin_list(active_only=False)))
        return holder.bot.blacklist_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def unblacklist(self, mess, args):
        """Remove a plugin from the blacklist"""
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin names. The current plugins are:\n"
                    "{}".format(args, holder.bot.formatted_plugin_list(active_only=False)))
        return holder.bot.unblacklist_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def load(self, mess, args):
        """load a plugin"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugin to reload:\n"
                    "{}".format(holder.bot.formatted_plugin_list(active_only=False)))
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin names. The current plugin are:\n"
                    "{}".format(args, holder.bot.formatted_plugin_list(active_only=False)))
        if args in get_all_active_plugin_names():
            return "{} is already loaded".format(args)

        reload_plugin_by_name(args)
        r = holder.bot.activate_plugin(args)
        return r

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def unload(self, mess, args):
        """unload a plugin"""
        args = args.strip()
        if not args:
            return ("Please tell me which of the following plugin to reload:\n"
                    "{}".format(holder.bot.formatted_plugin_list(active_only=False)))
        if args not in get_all_plugin_names():
            return ("{} isn't a valid plugin names. The current plugin are:\n"
                    "{}".format(args, holder.bot.formatted_plugin_list(active_only=False)))
        if args not in get_all_active_plugin_names():
            return "{} is not currently loaded".format(args)

        return holder.bot.deactivate_plugin(args)

    #noinspection PyUnusedLocal
    @botcmd(admin_only=True)
    def reload(self, mess, args):
        """reload a plugin"""
        args = args.strip()
        if not args:
            yield ("Please tell me which of the following plugin to reload:\n"
                   "{}".format(holder.bot.formatted_plugin_list(active_only=False)))
            return
        if args not in get_all_plugin_names():
            yield ("{} isn't a valid plugin names. The current plugin are:\n"
                   "{}".format(args, holder.bot.formatted_plugin_list(active_only=False)))
            return

        yield holder.bot.deactivate_plugin(args)  # Not needed but keeps the feedback to user consistent
        reload_plugin_by_name(args)
        yield holder.bot.activate_plugin(args)

    #noinspection PyUnusedLocal
    def get_doc(self, command):
        """Get command documentation
        """
        if not command.__doc__:
            return '(undocumented)'
        if holder.bot.prefix == '!':
            return command.__doc__
        return command.__doc__.replace('!', holder.bot.prefix)

    def get_command_classes(self):
        return (get_class_that_defined_method(command) for command in holder.bot.commands.values())

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
            for (name, command) in holder.bot.commands.items():
                clazz = get_class_that_defined_method(command)
                commands = clazz_commands.get(clazz, [])
                # if not config.hide_restrict_command or self.check_command_access(mess, names)[0]:
                if not config.hide_restrict_command:
                    commands.append((name, command))
                    clazz_commands[clazz] = commands

            for clazz in sorted(set(clazz_commands), key=lambda c: c.__name__):
                usage += '\n\n%s: %s\n' % (clazz.__name__, clazz.__tomdoc__ or '')
                usage += '\n'.join(sorted([
                    '\t' + holder.bot.prefix + ' %s: %s' % (name.replace('_', ' ', 1),
                                                            (self.get_doc(command).strip()).split('\n', 1)[0])
                    for (name, command) in clazz_commands[clazz]
                    if name != 'help' and not command._tom_command_hidden
                    # and (not config.hide_restrict_command or self.check_command_access(mess, names)[0])
                    and (not config.hide_restrict_command)
                ]))
            usage += '\n\n'
        elif args in (clazz.__name__ for clazz in self.get_command_classes()):
            # filter out the commands related to this class
            commands = [(name, command) for (name, command) in holder.bot.commands.items() if
                        get_class_that_defined_method(command).__name__ == args]
            description = 'Plugin %s contains commands:\n\n' % args
            usage += '\n'.join(sorted([
                '\t' + holder.bot.prefix + ' %s: %s' % (name.replace('_', ' ', 1),
                                                        (self.get_doc(command).strip()).split('\n', 1)[0])
                for (name, command) in commands
                if not command._tom_command_hidden and (not config.hide_restrict_command)
                # and (not config.hide_restrict_command or self.check_command_access(mess, names)[0])
            ]))
        else:
            # return super(TomBot, self).help(mess, '_'.join(args.strip().split(' ')))
            return 'No help available'

        top = holder.bot.top_of_help_message()
        bottom = holder.bot.bottom_of_help_message()
        return ''.join(filter(None, [top, description, usage, bottom]))

    #noinspection PyUnusedLocal
    @botcmd(historize=False)
    def history(self, mess, args):
        """display the command history"""
        answer = []
        # user_cmd_history = self.cmd_history[self.get_sender_username(mess)]
        user_cmd_history = mess.session['history']
        l = len(user_cmd_history)
        for i in range(0, l):
            c = user_cmd_history[i]
            answer.append('%2i:%s %s %s' % (l - i, holder.bot.prefix, c[0], c[1]))
        if not answer:
            return 'Your command history is empty.'
        answer.append('\nType {}# like !2 to perform an execute from history.'.format(holder.bot.prefix))
        answer.append('And !! for last history item.')
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
    def usage(self, mess, args):
        """   Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            return 'Usage: ' + holder.bot.prefix + ' usage search_term'

        description = 'Available commands:\n'

        clazz_commands = {}
        for (name, command) in holder.bot.commands.items():
            clazz = get_class_that_defined_method(command)
            clazz = str.__module__ + '.' + clazz.__name__  # makes the fuul qualified names
            commands = clazz_commands.get(clazz, [])
            # if not config.hide_restrict_command or self.check_command_access(mess, names)[0]:
            if not config.hide_restrict_command:
                commands.append((name, command))
                clazz_commands[clazz] = commands

        usage = ''
        for clazz in sorted(clazz_commands):
            usage += '\n'.join(sorted([
                '\t' + holder.bot.prefix + ' %s: %s' % (
                    name.replace('_', ' ', 1), (command.__doc__ or '(undocumented)').strip().split('\n', 1)[0])
                for (name, command) in clazz_commands[clazz] if
                args is not None and command.__doc__ is not None and args.lower() in command.__doc__.lower() and name != 'help' and not command._tom_command_hidden
            ]))
        usage += '\n\n'

        top = holder.bot.top_of_help_message()
        bottom = holder.bot.bottom_of_help_message()
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
