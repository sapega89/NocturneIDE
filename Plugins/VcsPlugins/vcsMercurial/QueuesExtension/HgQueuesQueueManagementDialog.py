# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog used by the queue management functions.
"""

import enum

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
)

from .Ui_HgQueuesQueueManagementDialog import Ui_HgQueuesQueueManagementDialog


class HgQueuesQueueManagementDialogMode(enum.Enum):
    """
    Class defining the supported dialog modes.
    """

    NO_INPUT = 0
    NAME_INPUT = 1
    QUEUE_INPUT = 2


class HgQueuesQueueManagementDialog(QDialog, Ui_HgQueuesQueueManagementDialog):
    """
    Class implementing a dialog used by the queue management functions.
    """

    def __init__(self, mode, title, suppressActive, vcs, parent=None):
        """
        Constructor

        @param mode mode of the dialog
        @type HgQueuesQueueManagementDialogMode
        @param title title for the dialog
        @type str
        @param suppressActive flag indicating to not show the name of the
            active queue
        @type bool
        @param vcs reference to the vcs object
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        @exception ValueError raised to indicate an invalid dialog mode
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        if not isinstance(mode, HgQueuesQueueManagementDialogMode):
            raise ValueError("illegal value for mode")

        self.__mode = mode
        self.__suppressActive = suppressActive
        self.__hgClient = vcs.getClient()
        self.vcs = vcs

        self.inputFrame.setHidden(mode != HgQueuesQueueManagementDialogMode.NAME_INPUT)
        self.selectLabel.setHidden(
            mode != HgQueuesQueueManagementDialogMode.QUEUE_INPUT
        )
        if mode != HgQueuesQueueManagementDialogMode.QUEUE_INPUT:
            self.queuesList.setSelectionMode(
                QAbstractItemView.SelectionMode.NoSelection
            )

        if mode == HgQueuesQueueManagementDialogMode.NO_INPUT:
            self.buttonBox.removeButton(
                self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            )
            self.buttonBox.removeButton(
                self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
            )
            self.refreshButton = self.buttonBox.addButton(
                self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.refreshButton.setToolTip(self.tr("Press to refresh the queues list"))
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(
                True
            )
        else:
            self.buttonBox.removeButton(
                self.buttonBox.button(QDialogButtonBox.StandardButton.Close)
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.refreshButton = None

        self.setWindowTitle(title)

        self.show()
        QCoreApplication.processEvents()

        self.refresh()

    def __getQueuesList(self):
        """
        Private method to get a list of all queues and the name of the active
        queue.

        @return tuple with a list of all queues and the name of the active queue
        @rtype tuple of (list of str, str)
        """
        queuesList = []
        activeQueue = ""

        args = self.vcs.initCommand("qqueue")
        args.append("--list")

        output = self.__hgClient.runcommand(args)[0]

        for queue in output.splitlines():
            queue = queue.strip()
            if queue.endswith(")"):
                queue = queue.rsplit(None, 1)[0]
                activeQueue = queue
            queuesList.append(queue)

        if self.__suppressActive:
            if activeQueue in queuesList:
                queuesList.remove(activeQueue)
            activeQueue = ""
        return queuesList, activeQueue

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the entered queue name.

        @param txt text of the edit
        @type str
        """
        if self.__mode == HgQueuesQueueManagementDialogMode.NAME_INPUT:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                txt != ""
            )

    @pyqtSlot()
    def on_queuesList_itemSelectionChanged(self):
        """
        Private slot to handle changes of selected queue names.
        """
        if self.__mode == HgQueuesQueueManagementDialogMode.QUEUE_INPUT:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                len(self.queuesList.selectedItems()) > 0
            )

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.refreshButton:
            self.refresh()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()

    def refresh(self):
        """
        Public slot to refresh the list of queues.
        """
        self.queuesList.clear()
        queuesList, activeQueue = self.__getQueuesList()
        for queue in sorted(queuesList):
            itm = QListWidgetItem(queue, self.queuesList)
            if queue == activeQueue:
                font = itm.font()
                font.setBold(True)
                itm.setFont(font)

    def getData(self):
        """
        Public slot to get the data.

        @return queue name
        @rtype str
        """
        name = ""
        if self.__mode == HgQueuesQueueManagementDialogMode.NAME_INPUT:
            name = self.nameEdit.text().replace(" ", "_")
        elif self.__mode == HgQueuesQueueManagementDialogMode.QUEUE_INPUT:
            selItems = self.queuesList.selectedItems()
            if selItems:
                name = selItems[0].text()
        return name
