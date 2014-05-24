# -*- coding:utf-8 -*-
import os
import gc
from datetime import datetime
import inspect
from pprint import pformat
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
        self.prefix = 'Tom'
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
        msg_obj = Message(message)
        session_id = Session.generate_session_id(msg_obj.id, msg_obj.user)
        self.sessions[session_id] = self.sessions.get(session_id) or Session(msg_obj.id, msg_obj.user)
        current_session = self.sessions[session_id]
        logger.debug('Global Sessions: {}'.format(self.sessions))
        logger.debug('Current session: {}'.format(current_session._data))
        msg_obj.session = current_session

        if msg_obj.session['is_wait']:
            # BUG actually, needs a lock here if user type fast enough
            msg_obj.session.queue.put(msg_obj.content)
            return

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
        logger.info('Activating all the plugins...')
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
        """Will put a flag to bot's shelf store"""
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
        logger.info('Notifying connection to all the plugins...')
        self.signal_connect_to_all_plugins()
        logger.info('Plugin activation done.')
        self.inject_commands_from(self)

    def disconnect_callback(self):
        self.remove_commands_from(self)
        logger.info('Disconnect callback, deactivating all the plugins.')
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
        Return a formatted, plain-text list of loaded plugins.

        When active_only=True, this will only return plugins which
        are actually active. Otherwise, it will also include inactive
        (blacklisted) plugins.
        """
        if active_only:
            all_plugins = get_all_active_plugin_names()
        else:
            all_plugins = get_all_plugin_names()
        return "\n".join(("- " + plugin for plugin in all_plugins))

