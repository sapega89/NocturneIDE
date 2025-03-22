# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the single application server and client for the web
browser.
"""

from PyQt6.QtCore import pyqtSignal

from eric7.Toolbox.SingleApplication import (
    SingleApplicationClient,
    SingleApplicationServer,
)

###########################################################################
## define some module global stuff
###########################################################################

SAFile = "eric7_browser"

# define the protocol tokens
SALoadUrl = "LoadUrl"
SANewTab = "NewTab"
SASearch = "Search"
SAShutdown = "Shutdown"


class WebBrowserSingleApplicationServer(SingleApplicationServer):
    """
    Class implementing the single application server embedded within the
    Web Browser.

    @signal loadUrl(str) emitted to load an URL
    @signal newTab(str) emitted to load an URL in a new tab
    @signal search(str) emitted to search for a given word
    @signal shutdown() emitted to shut down the browser
    """

    loadUrl = pyqtSignal(str)
    newTab = pyqtSignal(str)
    search = pyqtSignal(str)
    shutdown = pyqtSignal()

    def __init__(self, name=""):
        """
        Constructor

        @param name name to be used by the single application server
        @type str
        """
        if not name:
            name = SAFile

        SingleApplicationServer.__init__(self, name)

    def handleCommand(self, command, arguments):
        """
        Public slot to handle the command sent by the client.

        @param command command sent by the client
        @type str
        @param arguments list of command arguments
        @type list of str
        """
        if command == SALoadUrl:
            self.__saLoadUrl(arguments[0])

        elif command == SANewTab:
            self.__saNewTab(arguments[0])

        elif command == SASearch:
            self.__saSearch(arguments[0])

        elif command == SAShutdown:
            self.__saShutdown()

    def __saLoadUrl(self, url):
        """
        Private method to load an URL in a new tab.

        @param url URL to be loaded
        @type str
        """
        self.loadUrl.emit(url)

    def __saNewTab(self, url):
        """
        Private method to load an URL .

        @param url URL to be loaded
        @type str
        """
        self.newTab.emit(url)

    def __saSearch(self, word):
        """
        Private method to search for a given word.

        @param word word to be searched for
        @type str
        """
        self.search.emit(word)

    def __saShutdown(self):
        """
        Private method to shut down the web browser.
        """
        self.shutdown.emit()


class WebBrowserSingleApplicationClient(SingleApplicationClient):
    """
    Class implementing the single application client of the web browser.
    """

    def __init__(self, name=""):
        """
        Constructor

        @param name name to be used by the single application server
        @type str
        """
        if not name:
            name = SAFile

        super().__init__(name)

    def processArgs(self, args, disconnect=True):
        """
        Public method to process the command line args passed to the UI.

        @param args namespace object containing the parsed command line parameters
        @type argparse.Namespace
        @param disconnect flag indicating to disconnect when done
        @type bool
        """
        if args.shutdown:
            # send shutdown command and return
            self.__shutdown()
            return

        if args.search:
            self.__search(args.search)
        if args.new_tab:
            for url in args.new_tab:
                self.__newTab(url)
        if args.home:
            self.__loadUrl(args.home)

        if disconnect:
            self.disconnect()

    def __loadUrl(self, url):
        """
        Private method to send an URL to be loaded.

        @param url URL to be loaded
        @type str
        """
        self.sendCommand(SALoadUrl, [url])

    def __newTab(self, url):
        """
        Private method to send an URL to be loaded in a new tab.

        @param url URL to be loaded
        @type str
        """
        self.sendCommand(SANewTab, [url])

    def __search(self, word):
        """
        Private method to send a word to search for.

        @param word to to be searched for
        @type str
        """
        self.sendCommand(SASearch, [word])

    def __shutdown(self):
        """
        Private method to signal a shutdown request to the browser.
        """
        self.sendCommand(SAShutdown, [])
