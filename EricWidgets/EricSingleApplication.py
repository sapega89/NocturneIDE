# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the single application server and client.
"""

import os

from eric7.EricWidgets.EricApplication import ericApp
from eric7.Toolbox.SingleApplication import (
    SingleApplicationClient,
    SingleApplicationServer,
)

###########################################################################
## define some module global stuff
###########################################################################

SAFile = "eric7"

# define the protocol tokens
SAOpenFile = "OpenFile"
SAOpenProject = "OpenProject"
SAOpenMultiProject = "OpenMultiProject"
SAArguments = "Arguments"


class EricSingleApplicationServer(SingleApplicationServer):
    """
    Class implementing the single application server embedded within the IDE.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__(SAFile)

    def handleCommand(self, command, arguments):
        """
        Public slot to handle the command sent by the client.

        @param command command sent by the client
        @type str
        @param arguments list of command arguments
        @type list of str
        """
        if command == SAOpenFile:
            self.__saOpenFile(arguments[0])
            return

        if command == SAOpenProject:
            self.__saOpenProject(arguments[0])
            return

        if command == SAOpenMultiProject:
            self.__saOpenMultiProject(arguments[0])
            return

        if command == SAArguments:
            self.__saArguments(arguments[0])
            return

    def __saOpenFile(self, fname):
        """
        Private method used to handle the "Open File" command.

        @param fname filename to be opened
        @type str
        """
        ericApp().getObject("ViewManager").openSourceFile(fname)

    def __saOpenProject(self, pfname):
        """
        Private method used to handle the "Open Project" command.

        @param pfname filename of the project to be opened
        @type str
        """
        ericApp().getObject("Project").openProject(pfname)

    def __saOpenMultiProject(self, pfname):
        """
        Private method used to handle the "Open Multi-Project" command.

        @param pfname filename of the multi project to be opened
        @type str
        """
        ericApp().getObject("MultiProject").openMultiProject(pfname)

    def __saArguments(self, argsStr):
        """
        Private method used to handle the "Arguments" command.

        @param argsStr space delimited list of command args
        @type str
        """
        ericApp().getObject("DebugUI").setArgvHistory(argsStr)


class EricSingleApplicationClient(SingleApplicationClient):
    """
    Class implementing the single application client of the IDE.
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
        for filename in args.file_or_project:
            ext = os.path.splitext(filename)[1].lower()

            if ext in (".epj",):
                self.__openProject(filename)
            elif ext in (".emj",):
                self.__openMultiProject(filename)
            else:
                self.__openFile(filename)

        if args.dd_args:
            # send any args we had
            argsStr = " ".join(args.dd_args)
            self.__sendArguments(argsStr)

        self.disconnect()

    def __openFile(self, fname):
        """
        Private method to open a file in the application server.

        @param fname name of file to be opened
        @type str
        """
        self.sendCommand(SAOpenFile, [os.path.abspath(fname)])

    def __openProject(self, pfname):
        """
        Private method to open a project in the application server.

        @param pfname name of the projectfile to be opened
        @type str
        """
        self.sendCommand(SAOpenProject, [os.path.abspath(pfname)])

    def __openMultiProject(self, pfname):
        """
        Private method to open a project in the application server.

        @param pfname name of the projectfile to be opened
        @type str
        """
        self.sendCommand(SAOpenMultiProject, [os.path.abspath(pfname)])

    def __sendArguments(self, argsStr):
        """
        Private method to set the command arguments in the application server.

        @param argsStr space delimited list of command args
        @type str
        """
        self.sendCommand(SAArguments, [argsStr])
