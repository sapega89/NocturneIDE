# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the list of messages to be ignored.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_EricErrorMessageFilterDialog import Ui_EricErrorMessageFilterDialog


class EricErrorMessageFilterDialog(QDialog, Ui_EricErrorMessageFilterDialog):
    """
    Class implementing a dialog to manage the list of messages to be ignored.
    """

    def __init__(self, messageFilters, parent=None):
        """
        Constructor

        @param messageFilters list of message filters to be edited
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filtersEditWidget.setList(messageFilters)
        self.filtersEditWidget.setListWhatsThis(
            self.tr(
                "<b>Error Message Filters</b>"
                "<p>This list shows the configured message filters used to"
                " suppress error messages from within Qt.</p>"
                "<p>A default list of message filters is added to this"
                " user list.</p>"
            )
        )

    def getFilters(self):
        """
        Public method to get the list of message filters.

        @return error message filters
        @rtype list of str
        """
        return self.filtersEditWidget.getList()
