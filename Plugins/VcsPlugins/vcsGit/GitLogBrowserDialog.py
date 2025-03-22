# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to browse the log history.
"""

import collections
import contextlib
import os
import pathlib
import re

from PyQt6.QtCore import QDate, QPoint, QProcess, QSize, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QPainter, QPalette, QPen, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import strToQByteArray

from .GitDiffGenerator import GitDiffGenerator
from .GitDiffHighlighter import GitDiffHighlighter
from .Ui_GitLogBrowserDialog import Ui_GitLogBrowserDialog

COLORNAMES = [
    "red",
    "green",
    "purple",
    "cyan",
    "olive",
    "magenta",
    "gray",
    "yellow",
    "darkred",
    "darkgreen",
    "darkblue",
    "darkcyan",
    "darkmagenta",
    "blue",
]
COLORS = [str(QColor(x).name()) for x in COLORNAMES]

LIGHTCOLORS = [
    "#aaaaff",
    "#7faa7f",
    "#ffaaaa",
    "#aaffaa",
    "#7f7faa",
    "#ffaaff",
    "#aaffff",
    "#d5d579",
    "#ffaaff",
    "#d57979",
    "#d579d5",
    "#79d5d5",
    "#d5d5d5",
    "#d5d500",
]


class GitLogBrowserDialog(QWidget, Ui_GitLogBrowserDialog):
    """
    Class implementing a dialog to browse the log history.
    """

    IconColumn = 0
    CommitIdColumn = 1
    AuthorColumn = 2
    DateColumn = 3
    CommitterColumn = 4
    CommitDateColumn = 5
    SubjectColumn = 6
    BranchColumn = 7
    TagsColumn = 8

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        windowFlags = self.windowFlags()
        windowFlags |= Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(windowFlags)

        self.mainSplitter.setSizes([300, 400])
        self.mainSplitter.setStretchFactor(0, 1)
        self.mainSplitter.setStretchFactor(1, 2)
        self.diffSplitter.setStretchFactor(0, 1)
        self.diffSplitter.setStretchFactor(1, 2)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.filesTree.headerItem().setText(self.filesTree.columnCount(), "")
        self.filesTree.header().setSortIndicator(1, Qt.SortOrder.AscendingOrder)

        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.downButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list of commits"))
        self.refreshButton.setEnabled(False)

        self.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.__findBackwards = False

        self.modeComboBox.addItem(self.tr("Find"), "find")
        self.modeComboBox.addItem(self.tr("Filter"), "filter")

        self.fieldCombo.addItem(self.tr("Commit ID"), "commitId")
        self.fieldCombo.addItem(self.tr("Author"), "author")
        self.fieldCombo.addItem(self.tr("Committer"), "committer")
        self.fieldCombo.addItem(self.tr("Subject"), "subject")
        self.fieldCombo.addItem(self.tr("File"), "file")

        self.__logTreeNormalFont = self.logTree.font()
        self.__logTreeNormalFont.setBold(False)
        self.__logTreeBoldFont = self.logTree.font()
        self.__logTreeBoldFont.setBold(True)
        self.__logTreeHasDarkBackground = ericApp().usesDarkPalette()

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.diffEdit.document().setDefaultFont(font)

        self.diffHighlighter = GitDiffHighlighter(self.diffEdit.document())
        self.__diffGenerator = GitDiffGenerator(vcs, self)
        self.__diffGenerator.finished.connect(self.__generatorFinished)

        self.vcs = vcs

        self.__detailsTemplate = self.tr(
            "<table>"
            "<tr><td><b>Commit ID</b></td><td>{0}</td></tr>"
            "<tr><td colspan='2'>{10}</td></tr>"
            "<tr><td><b>Date</b></td><td>{1}</td></tr>"
            "<tr><td><b>Author</b></td><td>{2} &lt;{3}&gt;</td></tr>"
            "<tr><td><b>Commit Date</b></td><td>{4}</td></tr>"
            "<tr><td><b>Committer</b></td><td>{5} &lt;{6}&gt;</td></tr>"
            "{7}"
            "<tr><td><b>Subject</b></td><td>{8}</td></tr>"
            "{9}"
            "</table>"
        )
        self.__parentsTemplate = self.tr("<tr><td><b>Parents</b></td><td>{0}</td></tr>")
        self.__childrenTemplate = self.tr(
            "<tr><td><b>Children</b></td><td>{0}</td></tr>"
        )
        self.__branchesTemplate = self.tr(
            "<tr><td><b>Branches</b></td><td>{0}</td></tr>"
        )
        self.__tagsTemplate = self.tr("<tr><td><b>Tags</b></td><td>{0}</td></tr>")
        self.__mesageTemplate = self.tr("<tr><td><b>Message</b></td><td>{0}</td></tr>")

        self.__formatTemplate = (
            "format:recordstart%n"
            "commit|%h%n"
            "fullcommit|%H%n"
            "parents|%p%n"
            "author|%an%n"
            "authormail|%ae%n"
            "authordate|%ai%n"
            "committer|%cn%n"
            "committermail|%ce%n"
            "committerdate|%ci%n"
            "refnames|%d%n"
            "subject|%s%n"
            "bodystart%n"
            "%b%n"
            "bodyend%n"
        )

        self.__filename = ""
        self.__isFile = False
        self.__selectedCommitIDs = []
        self.intercept = False

        self.__initData()

        self.fromDate.setDisplayFormat("yyyy-MM-dd")
        self.toDate.setDisplayFormat("yyyy-MM-dd")
        self.__resetUI()

        # roles used in the log tree
        self.__subjectRole = Qt.ItemDataRole.UserRole
        self.__messageRole = Qt.ItemDataRole.UserRole + 1
        self.__changesRole = Qt.ItemDataRole.UserRole + 2
        self.__edgesRole = Qt.ItemDataRole.UserRole + 3
        self.__parentsRole = Qt.ItemDataRole.UserRole + 4
        self.__branchesRole = Qt.ItemDataRole.UserRole + 5
        self.__authorMailRole = Qt.ItemDataRole.UserRole + 6
        self.__committerMailRole = Qt.ItemDataRole.UserRole + 7
        self.__fullCommitIdRole = Qt.ItemDataRole.UserRole + 8

        # roles used in the file tree
        self.__diffFileLineRole = Qt.ItemDataRole.UserRole

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        self.flags = {
            "A": self.tr("Added"),
            "D": self.tr("Deleted"),
            "M": self.tr("Modified"),
            "C": self.tr("Copied"),
            "R": self.tr("Renamed"),
            "T": self.tr("Type changed"),
            "U": self.tr("Unmerged"),
            "X": self.tr("Unknown"),
        }

        self.__dotRadius = 8
        self.__rowHeight = 20

        self.logTree.setIconSize(QSize(100 * self.__rowHeight, self.__rowHeight))

        self.detailsEdit.anchorClicked.connect(self.__commitIdClicked)

        self.__initLogTreeContextMenu()
        self.__initActionsMenu()

        self.__finishCallbacks = []

    def __addFinishCallback(self, callback):
        """
        Private method to add a method to be called once the process finished.

        The callback methods are invoke in a FIFO style and are consumed. If
        a callback method needs to be called again, it must be added again.

        @param callback callback method
        @type function
        """
        if callback not in self.__finishCallbacks:
            self.__finishCallbacks.append(callback)

    def __initLogTreeContextMenu(self):
        """
        Private method to initialize the log tree context menu.
        """
        self.__logTreeMenu = QMenu()

        # commit ID column
        act = self.__logTreeMenu.addAction(self.tr("Show Commit ID Column"))
        act.setToolTip(self.tr("Press to show the commit ID column"))
        act.setCheckable(True)
        act.setChecked(self.vcs.getPlugin().getPreferences("ShowCommitIdColumn"))
        act.triggered.connect(self.__showCommitIdColumn)

        # author and date columns
        act = self.__logTreeMenu.addAction(self.tr("Show Author Columns"))
        act.setToolTip(self.tr("Press to show the author columns"))
        act.setCheckable(True)
        act.setChecked(self.vcs.getPlugin().getPreferences("ShowAuthorColumns"))
        act.triggered.connect(self.__showAuthorColumns)

        # committer and commit date columns
        act = self.__logTreeMenu.addAction(self.tr("Show Committer Columns"))
        act.setToolTip(self.tr("Press to show the committer columns"))
        act.setCheckable(True)
        act.setChecked(self.vcs.getPlugin().getPreferences("ShowCommitterColumns"))
        act.triggered.connect(self.__showCommitterColumns)

        # branches column
        act = self.__logTreeMenu.addAction(self.tr("Show Branches Column"))
        act.setToolTip(self.tr("Press to show the branches column"))
        act.setCheckable(True)
        act.setChecked(self.vcs.getPlugin().getPreferences("ShowBranchesColumn"))
        act.triggered.connect(self.__showBranchesColumn)

        # tags column
        act = self.__logTreeMenu.addAction(self.tr("Show Tags Column"))
        act.setToolTip(self.tr("Press to show the Tags column"))
        act.setCheckable(True)
        act.setChecked(self.vcs.getPlugin().getPreferences("ShowTagsColumn"))
        act.triggered.connect(self.__showTagsColumn)

        # set column visibility as configured
        self.__showCommitIdColumn(
            self.vcs.getPlugin().getPreferences("ShowCommitIdColumn")
        )
        self.__showAuthorColumns(
            self.vcs.getPlugin().getPreferences("ShowAuthorColumns")
        )
        self.__showCommitterColumns(
            self.vcs.getPlugin().getPreferences("ShowCommitterColumns")
        )
        self.__showBranchesColumn(
            self.vcs.getPlugin().getPreferences("ShowBranchesColumn")
        )
        self.__showTagsColumn(self.vcs.getPlugin().getPreferences("ShowTagsColumn"))

    def __initActionsMenu(self):
        """
        Private method to initialize the actions menu.
        """
        self.__actionsMenu = QMenu()
        self.__actionsMenu.setTearOffEnabled(True)
        self.__actionsMenu.setToolTipsVisible(True)

        self.__cherryAct = self.__actionsMenu.addAction(
            self.tr("Copy Commits"), self.__cherryActTriggered
        )
        self.__cherryAct.setToolTip(
            self.tr("Cherry-pick the selected commits to the current branch")
        )

        self.__actionsMenu.addSeparator()

        self.__tagAct = self.__actionsMenu.addAction(
            self.tr("Tag"), self.__tagActTriggered
        )
        self.__tagAct.setToolTip(self.tr("Tag the selected commit"))

        self.__branchAct = self.__actionsMenu.addAction(
            self.tr("Branch"), self.__branchActTriggered
        )
        self.__branchAct.setToolTip(
            self.tr("Create a new branch at the selected commit.")
        )
        self.__branchSwitchAct = self.__actionsMenu.addAction(
            self.tr("Branch && Switch"), self.__branchSwitchActTriggered
        )
        self.__branchSwitchAct.setToolTip(
            self.tr(
                "Create a new branch at the selected commit and switch"
                " the work tree to it."
            )
        )

        self.__switchAct = self.__actionsMenu.addAction(
            self.tr("Switch"), self.__switchActTriggered
        )
        self.__switchAct.setToolTip(
            self.tr("Switch the working directory to the selected commit")
        )
        self.__actionsMenu.addSeparator()

        self.__shortlogAct = self.__actionsMenu.addAction(
            self.tr("Show Short Log"), self.__shortlogActTriggered
        )
        self.__shortlogAct.setToolTip(
            self.tr("Show a dialog with a log output for release notes")
        )

        self.__describeAct = self.__actionsMenu.addAction(
            self.tr("Describe"), self.__describeActTriggered
        )
        self.__describeAct.setToolTip(
            self.tr("Show the most recent tag reachable from a commit")
        )

        self.actionsButton.setIcon(EricPixmapCache.getIcon("actionsToolButton"))
        self.actionsButton.setMenu(self.__actionsMenu)

    def __initData(self):
        """
        Private method to (re-)initialize some data.
        """
        self.__maxDate = QDate()
        self.__minDate = QDate()
        self.__filterLogsEnabled = True

        self.buf = []  # buffer for stdout
        self.diff = None
        self.__started = False
        self.__skipEntries = 0
        self.projectMode = False

        # attributes to store log graph data
        self.__commitIds = []
        self.__commitColors = {}
        self.__commitColor = 0

        self.__projectRevision = ""

        self.__childrenInfo = collections.defaultdict(list)

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.vcs.getPlugin().setPreferences("LogBrowserGeometry", self.saveGeometry())
        self.vcs.getPlugin().setPreferences(
            "LogBrowserSplitterStates",
            [
                self.mainSplitter.saveState(),
                self.detailsSplitter.saveState(),
                self.diffSplitter.saveState(),
            ],
        )

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        self.__reloadGeometry()
        self.__restoreSplitterStates()
        self.__resetUI()

        super().show()

    def __reloadGeometry(self):
        """
        Private method to restore the geometry.
        """
        geom = self.vcs.getPlugin().getPreferences("LogBrowserGeometry")
        if geom.isEmpty():
            s = QSize(1000, 800)
            self.resize(s)
        else:
            self.restoreGeometry(geom)

    def __restoreSplitterStates(self):
        """
        Private method to restore the state of the various splitters.
        """
        states = self.vcs.getPlugin().getPreferences("LogBrowserSplitterStates")
        if len(states) == 3:
            # we have three splitters
            self.mainSplitter.restoreState(states[0])
            self.detailsSplitter.restoreState(states[1])
            self.diffSplitter.restoreState(states[2])

    def __resetUI(self):
        """
        Private method to reset the user interface.
        """
        self.fromDate.setDate(QDate.currentDate())
        self.toDate.setDate(QDate.currentDate())
        self.fieldCombo.setCurrentIndex(self.fieldCombo.findData("subject"))
        self.limitSpinBox.setValue(self.vcs.getPlugin().getPreferences("LogLimit"))
        self.stopCheckBox.setChecked(
            self.vcs.getPlugin().getPreferences("StopLogOnCopy")
        )

        self.logTree.clear()

    def __resizeColumnsLog(self):
        """
        Private method to resize the log tree columns.
        """
        self.logTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.logTree.header().setStretchLastSection(True)

    def __resizeColumnsFiles(self):
        """
        Private method to resize the changed files tree columns.
        """
        self.filesTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.filesTree.header().setStretchLastSection(True)

    def __resortFiles(self):
        """
        Private method to resort the changed files tree.
        """
        self.filesTree.setSortingEnabled(True)
        self.filesTree.sortItems(1, Qt.SortOrder.AscendingOrder)
        self.filesTree.setSortingEnabled(False)

    def __getColor(self, n):
        """
        Private method to get the (rotating) name of the color given an index.

        @param n color index
        @type int
        @return color name
        @rtype str
        """
        if self.__logTreeHasDarkBackground:
            return LIGHTCOLORS[n % len(LIGHTCOLORS)]
        else:
            return COLORS[n % len(COLORS)]

    def __generateEdges(self, commitId, parents):
        """
        Private method to generate edge info for the give data.

        @param commitId commit id to calculate edge info for
        @type str
        @param parents list of parent commits
        @type list of str
        @return tuple containing the column and color index for
            the given node and a list of tuples indicating the edges
            between the given node and its parents
        @rtype tuple of (int, int, [(int, int, int), ...])
        """
        if commitId not in self.__commitIds:
            # new head
            self.__commitIds.append(commitId)
            self.__commitColors[commitId] = self.__commitColor
            self.__commitColor += 1

        col = self.__commitIds.index(commitId)
        color = self.__commitColors.pop(commitId)
        nextCommitIds = self.__commitIds[:]

        # add parents to next
        addparents = [p for p in parents if p not in nextCommitIds]
        nextCommitIds[col : col + 1] = addparents

        # set colors for the parents
        for i, p in enumerate(addparents):
            if not i:
                self.__commitColors[p] = color
            else:
                self.__commitColors[p] = self.__commitColor
                self.__commitColor += 1

        # add edges to the graph
        edges = []
        if parents:
            for ecol, ecommitId in enumerate(self.__commitIds):
                if ecommitId in nextCommitIds:
                    edges.append(
                        (
                            ecol,
                            nextCommitIds.index(ecommitId),
                            self.__commitColors[ecommitId],
                        )
                    )
                elif ecommitId == commitId:
                    for p in parents:
                        edges.append(
                            (ecol, nextCommitIds.index(p), self.__commitColors[p])
                        )

        self.__commitIds = nextCommitIds
        return col, color, edges

    def __generateIcon(self, column, bottomedges, topedges, dotColor, currentCommit):
        """
        Private method to generate an icon containing the revision tree for the
        given data.

        @param column column index of the revision
        @type int
        @param bottomedges list of edges for the bottom of the node
        @type list of [(int, int, int)]
        @param topedges list of edges for the top of the node
        @type list of [(int, int, int)]
        @param dotColor color to be used for the dot
        @type QColor
        @param currentCommit flag indicating to draw the icon for the
            current commit
        @type bool
        @return icon for the node
        @rtype QIcon
        """

        def col2x(col, radius):
            """
            Local function to calculate a x-position for a column.

            @param col column number
            @type int
            @param radius radius of the indicator circle
            @type int
            """
            return int(1.2 * radius) * col + radius // 2 + 3

        radius = self.__dotRadius
        w = len(bottomedges) * radius + 20
        h = self.__rowHeight

        dot_x = col2x(column, radius) - radius // 2
        dot_y = h // 2

        pix = QPixmap(w, h)
        pix.fill(QColor(0, 0, 0, 0))  # draw transparent background
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # draw the revision history lines
        for y1, y2, lines in ((0, h, bottomedges), (-h, 0, topedges)):
            if lines:
                for start, end, ecolor in lines:
                    lpen = QPen(QColor(self.__getColor(ecolor)))
                    lpen.setWidth(2)
                    painter.setPen(lpen)
                    x1 = col2x(start, radius)
                    x2 = col2x(end, radius)
                    painter.drawLine(x1, dot_y + y1, x2, dot_y + y2)

        penradius = 1
        pencolor = self.logTree.palette().color(QPalette.ColorRole.Text)

        dot_y = (h // 2) - radius // 2

        # draw a dot for the revision
        if currentCommit:
            # enlarge dot for the current revision
            delta = 2
            radius += 2 * delta
            dot_y -= delta
            dot_x -= delta
        painter.setBrush(dotColor)
        pen = QPen(pencolor)
        pen.setWidth(penradius)
        painter.setPen(pen)
        painter.drawEllipse(dot_x, dot_y, radius, radius)
        painter.end()
        return QIcon(pix)

    def __identifyProject(self):
        """
        Private method to determine the revision of the project directory.
        """
        errMsg = ""

        args = self.vcs.initCommand("show")
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        args.append("--format=%h")
        args.append("--no-patch")
        args.append("HEAD")

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )
            else:
                if not finished:
                    errMsg = self.tr("The git process did not finish within 30s.")
        else:
            errMsg = self.tr("Could not start the git executable.")

        if errMsg:
            EricMessageBox.critical(self, self.tr("Git Error"), errMsg)

        if output:
            self.__projectRevision = output.strip()

    def __generateLogItem(
        self,
        author,
        date,
        committer,
        commitDate,
        subject,
        message,
        commitId,
        fullCommitId,
        changedPaths,
        parents,
        refnames,
        authorMail,
        committerMail,
    ):
        """
        Private method to generate a log tree entry.

        @param author author info
        @type str
        @param date date info
        @type str
        @param committer committer info
        @type str
        @param commitDate commit date info
        @type str
        @param subject subject of the log entry
        @type str
        @param message text of the log message
        @type list of str
        @param commitId commit id info
        @type str
        @param fullCommitId unabbreviated commit id info
        @type str
        @param changedPaths list of dictionary objects containing
            info about the changed files/directories
        @type list of dict
        @param parents list of parent revisions
        @type list of int
        @param refnames tags and branches of the commit
        @type str
        @param authorMail author's email address
        @type str
        @param committerMail committer's email address
        @type str
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        branches = []
        allBranches = []
        tags = []
        names = refnames.strip()[1:-1].split(",")
        for name in names:
            name = name.strip()
            if name:
                if "HEAD" in name:
                    tags.append(name)
                elif name.startswith("tag: "):
                    tags.append(name.split()[1])
                else:
                    if "/" not in name:
                        branches.append(name)
                    elif "refs/bisect/" in name:
                        bname = name.replace("refs/", "").split("-", 1)[0]
                        branches.append(bname)
                    else:
                        branches.append(name)
                    allBranches.append(name)

        logMessageColumnWidth = self.vcs.getPlugin().getPreferences(
            "LogSubjectColumnWidth"
        )
        msgtxt = subject
        if logMessageColumnWidth and len(msgtxt) > logMessageColumnWidth:
            msgtxt = "{0}...".format(msgtxt[:logMessageColumnWidth])
        columnLabels = [
            "",
            commitId,
            author,
            date.rsplit(None, 1)[0].rsplit(":", 1)[0],
            committer,
            commitDate.rsplit(None, 1)[0].rsplit(":", 1)[0],
            msgtxt,
            ", ".join(branches),
            ", ".join(tags),
        ]
        itm = QTreeWidgetItem(self.logTree, columnLabels)

        parents = [p.strip() for p in parents.split()]
        column, color, edges = self.__generateEdges(commitId, parents)

        itm.setData(0, self.__subjectRole, subject)
        itm.setData(0, self.__messageRole, message)
        itm.setData(0, self.__changesRole, changedPaths)
        itm.setData(0, self.__edgesRole, edges)
        itm.setData(0, self.__branchesRole, allBranches)
        itm.setData(0, self.__authorMailRole, authorMail)
        itm.setData(0, self.__committerMailRole, committerMail)
        itm.setData(0, self.__fullCommitIdRole, fullCommitId)
        if not parents:
            itm.setData(0, self.__parentsRole, [])
        else:
            itm.setData(0, self.__parentsRole, parents)
            for parent in parents:
                self.__childrenInfo[parent].append(commitId)

        topedges = (
            self.logTree.topLevelItem(self.logTree.indexOfTopLevelItem(itm) - 1).data(
                0, self.__edgesRole
            )
            if self.logTree.topLevelItemCount() > 1
            else None
        )

        icon = self.__generateIcon(
            column,
            edges,
            topedges,
            QColor("blue"),
            commitId == self.__projectRevision,
        )
        itm.setIcon(0, icon)

        return itm

    def __generateFileItem(self, action, path, copyfrom, additions, deletions):
        """
        Private method to generate a changed files tree entry.

        @param action indicator for the change action ("A", "C", "D", "M",
            "R", "T", "U", "X")
        @type str
        @param path path of the file in the repository
        @type str
        @param copyfrom path the file was copied from
        @type str
        @param additions number of added lines
        @type int
        @param deletions number of deleted lines
        @type int
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        if len(action) > 1:
            # includes confidence level
            confidence = int(action[1:])
            actionTxt = self.tr("{0} ({1}%)", "action, confidence").format(
                self.flags[action[0]], confidence
            )
        else:
            actionTxt = self.flags[action]
        itm = QTreeWidgetItem(
            self.filesTree,
            [
                actionTxt,
                path,
                str(additions),
                str(deletions),
                copyfrom,
            ],
        )

        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(3, Qt.AlignmentFlag.AlignRight)

        return itm

    def __getLogEntries(self, skip=0, noEntries=0):
        """
        Private method to retrieve log entries from the repository.

        @param skip number of log entries to skip
        @type int
        @param noEntries number of entries to get (0 = default)
        @type int
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        QApplication.processEvents()

        self.buf = []
        self.cancelled = False
        self.errors.clear()
        self.intercept = False

        if noEntries == 0:
            noEntries = self.limitSpinBox.value()

        args = self.vcs.initCommand("log")
        args.append("--max-count={0}".format(noEntries))
        args.append("--numstat")
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        if self.vcs.getPlugin().getPreferences("FindCopiesHarder"):
            args.append("--find-copies-harder")
        args.append("--format={0}".format(self.__formatTemplate))
        args.append("--full-history")
        args.append("--all")
        args.append("--skip={0}".format(skip))
        if not self.projectMode:
            if not self.stopCheckBox.isChecked():
                args.append("--follow")
            args.append("--")
            args.append(self.__filename)

        self.__process.kill()

        self.__process.setWorkingDirectory(self.repodir)

        self.__process.start("git", args)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
            self.inputGroup.setEnabled(False)
            self.inputGroup.hide()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("git"),
            )

    def start(self, fn, isFile=False, noEntries=0):
        """
        Public slot to start the git log command.

        @param fn filename to show the log for
        @type str
        @param isFile flag indicating log for a file is to be shown
        @type bool
        @param noEntries number of entries to get (0 = default)
        @type int
        """
        self.__isFile = isFile

        self.sbsSelectLabel.clear()

        self.errorGroup.hide()
        QApplication.processEvents()

        self.__initData()

        self.__filename = fn
        self.dname, self.fname = self.vcs.splitPath(fn)

        # find the root of the repo
        self.repodir = self.vcs.findRepoRoot(self.dname)
        if not self.repodir:
            return

        self.projectMode = self.fname == "." and self.dname == self.repodir
        self.stopCheckBox.setDisabled(self.projectMode or self.fname == ".")
        self.activateWindow()
        self.raise_()

        self.logTree.clear()
        self.__started = True
        self.__identifyProject()
        self.__getLogEntries(noEntries=noEntries)

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__processBuffer()
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()
        self.refreshButton.setEnabled(True)

        while self.__finishCallbacks:
            self.__finishCallbacks.pop(0)()

    def __processBufferItem(self, logEntry):
        """
        Private method to process a log entry.

        @param logEntry dictionary as generated by __processBuffer
        @type dict
        """
        self.__generateLogItem(
            logEntry["author"],
            logEntry["authordate"],
            logEntry["committer"],
            logEntry["committerdate"],
            logEntry["subject"],
            logEntry["body"],
            logEntry["commit"],
            logEntry["fullcommit"],
            logEntry["changed_files"],
            logEntry["parents"],
            logEntry["refnames"],
            logEntry["authormail"],
            logEntry["committermail"],
        )
        for date in [logEntry["authordate"], logEntry["committerdate"]]:
            dt = QDate.fromString(date, Qt.DateFormat.ISODate)
            if not self.__maxDate.isValid() and not self.__minDate.isValid():
                self.__maxDate = dt
                self.__minDate = dt
            else:
                if self.__maxDate < dt:
                    self.__maxDate = dt
                if self.__minDate > dt:
                    self.__minDate = dt

    def __processBuffer(self):
        """
        Private method to process the buffered output of the git log command.
        """
        noEntries = 0
        logEntry = {"changed_files": []}
        descriptionBody = False

        for line in self.buf:
            line = line.rstrip()
            if line == "recordstart":
                if len(logEntry) > 1:
                    self.__processBufferItem(logEntry)
                    noEntries += 1
                logEntry = {"changed_files": []}
                descriptionBody = False
                fileChanges = False
                body = []
            elif line == "bodystart":
                descriptionBody = True
            elif line == "bodyend":
                if bool(body) and not bool(body[-1]):
                    body.pop()
                logEntry["body"] = body
                descriptionBody = False
                fileChanges = True
            elif descriptionBody:
                body.append(line)
            elif fileChanges:
                if line:
                    if "changed_files" not in logEntry:
                        logEntry["changed_files"] = []
                    changeInfo = line.strip().split("\t")
                    if "=>" in changeInfo[2]:
                        # copy/move
                        if "{" in changeInfo[2] and "}" in changeInfo[2]:
                            # change info of the form
                            # test/{pack1 => pack2}/file1.py
                            head, tail = changeInfo[2].split("{", 1)
                            middle, tail = tail.split("}", 1)
                            middleSrc, middleDst = middle.split("=>")
                            src = head + middleSrc.strip() + tail
                            dst = head + middleDst.strip() + tail
                        else:
                            src, dst = changeInfo[2].split("=>")
                        logEntry["changed_files"].append(
                            {
                                "action": "C",
                                "added": changeInfo[0].strip(),
                                "deleted": changeInfo[1].strip(),
                                "path": dst.strip(),
                                "copyfrom": src.strip(),
                            }
                        )
                    else:
                        logEntry["changed_files"].append(
                            {
                                "action": "M",
                                "added": changeInfo[0].strip(),
                                "deleted": changeInfo[1].strip(),
                                "path": changeInfo[2].strip(),
                                "copyfrom": "",
                            }
                        )
            else:
                try:
                    key, value = line.split("|", 1)
                except ValueError:
                    key = ""
                    value = line
                if key in (
                    "commit",
                    "fullcommit",
                    "parents",
                    "author",
                    "authormail",
                    "authordate",
                    "committer",
                    "committermail",
                    "committerdate",
                    "refnames",
                    "subject",
                ):
                    logEntry[key] = value.strip()
        if len(logEntry) > 1:
            self.__processBufferItem(logEntry)
            noEntries += 1

        self.__resizeColumnsLog()

        if self.__started:
            if self.__selectedCommitIDs:
                self.logTree.setCurrentItem(
                    self.logTree.findItems(
                        self.__selectedCommitIDs[0],
                        Qt.MatchFlag.MatchExactly,
                        self.CommitIdColumn,
                    )[0]
                )
            else:
                self.logTree.setCurrentItem(self.logTree.topLevelItem(0))
            self.__started = False

        self.__skipEntries += noEntries
        if noEntries < self.limitSpinBox.value() and not self.cancelled:
            self.nextButton.setEnabled(False)
            self.limitSpinBox.setEnabled(False)
        else:
            self.nextButton.setEnabled(True)
            self.limitSpinBox.setEnabled(True)

        # update the log filters
        self.__filterLogsEnabled = False
        self.fromDate.setMinimumDate(self.__minDate)
        self.fromDate.setMaximumDate(self.__maxDate)
        self.fromDate.setDate(self.__minDate)
        self.toDate.setMinimumDate(self.__minDate)
        self.toDate.setMaximumDate(self.__maxDate)
        self.toDate.setDate(self.__maxDate)

        self.__filterLogsEnabled = True
        if self.__actionMode() == "filter":
            self.__filterLogs()

        self.__updateToolMenuActions()

        # restore selected items
        if self.__selectedCommitIDs:
            for commitID in self.__selectedCommitIDs:
                items = self.logTree.findItems(
                    commitID, Qt.MatchFlag.MatchExactly, self.CommitIdColumn
                )
                if items:
                    items[0].setSelected(True)
            self.__selectedCommitIDs = []

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into a buffer.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.__process.canReadLine():
            line = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.buf.append(line)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            s = str(
                self.__process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__showError(s)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

        # show input in case the process asked for some input
        self.inputGroup.setEnabled(True)
        self.inputGroup.show()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.cancelled = True
            self.__finish()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the log.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.refreshButton.setEnabled(False)

        # save the selected items commit IDs
        self.__selectedCommitIDs = []
        for item in self.logTree.selectedItems():
            self.__selectedCommitIDs.append(item.text(self.CommitIdColumn))

        self.start(
            self.__filename,
            isFile=self.__isFile,
            noEntries=self.logTree.topLevelItemCount(),
        )

    def on_passwordCheckBox_toggled(self, isOn):
        """
        Private slot to handle the password checkbox toggled.

        @param isOn flag indicating the status of the check box
        @type bool
        """
        if isOn:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)

    @pyqtSlot()
    def on_sendButton_clicked(self):
        """
        Private slot to send the input to the git process.
        """
        inputTxt = self.input.text()
        inputTxt += os.linesep

        if self.passwordCheckBox.isChecked():
            self.errors.insertPlainText(os.linesep)
            self.errors.ensureCursorVisible()
        else:
            self.errors.insertPlainText(inputTxt)
            self.errors.ensureCursorVisible()
        self.errorGroup.show()

        self.__process.write(strToQByteArray(inputTxt))

        self.passwordCheckBox.setChecked(False)
        self.input.clear()

    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.intercept = True
        self.on_sendButton_clicked()

    def keyPressEvent(self, evt):
        """
        Protected slot to handle a key press event.

        @param evt the key press event
        @type QKeyEvent
        """
        if self.intercept:
            self.intercept = False
            evt.accept()
            return
        super().keyPressEvent(evt)

    def __prepareFieldSearch(self):
        """
        Private slot to prepare the filed search data.

        @return tuple of field index, search expression and flag indicating
            that the field index is a data role
        @rtype tuple of (int, str, bool)
        """
        indexIsRole = False
        txt = self.fieldCombo.itemData(self.fieldCombo.currentIndex())
        if txt == "author":
            fieldIndex = self.AuthorColumn
            searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)
        elif txt == "committer":
            fieldIndex = self.CommitterColumn
            searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)
        elif txt == "commitId":
            fieldIndex = self.CommitIdColumn
            txt = self.rxEdit.text()
            if txt.startswith("^"):
                searchRx = re.compile(r"^\s*{0}".format(txt[1:]), re.IGNORECASE)
            else:
                searchRx = re.compile(txt, re.IGNORECASE)
        elif txt == "file":
            fieldIndex = self.__changesRole
            searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)
            indexIsRole = True
        else:
            fieldIndex = self.__subjectRole
            searchRx = re.compile(self.rxEdit.text(), re.IGNORECASE)
            indexIsRole = True

        return fieldIndex, searchRx, indexIsRole

    def __filterLogs(self):
        """
        Private method to filter the log entries.
        """
        if self.__filterLogsEnabled:
            from_ = self.fromDate.date().toString("yyyy-MM-dd")
            to_ = self.toDate.date().addDays(1).toString("yyyy-MM-dd")
            fieldIndex, searchRx, indexIsRole = self.__prepareFieldSearch()

            visibleItemCount = self.logTree.topLevelItemCount()
            currentItem = self.logTree.currentItem()
            for topIndex in range(self.logTree.topLevelItemCount()):
                topItem = self.logTree.topLevelItem(topIndex)
                if indexIsRole:
                    if fieldIndex == self.__changesRole:
                        changes = topItem.data(0, self.__changesRole)
                        txt = "\n".join(
                            [c["path"] for c in changes]
                            + [c["copyfrom"] for c in changes]
                        )
                    else:
                        # Filter based on complete subject text
                        txt = topItem.data(0, self.__subjectRole)
                else:
                    txt = topItem.text(fieldIndex)
                if (
                    topItem.text(self.DateColumn) <= to_
                    and topItem.text(self.DateColumn) >= from_
                    and searchRx.search(txt) is not None
                ):
                    topItem.setHidden(False)
                    if topItem is currentItem:
                        self.on_logTree_currentItemChanged(topItem, None)
                else:
                    topItem.setHidden(True)
                    if topItem is currentItem:
                        self.filesTree.clear()
                    visibleItemCount -= 1
            self.logTree.header().setSectionHidden(
                self.IconColumn, visibleItemCount != self.logTree.topLevelItemCount()
            )

    def __updateSbsSelectLabel(self):
        """
        Private slot to update the enabled status of the diff buttons.
        """
        self.sbsSelectLabel.clear()
        if self.__isFile:
            selectedItems = self.logTree.selectedItems()
            if len(selectedItems) == 1:
                currentItem = selectedItems[0]
                commit2 = currentItem.text(self.CommitIdColumn).strip()
                parents = currentItem.data(0, self.__parentsRole)
                if parents:
                    parentLinks = []
                    for index in range(len(parents)):
                        parentLinks.append(
                            '<a href="sbsdiff:{0}_{1}">&nbsp;{2}&nbsp;</a>'.format(
                                parents[index], commit2, index + 1
                            )
                        )
                    self.sbsSelectLabel.setText(
                        self.tr("Side-by-Side Diff to Parent {0}").format(
                            " ".join(parentLinks)
                        )
                    )
            elif len(selectedItems) == 2:
                commit2 = selectedItems[0].text(self.CommitIdColumn)
                commit1 = selectedItems[1].text(self.CommitIdColumn)
                index2 = self.logTree.indexOfTopLevelItem(selectedItems[0])
                index1 = self.logTree.indexOfTopLevelItem(selectedItems[1])

                if index2 < index1:
                    # swap to always compare old to new
                    commit1, commit2 = commit2, commit1
                self.sbsSelectLabel.setText(
                    self.tr(
                        '<a href="sbsdiff:{0}_{1}">Side-by-Side Compare</a>'
                    ).format(commit1, commit2)
                )

    def __updateToolMenuActions(self):
        """
        Private slot to update the status of the tool menu actions and
        the tool menu button.
        """
        if self.projectMode:
            selectCount = len(self.logTree.selectedItems())
            self.__cherryAct.setEnabled(selectCount > 0)
            self.__describeAct.setEnabled(selectCount > 0)
            self.__tagAct.setEnabled(selectCount == 1)
            self.__switchAct.setEnabled(selectCount == 1)
            self.__branchAct.setEnabled(selectCount == 1)
            self.__branchSwitchAct.setEnabled(selectCount == 1)
            self.__shortlogAct.setEnabled(selectCount == 1)

            self.actionsButton.setEnabled(True)
        else:
            self.actionsButton.setEnabled(False)

    def __updateDetailsAndFiles(self):
        """
        Private slot to update the details and file changes panes.
        """
        self.detailsEdit.clear()
        self.filesTree.clear()
        self.__diffUpdatesFiles = False

        selectedItems = self.logTree.selectedItems()
        if len(selectedItems) == 1:
            self.detailsEdit.setHtml(self.__generateDetailsTableText(selectedItems[0]))
            self.__updateFilesTree(selectedItems[0])
            self.__resizeColumnsFiles()
            self.__resortFiles()
            if self.filesTree.topLevelItemCount() == 0:
                self.__diffUpdatesFiles = True
                # give diff a chance to update the files list
        elif len(selectedItems) == 2:
            self.__diffUpdatesFiles = True
            index1 = self.logTree.indexOfTopLevelItem(selectedItems[0])
            index2 = self.logTree.indexOfTopLevelItem(selectedItems[1])
            if index1 > index2:
                # Swap the entries
                selectedItems[0], selectedItems[1] = (
                    selectedItems[1],
                    selectedItems[0],
                )
            html = "{0}<hr/>{1}".format(
                self.__generateDetailsTableText(selectedItems[0]),
                self.__generateDetailsTableText(selectedItems[1]),
            )
            self.detailsEdit.setHtml(html)
            # self.filesTree is updated by the diff

    def __generateDetailsTableText(self, itm):
        """
        Private method to generate an HTML table with the details of the given
        changeset.

        @param itm reference to the item the table should be based on
        @type QTreeWidgetItem
        @return HTML table containing details
        @rtype str
        """
        if itm is not None:
            commitId = itm.text(self.CommitIdColumn)

            parentLinks = []
            for parent in [str(x) for x in itm.data(0, self.__parentsRole)]:
                parentLinks.append('<a href="rev:{0}">{0}</a>'.format(parent))
            if parentLinks:
                parentsStr = self.__parentsTemplate.format(", ".join(parentLinks))
            else:
                parentsStr = ""

            childLinks = []
            for child in [str(x) for x in self.__childrenInfo[commitId]]:
                childLinks.append('<a href="rev:{0}">{0}</a>'.format(child))
            if childLinks:
                childrenStr = self.__childrenTemplate.format(", ".join(childLinks))
            else:
                childrenStr = ""

            branchLinks = []
            for branch, branchHead in self.__getBranchesForCommit(commitId):
                branchLinks.append(
                    '<a href="rev:{0}">{1}</a>'.format(branchHead, branch)
                )
            if branchLinks:
                branchesStr = self.__branchesTemplate.format(", ".join(branchLinks))
            else:
                branchesStr = ""

            tagLinks = []
            for tag, tagCommit in self.__getTagsForCommit(commitId):
                if tagCommit:
                    tagLinks.append('<a href="rev:{0}">{1}</a>'.format(tagCommit, tag))
                else:
                    tagLinks.append(tag)
            if tagLinks:
                tagsStr = self.__tagsTemplate.format(", ".join(tagLinks))
            else:
                tagsStr = ""

            if itm.data(0, self.__messageRole):
                messageStr = self.__mesageTemplate.format(
                    "<br/>".join(itm.data(0, self.__messageRole))
                )
            else:
                messageStr = ""

            html = self.__detailsTemplate.format(
                commitId,
                itm.text(self.DateColumn),
                itm.text(self.AuthorColumn),
                itm.data(0, self.__authorMailRole).strip(),
                itm.text(self.CommitDateColumn),
                itm.text(self.CommitterColumn),
                itm.data(0, self.__committerMailRole).strip(),
                parentsStr + childrenStr + branchesStr + tagsStr,
                itm.data(0, self.__subjectRole),
                messageStr,
                itm.data(0, self.__fullCommitIdRole).strip(),
            )
        else:
            html = ""

        return html

    def __updateFilesTree(self, itm):
        """
        Private method to update the files tree with changes of the given item.

        @param itm reference to the item the update should be based on
        @type QTreeWidgetItem
        """
        if itm is not None:
            changes = itm.data(0, self.__changesRole)
            if len(changes) > 0:
                for change in changes:
                    self.__generateFileItem(
                        change["action"],
                        change["path"],
                        change["copyfrom"],
                        change["added"],
                        change["deleted"],
                    )
                self.__resizeColumnsFiles()
                self.__resortFiles()

    def __getBranchesForCommit(self, commitId):
        """
        Private method to get all branches reachable from a commit ID.

        @param commitId commit ID to get the branches for
        @type str
        @return list of tuples containing the branch name and the associated
            commit ID of its branch head
        @rtype tuple of (str, str)
        """
        branches = []

        args = self.vcs.initCommand("branch")
        args.append("--list")
        args.append("--verbose")
        args.append("--contains")
        args.append(commitId)

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )

        if output:
            for line in output.splitlines():
                name, commitId = line[2:].split(None, 2)[:2]
                branches.append((name, commitId))

        return branches

    def __getTagsForCommit(self, commitId):
        """
        Private method to get all tags reachable from a commit ID.

        @param commitId commit ID to get the tags for
        @type str
        @return list of tuples containing the tag name and the associated
            commit ID
        @rtype tuple of (str, str)
        """
        tags = []

        args = self.vcs.initCommand("tag")
        args.append("--list")
        args.append("--contains")
        args.append(commitId)

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )

        if output:
            tagNames = []
            for line in output.splitlines():
                tagNames.append(line.strip())

            # determine the commit IDs for the tags
            for tagName in tagNames:
                commitId = self.__getCommitForTag(tagName)
                tags.append((tagName, commitId))

        return tags

    def __getCommitForTag(self, tag):
        """
        Private method to get the commit id for a tag.

        @param tag tag name
        @type str
        @return commit id shortened to 10 characters
        @rtype str
        """
        args = self.vcs.initCommand("show")
        args.append("--abbrev-commit")
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        args.append("--no-patch")
        args.append(tag)

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )

        if output:
            for line in output.splitlines():
                if line.startswith("commit "):
                    commitId = line.split()[1].strip()
                    return commitId

        return ""

    @pyqtSlot(QPoint)
    def on_logTree_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the log tree.

        @param pos position of the mouse pointer
        @type QPoint
        """
        self.__logTreeMenu.popup(self.logTree.mapToGlobal(pos))

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_logTree_currentItemChanged(self, current, previous):
        """
        Private slot called, when the current item of the log tree changes.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param previous reference to the old current item
        @type QTreeWidgetItem
        """
        self.__updateToolMenuActions()

        # Highlight the current entry using a bold font
        for col in range(self.logTree.columnCount()):
            current and current.setFont(col, self.__logTreeBoldFont)
            previous and previous.setFont(col, self.__logTreeNormalFont)

        # set the state of the up and down buttons
        self.upButton.setEnabled(
            current is not None and self.logTree.indexOfTopLevelItem(current) > 0
        )
        self.downButton.setEnabled(
            current is not None
            and len(current.data(0, self.__parentsRole)) > 0
            and (
                self.logTree.indexOfTopLevelItem(current)
                < self.logTree.topLevelItemCount() - 1
                or self.nextButton.isEnabled()
            )
        )

    @pyqtSlot()
    def on_logTree_itemSelectionChanged(self):
        """
        Private slot called, when the selection has changed.
        """
        self.__updateDetailsAndFiles()
        self.__updateSbsSelectLabel()
        self.__updateToolMenuActions()
        self.__generateDiffs()

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move the current item up one entry.
        """
        itm = self.logTree.itemAbove(self.logTree.currentItem())
        if itm:
            self.logTree.setCurrentItem(itm)

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move the current item down one entry.
        """
        itm = self.logTree.itemBelow(self.logTree.currentItem())
        if itm:
            self.logTree.setCurrentItem(itm)
        else:
            # load the next bunch and try again
            if self.nextButton.isEnabled():
                self.__addFinishCallback(self.on_downButton_clicked)
                self.on_nextButton_clicked()

    @pyqtSlot()
    def on_nextButton_clicked(self):
        """
        Private slot to handle the Next button.
        """
        if self.__skipEntries > 0 and self.nextButton.isEnabled():
            self.__getLogEntries(skip=self.__skipEntries)

    @pyqtSlot(QDate)
    def on_fromDate_dateChanged(self, date):
        """
        Private slot called, when the from date changes.

        @param date new date
        @type QDate
        """
        if self.__actionMode() == "filter":
            self.__filterLogs()

    @pyqtSlot(QDate)
    def on_toDate_dateChanged(self, date):
        """
        Private slot called, when the from date changes.

        @param date new date
        @type QDate
        """
        if self.__actionMode() == "filter":
            self.__filterLogs()

    @pyqtSlot(int)
    def on_fieldCombo_activated(self, index):
        """
        Private slot called, when a new filter field is selected.

        @param index index of the selected entry
        @type int
        """
        if self.__actionMode() == "filter":
            self.__filterLogs()

    @pyqtSlot(str)
    def on_rxEdit_textChanged(self, txt):
        """
        Private slot called, when a filter expression is entered.

        @param txt filter expression
        @type str
        """
        if self.__actionMode() == "filter":
            self.__filterLogs()
        elif self.__actionMode() == "find":
            self.__findItem(self.__findBackwards, interactive=True)

    @pyqtSlot()
    def on_rxEdit_returnPressed(self):
        """
        Private slot handling a press of the Return key in the rxEdit input.
        """
        if self.__actionMode() == "find":
            self.__findItem(self.__findBackwards, interactive=True)

    @pyqtSlot(bool)
    def on_stopCheckBox_clicked(self, _checked):
        """
        Private slot called, when the stop on copy/move checkbox is clicked.

        @param _checked flag indicating the state of the check box (unused)
        @type bool
        """
        self.vcs.getPlugin().setPreferences(
            "StopLogOnCopy", self.stopCheckBox.isChecked()
        )
        self.nextButton.setEnabled(True)
        self.limitSpinBox.setEnabled(True)

    ##################################################################
    ## Tool button menu action methods below
    ##################################################################

    @pyqtSlot()
    def __cherryActTriggered(self):
        """
        Private slot to handle the Copy Commits action.
        """
        commits = {}

        for itm in self.logTree.selectedItems():
            index = self.logTree.indexOfTopLevelItem(itm)
            commits[index] = itm.text(self.CommitIdColumn)

        if commits:
            pfile = pathlib.Path(ericApp().getObject("Project").getProjectFile())
            lastModified = pfile.stat().st_mtime
            shouldReopen = (
                self.vcs.gitCherryPick(
                    self.repodir,
                    [commits[i] for i in sorted(commits, reverse=True)],
                )
                or pfile.stat().st_mtime != lastModified
            )
            if shouldReopen:
                res = EricMessageBox.yesNo(
                    None,
                    self.tr("Copy Changesets"),
                    self.tr("""The project should be reread. Do this now?"""),
                    yesDefault=True,
                )
                if res:
                    ericApp().getObject("Project").reopenProject()
                    return

            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __tagActTriggered(self):
        """
        Private slot to tag the selected commit.
        """
        if len(self.logTree.selectedItems()) == 1:
            itm = self.logTree.selectedItems()[0]
            commit = itm.text(self.CommitIdColumn)
            tag = itm.text(self.TagsColumn).strip().split(", ", 1)[0]
            res = self.vcs.vcsTag(self.repodir, revision=commit, tagName=tag)
            if res:
                self.on_refreshButton_clicked()

    @pyqtSlot()
    def __switchActTriggered(self):
        """
        Private slot to switch the working directory to the
        selected commit.
        """
        if len(self.logTree.selectedItems()) == 1:
            itm = self.logTree.selectedItems()[0]
            commit = itm.text(self.CommitIdColumn)
            branches = [
                b for b in itm.text(self.BranchColumn).split(", ") if "/" not in b
            ]
            if len(branches) == 1:
                branch = branches[0]
            elif len(branches) > 1:
                branch, ok = QInputDialog.getItem(
                    self,
                    self.tr("Switch"),
                    self.tr("Select a branch"),
                    [""] + branches,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                branch = ""
            if branch:
                rev = branch
            else:
                rev = commit
            pfile = pathlib.Path(ericApp().getObject("Project").getProjectFile())
            lastModified = pfile.stat().st_mtime
            shouldReopen = (
                self.vcs.vcsUpdate(self.repodir, revision=rev)
                or pfile.stat().st_mtime != lastModified
            )
            if shouldReopen:
                res = EricMessageBox.yesNo(
                    None,
                    self.tr("Switch"),
                    self.tr("""The project should be reread. Do this now?"""),
                    yesDefault=True,
                )
                if res:
                    ericApp().getObject("Project").reopenProject()
                    return

            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __branchActTriggered(self):
        """
        Private slot to create a new branch starting at the selected commit.
        """
        from .GitBranchDialog import GitBranchDialog

        if len(self.logTree.selectedItems()) == 1:
            itm = self.logTree.selectedItems()[0]
            commit = itm.text(self.CommitIdColumn)
            branches = [
                b for b in itm.text(self.BranchColumn).split(", ") if "/" not in b
            ]
            if len(branches) == 1:
                branch = branches[0]
            elif len(branches) > 1:
                branch, ok = QInputDialog.getItem(
                    self,
                    self.tr("Branch"),
                    self.tr("Select a default branch"),
                    [""] + branches,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                branch = ""
            res = self.vcs.gitBranch(
                self.repodir,
                revision=commit,
                branchName=branch,
                branchOp=GitBranchDialog.CreateBranch,
            )
            if res:
                self.on_refreshButton_clicked()

    @pyqtSlot()
    def __branchSwitchActTriggered(self):
        """
        Private slot to create a new branch starting at the selected commit
        and switch the work tree to it.
        """
        from .GitBranchDialog import GitBranchDialog

        if len(self.logTree.selectedItems()) == 1:
            itm = self.logTree.selectedItems()[0]
            commit = itm.text(self.CommitIdColumn)
            branches = [
                b for b in itm.text(self.BranchColumn).split(", ") if "/" not in b
            ]
            if len(branches) == 1:
                branch = branches[0]
            elif len(branches) > 1:
                branch, ok = QInputDialog.getItem(
                    self,
                    self.tr("Branch & Switch"),
                    self.tr("Select a default branch"),
                    [""] + branches,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                branch = ""
            pfile = pathlib.Path(ericApp().getObject("Project").getProjectFile())
            lastModified = pfile.stat().st_mtime
            res, shouldReopen = self.vcs.gitBranch(
                self.repodir,
                revision=commit,
                branchName=branch,
                branchOp=GitBranchDialog.CreateSwitchBranch,
            )
            shouldReopen |= pfile.stat().st_mtime != lastModified
            if res:
                if shouldReopen:
                    res = EricMessageBox.yesNo(
                        None,
                        self.tr("Switch"),
                        self.tr("""The project should be reread. Do this now?"""),
                        yesDefault=True,
                    )
                    if res:
                        ericApp().getObject("Project").reopenProject()
                        return

                self.on_refreshButton_clicked()

    @pyqtSlot()
    def __shortlogActTriggered(self):
        """
        Private slot to show a short log suitable for release announcements.
        """
        if len(self.logTree.selectedItems()) == 1:
            itm = self.logTree.selectedItems()[0]
            commit = itm.text(self.CommitIdColumn)
            branch = itm.text(self.BranchColumn).split(", ", 1)[0]
            branches = [
                b for b in itm.text(self.BranchColumn).split(", ") if "/" not in b
            ]
            if len(branches) == 1:
                branch = branches[0]
            elif len(branches) > 1:
                branch, ok = QInputDialog.getItem(
                    self,
                    self.tr("Show Short Log"),
                    self.tr("Select a branch"),
                    [""] + branches,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                branch = ""
            if branch:
                rev = branch
            else:
                rev = commit
            self.vcs.gitShortlog(self.repodir, commit=rev)

    @pyqtSlot()
    def __describeActTriggered(self):
        """
        Private slot to show the most recent tag reachable from a commit.
        """
        commits = []

        for itm in self.logTree.selectedItems():
            commits.append(itm.text(self.CommitIdColumn))

        if commits:
            self.vcs.gitDescribe(self.repodir, commits)

    ##################################################################
    ## Log context menu action methods below
    ##################################################################

    @pyqtSlot(bool)
    def __showCommitterColumns(self, on):
        """
        Private slot to show/hide the committer columns.

        @param on flag indicating the selection state
        @type bool
        """
        self.logTree.setColumnHidden(self.CommitterColumn, not on)
        self.logTree.setColumnHidden(self.CommitDateColumn, not on)
        self.vcs.getPlugin().setPreferences("ShowCommitterColumns", on)
        self.__resizeColumnsLog()

    @pyqtSlot(bool)
    def __showAuthorColumns(self, on):
        """
        Private slot to show/hide the committer columns.

        @param on flag indicating the selection state
        @type bool
        """
        self.logTree.setColumnHidden(self.AuthorColumn, not on)
        self.logTree.setColumnHidden(self.DateColumn, not on)
        self.vcs.getPlugin().setPreferences("ShowAuthorColumns", on)
        self.__resizeColumnsLog()

    @pyqtSlot(bool)
    def __showCommitIdColumn(self, on):
        """
        Private slot to show/hide the commit ID column.

        @param on flag indicating the selection state
        @type bool
        """
        self.logTree.setColumnHidden(self.CommitIdColumn, not on)
        self.vcs.getPlugin().setPreferences("ShowCommitIdColumn", on)
        self.__resizeColumnsLog()

    @pyqtSlot(bool)
    def __showBranchesColumn(self, on):
        """
        Private slot to show/hide the branches column.

        @param on flag indicating the selection state
        @type bool
        """
        self.logTree.setColumnHidden(self.BranchColumn, not on)
        self.vcs.getPlugin().setPreferences("ShowBranchesColumn", on)
        self.__resizeColumnsLog()

    @pyqtSlot(bool)
    def __showTagsColumn(self, on):
        """
        Private slot to show/hide the tags column.

        @param on flag indicating the selection state
        @type bool
        """
        self.logTree.setColumnHidden(self.TagsColumn, not on)
        self.vcs.getPlugin().setPreferences("ShowTagsColumn", on)
        self.__resizeColumnsLog()

    ##################################################################
    ## Search and filter methods below
    ##################################################################

    def __actionMode(self):
        """
        Private method to get the selected action mode.

        @return selected action mode (one of 'filter' or 'find')
        @rtype str
        """
        return self.modeComboBox.itemData(self.modeComboBox.currentIndex())

    @pyqtSlot(int)
    def on_modeComboBox_currentIndexChanged(self, index):
        """
        Private slot to react on mode changes.

        @param index index of the selected entry
        @type int
        """
        mode = self.modeComboBox.itemData(index)
        findMode = mode == "find"
        filterMode = mode == "filter"

        self.fromDate.setEnabled(filterMode)
        self.toDate.setEnabled(filterMode)
        self.findPrevButton.setVisible(findMode)
        self.findNextButton.setVisible(findMode)

        if findMode:
            for topIndex in range(self.logTree.topLevelItemCount()):
                self.logTree.topLevelItem(topIndex).setHidden(False)
            self.logTree.header().setSectionHidden(self.IconColumn, False)
        elif filterMode:
            self.__filterLogs()

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous item matching the entered criteria.
        """
        self.__findItem(True)

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next item matching the entered criteria.
        """
        self.__findItem(False)

    def __findItem(self, backwards=False, interactive=False):
        """
        Private slot to find an item matching the entered criteria.

        @param backwards flag indicating to search backwards
        @type bool
        @param interactive flag indicating an interactive search
        @type bool
        """
        self.__findBackwards = backwards

        fieldIndex, searchRx, indexIsRole = self.__prepareFieldSearch()
        currentIndex = self.logTree.indexOfTopLevelItem(self.logTree.currentItem())
        if backwards:
            if interactive:
                indexes = range(currentIndex, -1, -1)
            else:
                indexes = range(currentIndex - 1, -1, -1)
        else:
            if interactive:
                indexes = range(currentIndex, self.logTree.topLevelItemCount())
            else:
                indexes = range(currentIndex + 1, self.logTree.topLevelItemCount())

        for index in indexes:
            topItem = self.logTree.topLevelItem(index)
            if indexIsRole:
                if fieldIndex == self.__changesRole:
                    changes = topItem.data(0, self.__changesRole)
                    txt = "\n".join(
                        [c["path"] for c in changes] + [c["copyfrom"] for c in changes]
                    )
                else:
                    # Filter based on complete subject text
                    txt = topItem.data(0, self.__subjectRole)
            else:
                txt = topItem.text(fieldIndex)
            if searchRx.search(txt) is not None:
                self.logTree.setCurrentItem(self.logTree.topLevelItem(index))
                break
        else:
            EricMessageBox.information(
                self,
                self.tr("Find Commit"),
                self.tr("""'{0}' was not found.""").format(self.rxEdit.text()),
            )

    ##################################################################
    ## Commit navigation methods below
    ##################################################################

    def __commitIdClicked(self, url):
        """
        Private slot to handle the anchorClicked signal of the changeset
        details pane.

        @param url URL that was clicked
        @type QUrl
        """
        if url.scheme() == "rev":
            # a commit ID was clicked, show the respective item
            commitId = url.path()
            items = self.logTree.findItems(
                commitId, Qt.MatchFlag.MatchStartsWith, self.CommitIdColumn
            )
            if items:
                itm = items[0]
                if itm.isHidden():
                    itm.setHidden(False)
                self.logTree.setCurrentItem(itm)
            else:
                # load the next batch and try again
                if self.nextButton.isEnabled():
                    self.__addFinishCallback(lambda: self.__commitIdClicked(url))
                    self.on_nextButton_clicked()

    ###########################################################################
    ## Diff handling methods below
    ###########################################################################

    def __generateDiffs(self, parent=1):
        """
        Private slot to generate diff outputs for the selected item.

        @param parent number of parent to diff against
        @type int
        """
        self.diffHighlighter.regenerateRules(
            {
                "text": Preferences.getDiffColour("TextColor"),
                "added": Preferences.getDiffColour("AddedColor"),
                "removed": Preferences.getDiffColour("RemovedColor"),
                "replaced": Preferences.getDiffColour("ReplacedColor"),
                "context": Preferences.getDiffColour("ContextColor"),
                "header": Preferences.getDiffColour("HeaderColor"),
                "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
            },
            Preferences.getEditorOtherFonts("MonospacedFont"),
        )

        self.diffEdit.clear()
        self.diffLabel.setText(self.tr("Differences"))
        self.diffSelectLabel.clear()

        selectedItems = self.logTree.selectedItems()
        if len(selectedItems) == 1:
            currentItem = selectedItems[0]
            commit2 = currentItem.text(self.CommitIdColumn)
            parents = currentItem.data(0, self.__parentsRole)
            if len(parents) >= parent:
                self.diffLabel.setText(
                    self.tr("Differences to Parent {0}").format(parent)
                )
                commit1 = parents[parent - 1]

                self.__diffGenerator.start(self.__filename, [commit1, commit2])

            if len(parents) > 1:
                parentLinks = []
                for index in range(1, len(parents) + 1):
                    if parent == index:
                        parentLinks.append("&nbsp;{0}&nbsp;".format(index))
                    else:
                        parentLinks.append(
                            '<a href="diff:{0}">&nbsp;{0}&nbsp;</a>'.format(index)
                        )
                    self.diffSelectLabel.setText(
                        self.tr("Diff to Parent {0}").format(" ".join(parentLinks))
                    )
        elif len(selectedItems) == 2:
            commit2 = selectedItems[0].text(self.CommitIdColumn)
            commit1 = selectedItems[1].text(self.CommitIdColumn)
            index2 = self.logTree.indexOfTopLevelItem(selectedItems[0])
            index1 = self.logTree.indexOfTopLevelItem(selectedItems[1])

            if index2 < index1:
                # swap to always compare old to new
                commit1, commit2 = commit2, commit1

            self.__diffGenerator.start(self.__filename, [commit1, commit2])

    def __generatorFinished(self):
        """
        Private slot connected to the finished signal of the diff generator.
        """
        diff, _, errors, fileSeparators = self.__diffGenerator.getResult()

        if diff:
            self.diffEdit.setPlainText("".join(diff))
        elif errors:
            self.diffEdit.setPlainText("".join(errors))
        else:
            self.diffEdit.setPlainText(self.tr("There is no difference."))

        self.saveLabel.setVisible(bool(diff))

        fileSeparators = self.__mergeFileSeparators(fileSeparators)
        if self.__diffUpdatesFiles:
            for oldFileName, newFileName, lineNumber, _ in fileSeparators:
                if oldFileName == newFileName:
                    item = QTreeWidgetItem(self.filesTree, ["", oldFileName])
                elif oldFileName == "/dev/null":
                    item = QTreeWidgetItem(self.filesTree, ["", newFileName])
                else:
                    item = QTreeWidgetItem(
                        self.filesTree, ["", newFileName, "", "", oldFileName]
                    )
                item.setData(0, self.__diffFileLineRole, lineNumber)
            self.__resizeColumnsFiles()
            self.__resortFiles()
        else:
            for oldFileName, newFileName, lineNumber, _ in fileSeparators:
                for fileName in (oldFileName, newFileName):
                    if fileName != "/dev/null":
                        items = self.filesTree.findItems(
                            fileName, Qt.MatchFlag.MatchExactly, 1
                        )
                        for item in items:
                            item.setData(0, self.__diffFileLineRole, lineNumber)

        tc = self.diffEdit.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Start)
        self.diffEdit.setTextCursor(tc)
        self.diffEdit.ensureCursorVisible()

    def __mergeFileSeparators(self, fileSeparators):
        """
        Private method to merge the file separator entries.

        @param fileSeparators list of file separator entries to be merged
        @type list of str
        @return merged list of file separator entries
        @rtype list of str
        """
        separators = {}
        for oldFile, newFile, pos1, pos2 in sorted(fileSeparators):
            if (oldFile, newFile) not in separators:
                separators[(oldFile, newFile)] = [oldFile, newFile, pos1, pos2]
            else:
                if pos1 != -2:
                    separators[(oldFile, newFile)][2] = pos1
                if pos2 != -2:
                    separators[(oldFile, newFile)][3] = pos2
        return list(separators.values())

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_filesTree_currentItemChanged(self, current, previous):
        """
        Private slot called, when the current item of the files tree changes.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param previous reference to the old current item
        @type QTreeWidgetItem
        """
        if current:
            para = current.data(0, self.__diffFileLineRole)
            if para is not None:
                if para == 0:
                    tc = self.diffEdit.textCursor()
                    tc.movePosition(QTextCursor.MoveOperation.Start)
                    self.diffEdit.setTextCursor(tc)
                    self.diffEdit.ensureCursorVisible()
                elif para == -1:
                    tc = self.diffEdit.textCursor()
                    tc.movePosition(QTextCursor.MoveOperation.End)
                    self.diffEdit.setTextCursor(tc)
                    self.diffEdit.ensureCursorVisible()
                else:
                    # step 1: move cursor to end
                    tc = self.diffEdit.textCursor()
                    tc.movePosition(QTextCursor.MoveOperation.End)
                    self.diffEdit.setTextCursor(tc)
                    self.diffEdit.ensureCursorVisible()

                    # step 2: move cursor to desired line
                    tc = self.diffEdit.textCursor()
                    delta = tc.blockNumber() - para
                    tc.movePosition(
                        QTextCursor.MoveOperation.PreviousBlock,
                        QTextCursor.MoveMode.MoveAnchor,
                        delta,
                    )
                    self.diffEdit.setTextCursor(tc)
                    self.diffEdit.ensureCursorVisible()

    @pyqtSlot(str)
    def on_diffSelectLabel_linkActivated(self, link):
        """
        Private slot to handle the selection of a diff target.

        @param link activated link
        @type str
        """
        if ":" in link:
            scheme, parent = link.split(":", 1)
            if scheme == "diff":
                with contextlib.suppress(ValueError):
                    parent = int(parent)
                    self.__generateDiffs(parent)

    @pyqtSlot(str)
    def on_saveLabel_linkActivated(self, link):
        """
        Private slot to handle the selection of the save link.

        @param link activated link
        @type str
        """
        if ":" not in link:
            return

        scheme, rest = link.split(":", 1)
        if scheme != "save" or rest != "me":
            return

        if self.projectMode:
            fname = self.vcs.splitPath(self.__filename)[0]
            fname += "/{0}.diff".format(os.path.split(fname)[-1])
        else:
            dname, fname = self.vcs.splitPath(self.__filename)
            if fname != ".":
                fname = "{0}.diff".format(self.__filename)
            else:
                fname = dname

        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save Diff"),
            fname,
            self.tr("Patch Files (*.diff)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fname:
            return  # user aborted

        fpath = pathlib.Path(fname)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fpath),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        eol = ericApp().getObject("Project").getEolString()
        try:
            with fpath.open("w", encoding="utf-8", newline="") as f:
                f.write(eol.join(self.diffEdit.toPlainText().splitlines()))
                f.write(eol)
        except OSError as why:
            EricMessageBox.critical(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> could not be saved."
                    "<br>Reason: {1}</p>"
                ).format(fpath, str(why)),
            )

    @pyqtSlot(str)
    def on_sbsSelectLabel_linkActivated(self, link):
        """
        Private slot to handle selection of a side-by-side link.

        @param link text of the selected link
        @type str
        """
        if ":" in link:
            scheme, path = link.split(":", 1)
            if scheme == "sbsdiff" and "_" in path:
                commit1, commit2 = path.split("_", 1)
                self.vcs.vcsSbsDiff(self.__filename, revisions=(commit1, commit2))
