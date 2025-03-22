# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the APIsManager.
"""

import glob
import os
import pathlib

from PyQt6.Qsci import QsciAPIs
from PyQt6.QtCore import QLibraryInfo, QObject, pyqtSignal

from eric7 import EricUtilities, Preferences

from . import Lexers


class APIs(QObject):
    """
    Class implementing an API storage entity.

    @signal apiPreparationFinished() emitted after the API preparation has
        finished
    @signal apiPreparationCancelled() emitted after the API preparation has
        been cancelled
    @signal apiPreparationStarted() emitted after the API preparation has
        started
    """

    apiPreparationFinished = pyqtSignal()
    apiPreparationCancelled = pyqtSignal()
    apiPreparationStarted = pyqtSignal()

    def __init__(self, language, projectType="", forPreparation=False, parent=None):
        """
        Constructor

        @param language language of the APIs object
        @type str
        @param projectType type of the project
        @type str
        @param forPreparation flag indicating this object is just needed
            for a preparation process
        @type bool
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)
        if projectType:
            self.setObjectName("APIs_{0}_{1}".format(language, projectType))
        else:
            self.setObjectName("APIs_{0}".format(language))

        self.__inPreparation = False
        self.__language = language
        self.__projectType = projectType
        self.__forPreparation = forPreparation
        self.__lexer = Lexers.getLexer(self.__language)
        self.__apifiles = Preferences.getEditorAPI(self.__language, self.__projectType)
        self.__apifiles.sort()
        if self.__lexer is None:
            self.__apis = None
        else:
            self.__apis = QsciAPIs(self.__lexer)
            self.__apis.apiPreparationFinished.connect(self.__apiPreparationFinished)
            self.__apis.apiPreparationCancelled.connect(self.__apiPreparationCancelled)
            self.__apis.apiPreparationStarted.connect(self.__apiPreparationStarted)
            self.__loadAPIs()

    def __loadAPIs(self):
        """
        Private method to load the APIs.
        """
        if self.__apis.isPrepared():
            # load a prepared API file
            if not self.__forPreparation and Preferences.getEditor("AutoPrepareAPIs"):
                self.prepareAPIs()
            self.__apis.loadPrepared(self.__preparedName())
        else:
            # load the raw files and prepare the API file
            if not self.__forPreparation and Preferences.getEditor("AutoPrepareAPIs"):
                self.prepareAPIs(ondemand=True)

    def reloadAPIs(self):
        """
        Public method to reload the API information.
        """
        if not self.__forPreparation and Preferences.getEditor("AutoPrepareAPIs"):
            self.prepareAPIs()
        self.__loadAPIs()

    def getQsciAPIs(self):
        """
        Public method to get a reference to QsciAPIs object.

        @return reference to the QsciAPIs object
        @rtype QsciAPIs
        """
        if not self.__forPreparation and Preferences.getEditor("AutoPrepareAPIs"):
            self.prepareAPIs()
        return self.__apis

    def isEmpty(self):
        """
        Public method to check, if the object has API files configured.

        @return flag indicating no API files have been configured
        @rtype bool
        """
        return len(self.__apifiles) == 0

    def __apiPreparationFinished(self):
        """
        Private method called to save an API, after it has been prepared.
        """
        self.__apis.savePrepared(self.__preparedName())
        self.__inPreparation = False
        self.apiPreparationFinished.emit()

    def __apiPreparationCancelled(self):
        """
        Private method called, after the API preparation process has been
        cancelled.
        """
        self.__inPreparation = False
        self.apiPreparationCancelled.emit()

    def __apiPreparationStarted(self):
        """
        Private method called, when the API preparation process started.
        """
        self.__inPreparation = True
        self.apiPreparationStarted.emit()

    def prepareAPIs(self, ondemand=False, rawList=None):
        """
        Public method to prepare the APIs if necessary.

        @param ondemand flag indicating a requested preparation
        @type bool
        @param rawList list of raw API files
        @type list of str
        """
        if self.__apis is None or self.__inPreparation:
            return

        needsPreparation = False
        if ondemand:
            needsPreparation = True
        else:
            # check, if a new preparation is necessary
            preparedAPIs = self.__preparedName()
            if preparedAPIs:
                preparedPath = pathlib.Path(preparedAPIs)
                if not preparedPath.exists():
                    needsPreparation = True
                else:
                    preparedAPIsModified = preparedPath.stat().st_mtime
                    apifiles = sorted(
                        Preferences.getEditorAPI(self.__language, self.__projectType)
                    )
                    if self.__apifiles != apifiles:
                        needsPreparation = True
                    for apifile in apifiles:
                        apifilePath = pathlib.Path(apifile)
                        if (
                            apifilePath.exists()
                            and apifilePath.stat().st_mtime > preparedAPIsModified
                        ):
                            needsPreparation = True
                            break

        if needsPreparation:
            # do the preparation
            self.__apis.clear()
            if rawList:
                apifiles = rawList
            else:
                apifiles = Preferences.getEditorAPI(self.__language, self.__projectType)
            for apifile in apifiles:
                self.__apis.load(apifile)
            self.__apis.prepare()
            self.__apifiles = apifiles

    def cancelPreparation(self):
        """
        Public slot to cancel the APIs preparation.
        """
        self.__apis and self.__apis.cancelPreparation()

    def installedAPIFiles(self):
        """
        Public method to get a list of installed API files.

        @return list of installed API files
        @rtype list of str
        """
        if self.__apis is not None:
            qtDataDir = QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath)
            apisDir = os.path.join(qtDataDir, "qsci", "api")
            if os.path.exists(apisDir) and self.__lexer.language():
                apiDir = os.path.join(apisDir, self.__lexer.language())
                if not os.path.exists(apiDir):
                    # use lower case language
                    apiDir = os.path.join(apisDir, self.__lexer.language().lower())
                fnames = set(glob.glob(os.path.join(apiDir, "*.api")))
                # combine with the QScintilla standard behavior
                fnames |= set(
                    glob.glob(os.path.join(apisDir, self.__lexer.lexer(), "*.api"))
                )
                return sorted(fnames)

        return []

    def __preparedName(self):
        """
        Private method returning the default name of a prepared API file.

        @return complete filename for the Prepared APIs file
        @rtype str
        """
        apisDir = os.path.join(EricUtilities.getConfigDir(), "APIs")
        if self.__apis is not None:
            if self.__projectType:
                filename = "{0}_{1}.pap".format(self.__language, self.__projectType)
            else:
                filename = "{0}.pap".format(self.__language)
            return os.path.join(apisDir, filename)
        else:
            return ""


class APIsManager(QObject):
    """
    Class implementing the APIsManager class, which is the central store for
    API information used by autocompletion and calltips.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)
        self.setObjectName("APIsManager")

        self.__apis = {}

    def reloadAPIs(self):
        """
        Public slot to reload the api information.
        """
        for api in self.__apis.values():
            api and api.reloadAPIs()

    def getAPIs(self, language, projectType="", forPreparation=False):
        """
        Public method to get an APIs object for autocompletion/calltips.

        This method creates and loads an APIs object dynamically upon request.
        This saves memory for languages, that might not be needed at the
        moment.

        @param language language of the requested APIs object
        @type str
        @param projectType type of the project
        @type str
        @param forPreparation flag indicating the requested APIs object is just
            needed for a preparation process
        @type bool
        @return reference to the APIs object
        @rtype APIs
        """
        if forPreparation:
            return APIs(
                language, projectType=projectType, forPreparation=forPreparation
            )
        else:
            try:
                return self.__apis[(language, projectType)]
            except KeyError:
                if language in Lexers.getSupportedApiLanguages():
                    # create the api object
                    self.__apis[(language, projectType)] = APIs(
                        language, projectType=projectType
                    )
                    return self.__apis[(language, projectType)]
                else:
                    return None
