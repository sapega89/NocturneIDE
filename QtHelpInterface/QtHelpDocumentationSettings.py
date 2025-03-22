# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to store the QtHelp documentation settings before
being applied to the help engine.
"""

import collections
import contextlib
import copy

from PyQt6.QtHelp import QCompressedHelpInfo


class QtHelpDocumentationSettings:
    """
    Class implementing a temporary store for QtHelp documentation settings.
    """

    def __init__(self):
        """
        Constructor
        """
        self._namespaceToComponent = {}
        self._componentToNamespace = collections.defaultdict(list)

        self._namespaceToVersion = {}
        self._versionToNamespace = collections.defaultdict(list)

        self._namespaceToFilename = {}
        self._filenameToNamespace = {}

    def addDocumentation(self, filename):
        """
        Public method to a add a documentation file to the list.

        @param filename name of the documentation file to add
        @type str
        @return flag indicating success
        @rtype bool
        """
        info = QCompressedHelpInfo.fromCompressedHelpFile(filename)

        if info.isNull():
            return False

        namespace = info.namespaceName()

        if namespace in self._namespaceToFilename:
            return False

        if filename in self._filenameToNamespace:
            return False

        component = info.component()
        version = info.version()

        self._namespaceToFilename[namespace] = filename
        self._filenameToNamespace[filename] = namespace

        self._namespaceToComponent[namespace] = component
        self._componentToNamespace[component].append(namespace)

        self._namespaceToVersion[namespace] = version
        self._versionToNamespace[version].append(namespace)

        return True

    def removeDocumentation(self, namespace):
        """
        Public method to remove the documentation of a given namespace.

        @param namespace name of the namespace
        @type str
        @return flag indicating success
        @rtype bool
        """
        if not namespace:
            return False

        try:
            filename = self._namespaceToFilename[namespace]
        except KeyError:
            return False

        component = self._namespaceToComponent[namespace]
        version = self._namespaceToVersion[namespace]

        del self._namespaceToComponent[namespace]
        del self._namespaceToVersion[namespace]
        del self._namespaceToFilename[namespace]
        with contextlib.suppress(KeyError):
            del self._filenameToNamespace[filename]
        self._componentToNamespace[component].remove(namespace)
        if len(self._componentToNamespace[component]) == 0:
            del self._componentToNamespace[component]
        self._versionToNamespace[version].remove(namespace)
        if len(self._versionToNamespace[version]) == 0:
            del self._versionToNamespace[version]

        return True

    def namespace(self, filename):
        """
        Public method to get the namespace defined by a QtHelp file.

        @param filename name of the QtHelp file
        @type str
        @return name of the namespace
        @rtype str
        """
        return self._filenameToNamespace[filename]

    def components(self):
        """
        Public method to get the list of components.

        @return list of components
        @rtype list of str
        """
        return list(self._componentToNamespace)

    def versions(self):
        """
        Public method to get the list of versions.

        @return list of versions
        @rtype list of QVersionNumber
        """
        return list(self._versionToNamespace)

    def namespaces(self):
        """
        Public method to get the list of namespaces.

        @return list of namespaces
        @rtype list of str
        """
        return list(self._namespaceToFilename)

    def namespaceToFilename(self):
        """
        Public method to get the namespace to filename mapping.

        @return dictionary containing the namespace to filename mapping
        @rtype dict
        """
        return copy.deepcopy(self._namespaceToFilename)

    @staticmethod
    def readSettings(helpEngine):
        """
        Static method to read the QtHelp documentation configuration.

        @param helpEngine reference to the QtHelp engine
        @type QHelpEngineCore
        @return reference to the created QtHelpDocumentationSettings object
        @rtype QtHelpDocumentationSettings
        """
        filterEngine = helpEngine.filterEngine()

        docSettings = QtHelpDocumentationSettings()
        docSettings._namespaceToComponent = filterEngine.namespaceToComponent()
        docSettings._namespaceToVersion = filterEngine.namespaceToVersion()

        for namespace, component in docSettings._namespaceToComponent.items():
            filename = helpEngine.documentationFileName(namespace)
            docSettings._namespaceToFilename[namespace] = filename
            docSettings._filenameToNamespace[filename] = namespace
            docSettings._componentToNamespace[component].append(namespace)

        for namespace, version in docSettings._namespaceToVersion.items():
            docSettings._versionToNamespace[version].append(namespace)

        return docSettings

    @staticmethod
    def applySettings(helpEngine, settings):
        """
        Static method to apply the changed QtHelp documentation configuration.

        @param helpEngine reference to the QtHelp engine
        @type QHelpEngineCore
        @param settings reference to the created QtHelpDocumentationSettings
            object
        @type QtHelpDocumentationSettings
        @return flag indicating success
        @rtype bool
        """
        currentSettings = QtHelpDocumentationSettings.readSettings(helpEngine)

        docsToRemove = [
            name
            for name in currentSettings._namespaceToFilename
            if name not in settings._namespaceToFilename
        ]
        docsToAdd = [
            filename
            for filename in settings._filenameToNamespace
            if filename not in currentSettings._filenameToNamespace
        ]

        changed = False
        for namespace in docsToRemove:
            helpEngine.unregisterDocumentation(namespace)
            changed = True

        for filename in docsToAdd:
            helpEngine.registerDocumentation(filename)
            changed = True

        return changed
