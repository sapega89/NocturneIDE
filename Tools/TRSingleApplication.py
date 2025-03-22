# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the single application server and client.
"""

import os

from PyQt6.QtCore import pyqtSignal

from eric7.Toolbox.SingleApplication import (
    SingleApplicationClient,
    SingleApplicationServer,
)

###########################################################################
## define some module global stuff
###########################################################################

SAFile = "eric7_trpreviewer"

# define the protocol tokens
SALoadForm = "LoadForm"
SALoadTranslation = "LoadTranslation"


class TRSingleApplicationServer(SingleApplicationServer):
    """
    Class implementing the single application server embedded within the
    Translations Previewer.

    @signal loadForm(str) emitted to load a form file
    @signal loadTranslation(str, bool) emitted to load a translation file
    """

    loadForm = pyqtSignal(str)
    loadTranslation = pyqtSignal(str, bool)

    def __init__(self, parent):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        SingleApplicationServer.__init__(self, SAFile)

        self.parent = parent

    def handleCommand(self, command, arguments):
        """
        Public slot to handle the command sent by the client.

        @param command command sent by the client
        @type str
        @param arguments list of command arguments
        @type list of str
        """
        if command == SALoadForm:
            self.__saLoadForm(arguments)

        elif command == SALoadTranslation:
            self.__saLoadTranslation(arguments)

    def __saLoadForm(self, fnames):
        """
        Private method used to handle the "Load Form" command.

        @param fnames filenames of the forms to be loaded
        @type list of str
        """
        for fname in fnames:
            self.loadForm.emit(fname)

    def __saLoadTranslation(self, fnames):
        """
        Private method used to handle the "Load Translation" command.

        @param fnames filenames of the translations to be loaded
        @type list of str
        """
        first = True
        for fname in fnames:
            self.loadTranslation.emit(fname, first)
            first = False


class TRSingleApplicationClient(SingleApplicationClient):
    """
    Class implementing the single application client of the Translations
    Previewer.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__(SAFile)

    def processArgs(self, args):
        """
        Public method to process the command line args passed to the UI.

        @param args namespace object containing the parsed command line parameters
        @type argparse.Namespace
        """
        uiFiles = []
        qmFiles = []

        for filename in args.file:
            ext = os.path.splitext(filename)[1].lower()

            if ext == ".ui":
                uiFiles.append(filename)
            elif ext == ".qm":
                qmFiles.append(filename)
            elif ext == ".ts":
                qmFile = os.path.splitext(filename)[0] + ".qm"
                if os.path.exists(qmFile):
                    qmFiles.append(qmFile)

        self.sendCommand(SALoadForm, uiFiles)
        self.sendCommand(SALoadTranslation, qmFiles)

        self.disconnect()
