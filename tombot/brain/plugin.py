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
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : plugin.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-29
#  Description : manage plugins
# TODO make ansible and builtins and user plugin separately

import sys
import os
from itertools import chain
from yapsy.PluginManager import PluginManager

from tombot.brain import holder
from tombot.common import log, config
from tombot.brain.engine import Engine, AnsibleEngine, BuiltinEngine
from tombot.brain.templating import add_plugin_templates_path, remove_plugin_templates_path


logger = log.logger

BUILTIN = config.home + os.sep + 'plugins'


def get_builtins(extra):
    # adds the extra plugin dir from the setup for developers convenience
    if extra:
        if isinstance(extra, list):
            return [BUILTIN] + extra
        return [BUILTIN, extra]
    else:
        return [BUILTIN]


def init_plugin_manager():
    global tom_plugin_manager
    from engine import BuiltinEngine, AnsibleEngine, Engine

    if not holder.plugin_manager:
        tom_plugin_manager = PluginManager()
        tom_plugin_manager.setPluginPlaces(config.plugin_dirs)
        tom_plugin_manager.setPluginInfoExtension('plug')
        # 3 types of plugins, Built-in for plugin come with Tom,
        # Ansible for ansible simplerunner or playbook running on tom
        # User for user-defined plugin
        tom_plugin_manager.setCategoriesFilter({
            'Built-in': BuiltinEngine,
            'Ansible': AnsibleEngine,
            'User': Engine
        })
        holder.plugin_manager = tom_plugin_manager
    else:
        tom_plugin_manager = holder.plugin_manager


init_plugin_manager()


def get_plugin_by_name(name):
    user_item = tom_plugin_manager.getPluginByName(name, 'User')
    builtin_item = tom_plugin_manager.getPluginByName(name, 'Built-in')
    ansible_item = tom_plugin_manager.getPluginByName(name, 'Ansible')

    pta_item = user_item or builtin_item or ansible_item
    if pta_item is None:
        return None
    return pta_item


def get_plugin_obj_by_name(name):
    plugin = get_plugin_by_name(name)
    return None if plugin is None else plugin.plugin_object


def populate_doc(plugin):
    """

    :param plugin: plugin to add doc
    """
    # TODO make docstring with method scope
    plugin_type = type(plugin.plugin_object)
    # plugin_type.__tomdoc__ = plugin_type.__doc__ if plugin_type.__doc__ else plugin.description
    plugin_type.__tomdoc__ = plugin.description if plugin.description else plugin_type.__doc__


def activate_plugin_by_name(name):
    pta_item = get_plugin_by_name(name)
    if pta_item is None:
        logger.warning('Could not activate %s' % name)
        return None
    # obj = pta_item.plugin_object

    populate_doc(pta_item)
    add_plugin_templates_path(pta_item.path)
    try:
        return tom_plugin_manager.activatePluginByName(name, pta_item.category)
    except Exception as _:
        pta_item.activated = False  # Yapsy doesn't revert this in case of error
        remove_plugin_templates_path(pta_item.path)
        logger.error("Plugin %s failed at activation stage, deactivating it..." % name)
        tom_plugin_manager.deactivatePluginByName(name, pta_item.category)
        raise


def deactivate_plugin_by_name(name):
    pta_item = get_plugin_by_name(name)
    # obj = pta_item.plugin_object
    remove_plugin_templates_path(pta_item.path)
    try:
        return tom_plugin_manager.deactivatePluginByName(name, pta_item.category)
    except Exception as _:
        add_plugin_templates_path(pta_item.path)
        raise


def reload_plugin_by_name(name):
    """
    Completely reload the given plugin, including reloading of the module's code
    """
    if name in get_all_active_plugin_names():
        deactivate_plugin_by_name(name)

    plugin = get_plugin_by_name(name)
    logger.critical(dir(plugin))
    module = __import__(plugin.path.split(os.sep)[-1])
    reload(module)

    class_name = type(plugin.plugin_object).__name__
    new_class = getattr(module, class_name)
    plugin.plugin_object.__class__ = new_class


def update_plugin_places(list):
    builtins = get_builtins(config.plugin_dirs)
    for entry in chain(builtins, list):
        if entry not in sys.path:
            sys.path.append(entry)  # so the user can relatively import their submodules
        for subdir in os.walk(entry).next()[1]:
            sys.path.append(entry + os.sep + subdir)

    tom_plugin_manager.setPluginPlaces(chain(builtins, list))
    all_candidates = []

    def add_candidate(candidate):
        all_candidates.append(candidate)

    tom_plugin_manager.locatePlugins()
    #noinspection PyBroadException
    try:
        tom_plugin_manager.loadPlugins(add_candidate)
    except Exception as _:
        logger.exception("Error while loading plugin")

    # FIXME temporary keep it from errbot
    errors = None

    return all_candidates, errors


def get_all_plugins():
    logger.debug("All plugins: %s" % tom_plugin_manager.getAllPlugins())
    return tom_plugin_manager.getAllPlugins()


def get_all_active_plugin_objects():
    return [plug.plugin_object for plug in get_all_plugins() if hasattr(plug, 'is_activated') and plug.is_activated]


def get_all_active_plugin_names():
    return [p.name for p in get_all_plugins() if hasattr(p, 'is_activated') and p.is_activated]


def get_all_plugin_names():
    return [p.name for p in get_all_plugins()]


def deactivate_all_plugins():
    for name in get_all_active_plugin_names():
        deactivate_plugin_by_name(name)


def global_restart():
    python = sys.executable
    os.execl(python, python, *sys.argv)
