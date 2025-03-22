# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing statistical data for the last code
style checker run.
"""

import textwrap

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from . import CodeStyleCheckerUtilities
from .translations import getTranslatedMessage
from .Ui_CodeStyleStatisticsDialog import Ui_CodeStyleStatisticsDialog


class CodeStyleStatisticsDialog(QDialog, Ui_CodeStyleStatisticsDialog):
    """
    Class implementing a dialog showing statistical data for the last
    code style checker run.
    """

    def __init__(self, statisticData, parent=None):
        """
        Constructor

        @param statisticData dictionary with the statistical data
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        stats = statisticData.copy()
        filesCount = stats["_FilesCount"]
        filesIssues = stats["_FilesIssues"]
        fixesCount = stats["_IssuesFixed"]
        securityOk = stats["_SecurityOK"]
        del stats["_FilesCount"]
        del stats["_FilesIssues"]
        del stats["_IssuesFixed"]
        del stats["_SecurityOK"]

        totalIssues = 0
        ignoresCount = 0

        textWrapper = textwrap.TextWrapper(width=80)

        for msgCode in sorted(stats):
            message = getTranslatedMessage(msgCode, [], example=True)
            if message is None:
                continue

            self.__createItem(
                stats[msgCode], msgCode, "\n".join(textWrapper.wrap(message))
            )
            totalIssues += stats[msgCode]["total"]
            ignoresCount += stats[msgCode]["ignored"]

        self.totalIssues.setText(self.tr("%n issue(s) found", "", totalIssues))
        self.ignoredIssues.setText(self.tr("%n issue(s) ignored", "", ignoresCount))
        self.fixedIssues.setText(self.tr("%n issue(s) fixed", "", fixesCount))
        self.filesChecked.setText(self.tr("%n file(s) checked", "", filesCount))
        self.filesIssues.setText(
            self.tr("%n file(s) with issues found", "", filesIssues)
        )
        self.securityOk.setText(
            self.tr("%n security issue(s) acknowledged", "", securityOk)
        )

        self.statisticsList.resizeColumnToContents(0)
        self.statisticsList.resizeColumnToContents(1)
        self.statisticsList.resizeColumnToContents(2)

    def __createItem(self, counts, msgCode, message):
        """
        Private method to create an entry in the result list.

        @param counts dictionary containing the total and ignored occurrences
            of the issue
        @type dict
        @param msgCode code of a code style issue message
        @type str
        @param message code style issue message to be shown
        @type str
        """
        itm = QTreeWidgetItem(
            self.statisticsList,
            [
                msgCode,
                "{0:6d}".format(counts["total"] - counts["ignored"]),
                "{0:6d}".format(counts["ignored"]),
                message,
            ],
        )
        CodeStyleCheckerUtilities.setItemIcon(itm, 0, msgCode)

        itm.setTextAlignment(
            0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        itm.setTextAlignment(
            1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        itm.setTextAlignment(
            2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
