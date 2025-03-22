# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the SQL Browser main window.
"""

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QKeySequence
from PyQt6.QtSql import QSqlDatabase, QSqlError

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow

from .SqlBrowserWidget import SqlBrowserWidget


class SqlBrowser(EricMainWindow):
    """
    Class implementing the SQL Browser main window.
    """

    def __init__(self, connections=None, parent=None):
        """
        Constructor

        @param connections list of database connections to add
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setObjectName("SqlBrowser")

        if connections is None:
            connections = []

        self.setWindowTitle(self.tr("SQL Browser"))
        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.__browser = SqlBrowserWidget(self)
        self.setCentralWidget(self.__browser)

        self.__browser.statusMessage.connect(self.statusBar().showMessage)

        self.__initActions()
        self.__initMenus()
        self.__initToolbars()

        self.resize(self.__browser.size())

        self.__warnings = []

        for connection in connections:
            url = QUrl(connection, QUrl.ParsingMode.TolerantMode)
            if not url.isValid():
                self.__warnings.append(self.tr("Invalid URL: {0}").format(connection))
                continue

            err = self.__browser.addConnection(
                url.scheme(),
                url.path(),
                url.userName(),
                url.password(),
                url.host(),
                url.port(-1),
            )
            if err.type() != QSqlError.ErrorType.NoError:
                self.__warnings.append(
                    self.tr("Unable to open connection: {0}".format(err.text()))
                )

        QTimer.singleShot(0, self.__uiStartUp)

    def __uiStartUp(self):
        """
        Private slot to do some actions after the UI has started and the main
        loop is up.
        """
        for warning in self.__warnings:
            EricMessageBox.warning(
                self, self.tr("SQL Browser startup problem"), warning
            )

        if len(QSqlDatabase.connectionNames()) == 0:
            self.__browser.addConnectionByDialog()

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        # list of all actions
        self.__actions = []

        self.addConnectionAct = EricAction(
            self.tr("Add Connection"),
            EricPixmapCache.getIcon("databaseConnection"),
            self.tr("Add &Connection..."),
            0,
            0,
            self,
            "sql_file_add_connection",
        )
        self.addConnectionAct.setStatusTip(
            self.tr("Open a dialog to add a new database connection")
        )
        self.addConnectionAct.setWhatsThis(
            self.tr(
                """<b>Add Connection</b>"""
                """<p>This opens a dialog to add a new database"""
                """ connection.</p>"""
            )
        )
        self.addConnectionAct.triggered.connect(self.__browser.addConnectionByDialog)
        self.__actions.append(self.addConnectionAct)

        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "sql_file_quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the SQL browser"))
        self.exitAct.setWhatsThis(
            self.tr("""<b>Quit</b><p>Quit the SQL browser.</p>""")
        )
        self.exitAct.triggered.connect(ericApp().closeAllWindows)

        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "sql_help_about"
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)
        self.__actions.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"), self.tr("About &Qt"), 0, 0, self, "sql_help_about_qt"
        )
        self.aboutQtAct.setStatusTip(
            self.tr("Display information about the Qt toolkit")
        )
        self.aboutQtAct.setWhatsThis(
            self.tr(
                """<b>About Qt</b>"""
                """<p>Display some information about the Qt toolkit.</p>"""
            )
        )
        self.aboutQtAct.triggered.connect(self.__aboutQt)
        self.__actions.append(self.aboutQtAct)

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.addConnectionAct)
        menu.addSeparator()
        menu.addAction(self.exitAct)

        mb.addSeparator()

        menu = mb.addMenu(self.tr("&Help"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.aboutAct)
        menu.addAction(self.aboutQtAct)

    def __initToolbars(self):
        """
        Private method to create the toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.setObjectName("FileToolBar")
        filetb.addAction(self.addConnectionAct)
        filetb.addSeparator()
        filetb.addAction(self.exitAct)

    def __about(self):
        """
        Private slot to show the about information.
        """
        EricMessageBox.about(
            self,
            self.tr("SQL Browser"),
            self.tr(
                """<h3>About SQL Browser</h3>"""
                """<p>The SQL browser window is a little tool to examine """
                """the data and the schema of a database and to execute """
                """queries on a database.</p>"""
            ),
        )

    def __aboutQt(self):
        """
        Private slot to show info about Qt.
        """
        EricMessageBox.aboutQt(self, self.tr("SQL Browser"))
