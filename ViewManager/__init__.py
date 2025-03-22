# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the viewmanager of the eric IDE.

The viewmanager is responsible for the layout of the editor windows. This is
the central part of the IDE. In additon to this, the viewmanager provides all
editor related actions, menus and toolbars.

View managers are provided as plugins and loaded via the factory function. If
the requested view manager type is not available, tabview will be used by
default.
"""

from eric7 import Preferences

######################################################################
## Below is the factory function to instantiate the appropriate
## viewmanager depending on the configuration settings
######################################################################


def factory(ui, dbs, remoteServerInterface, pluginManager):
    """
    Modul factory function to generate the right viewmanager type.

    The viewmanager is instantiated depending on the data set in
    the current preferences.

    @param ui reference to the main UI object
    @type UserInterface
    @param dbs reference to the debug server object
    @type DebugServer
    @param remoteServerInterface reference to the 'eric-ide' server interface
    @type EricServerInterface
    @param pluginManager reference to the plugin manager object
    @type PluginManager
    @return the instantiated viewmanager
    @rtype ViewManager
    @exception RuntimeError raised if no view manager could be created
    """
    viewManagerStr = Preferences.getViewManager()
    vm = pluginManager.getPluginObject("viewmanager", viewManagerStr)[0]
    if vm is None:
        # load tabview view manager as default
        vm, err = pluginManager.getPluginObject("viewmanager", "tabview")
        if vm is None:
            raise RuntimeError(f"Could not create a viemanager object.\nError: {err}")
        Preferences.setViewManager("tabview")
    vm.setReferences(ui, dbs, remoteServerInterface)
    return vm
