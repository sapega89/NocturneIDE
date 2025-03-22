# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the general part of the interface to version control
systems.

The general part of the VCS interface defines classes to implement common
dialogs. These are a dialog to enter command options, a dialog to display
some repository information and an abstract base class. The individual
interfaces have to be subclasses of this base class.
"""

from eric7.EricWidgets.EricApplication import ericApp

######################################################################
## Below is the factory function to instantiate the appropriate
## vcs object depending on the project settings.
######################################################################


def factory(vcs):
    """
    Modul factory function to generate the right vcs object.

    @param vcs name of the VCS system to be used
    @type str
    @return the instantiated VCS object
    @rtype VersionControl
    """
    pluginManager = ericApp().getObject("PluginManager")
    if pluginManager is None:
        # that should not happen
        vc = None

    vc = pluginManager.getPluginObject("version_control", vcs, maybeActive=True)[0]
    if vc is None:
        # try alternative vcs interfaces assuming, that there is a common
        # indicator for the alternatives
        for vcsData in pluginManager.getVcsSystemIndicators().values():
            for vcsSystem, _vcsSystemDisplay in vcsData:
                if vcsSystem == vcs and len(vcsData) > 1:
                    for vcsSystem, _vcsSystemDisplay in vcsData:
                        if vcsSystem != vcs:
                            vc = pluginManager.getPluginObject(
                                "version_control", vcsSystem, maybeActive=True
                            )[0]
                            if vc is not None:
                                return vc

    return vc


VcsBasicHelperSingleton = None


def getBasicHelper(project):
    """
    Module function to get a reference to the basic project helper singleton.

    @param project reference to the project object
    @type Project
    @return reference to the basic VCS project helper singleton
    @rtype VcsProjectHelper
    """
    from .ProjectHelper import VcsProjectHelper

    global VcsBasicHelperSingleton

    if VcsBasicHelperSingleton is None:
        VcsBasicHelperSingleton = VcsProjectHelper(None, project)

    return VcsBasicHelperSingleton
