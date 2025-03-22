# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select a help topic to display.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtHelp import QHelpLink
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from .Ui_HelpTopicDialog import Ui_HelpTopicDialog


class HelpTopicDialog(QDialog, Ui_HelpTopicDialog):
    """
    Class implementing a dialog to select a help topic to display.
    """

    def __init__(self, parent, helpKeyword, documents):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param helpKeyword keyword for the link set
        @type str
        @param documents list of help document link data structures
        @type list of QHelpLink
        """
        super().__init__(parent)
        self.setupUi(self)

        self.label.setText(
            self.tr("Choose a &topic for <b>{0}</b>:").format(helpKeyword)
        )

        for document in documents:
            itm = QListWidgetItem(document.title, self.topicsList)
            itm.setData(Qt.ItemDataRole.UserRole, document.url)
        if self.topicsList.count() > 0:
            self.topicsList.setCurrentRow(0)
        self.topicsList.setFocus()

        self.topicsList.itemActivated.connect(self.accept)

    def document(self):
        """
        Public method to retrieve the selected help topic.

        @return help document link for the selected help topic
        @rtype QHelpLink
        """
        document = QHelpLink()

        itm = self.topicsList.currentItem()
        if itm is not None:
            document.title = itm.text()
            document.url = itm.data(Qt.ItemDataRole.UserRole)

        return document
