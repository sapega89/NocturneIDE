# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to manage the QtHelp documentation settings.
"""

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QWidget

from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .QtHelpDocumentationSettings import QtHelpDocumentationSettings
from .Ui_QtHelpDocumentationSettingsWidget import Ui_QtHelpDocumentationSettingsWidget


class QtHelpDocumentationSettingsWidget(QWidget, Ui_QtHelpDocumentationSettingsWidget):
    """
    Class implementing a widget to manage the QtHelp documentation settings.

    @signal documentationSettingsChanged(settings) emitted to signal a change
        of the documentation configuration
    """

    documentationSettingsChanged = pyqtSignal(QtHelpDocumentationSettings)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__settings = None

        try:
            self.__pluginHelpDocuments = (
                ericApp().getObject("PluginManager").getPluginQtHelpFiles()
            )
        except KeyError:
            from eric7.PluginManager.PluginManager import (  # __IGNORE_WARNING_I101__
                PluginManager,
            )

            pluginManager = PluginManager(self, doLoadPlugins=False)
            pluginManager.loadDocumentationSetPlugins()
            pluginManager.activatePlugins()
            self.__pluginHelpDocuments = pluginManager.getPluginQtHelpFiles()
        self.addPluginButton.setEnabled(bool(self.__pluginHelpDocuments))

    @pyqtSlot()
    def on_removeDocumentsButton_clicked(self):
        """
        Private slot to remove a document from the help database.
        """
        selectedItems = self.documentsList.selectedItems()[:]
        if not selectedItems:
            return

        for itm in selectedItems:
            namespace = itm.text()
            self.documentsList.takeItem(self.documentsList.row(itm))
            del itm

            self.__settings.removeDocumentation(namespace)

        self.documentationSettingsChanged.emit(self.__settings)

    @pyqtSlot()
    def on_addDocumentsButton_clicked(self):
        """
        Private slot to add QtHelp documents to the help database.
        """
        filenames = EricFileDialog.getOpenFileNames(
            self,
            self.tr("Add Documentation"),
            "",
            self.tr("Qt Compressed Help Files (*.qch)"),
        )
        if not filenames:
            return

        self.__registerDocumentation(filenames)

    @pyqtSlot()
    def on_addPluginButton_clicked(self):
        """
        Private slot to add QtHelp documents provided by plug-ins to
        the help database.
        """
        from .QtHelpDocumentationSelectionDialog import (
            QtHelpDocumentationSelectionDialog,
        )

        dlg = QtHelpDocumentationSelectionDialog(
            self.__pluginHelpDocuments,
            QtHelpDocumentationSelectionDialog.AddMode,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            documents = dlg.getData()
            if documents:
                self.__registerDocumentation(documents)

    def __registerDocumentation(self, filenames):
        """
        Private method to register a given list of documentations.

        @param filenames list of documentation files to be registered
        @type list of str
        """
        added = False

        for filename in filenames:
            if not self.__settings.addDocumentation(filename):
                EricMessageBox.warning(
                    self,
                    self.tr("Add Documentation"),
                    self.tr("""The file <b>{0}</b> could not be added.""").format(
                        filename
                    ),
                )
                continue

            if not added:
                added = True
                self.documentsList.clearSelection()

            namespace = self.__settings.namespace(filename)
            itm = QListWidgetItem(namespace)
            self.documentsList.addItem(itm)

            itm.setSelected(True)
        self.__applyDocumentsListFilter()

        if added:
            self.documentationSettingsChanged.emit(self.__settings)

    @pyqtSlot()
    def on_managePluginButton_clicked(self):
        """
        Private slot to manage the QtHelp documents provided by plug-ins.
        """
        from .QtHelpDocumentationSelectionDialog import (
            QtHelpDocumentationSelectionDialog,
        )

        dlg = QtHelpDocumentationSelectionDialog(
            self.__pluginHelpDocuments,
            QtHelpDocumentationSelectionDialog.ManageMode,
            parent=self,
        )
        dlg.exec()

    @pyqtSlot()
    def on_documentsList_itemSelectionChanged(self):
        """
        Private slot handling a change of the documents selection.
        """
        self.removeDocumentsButton.setEnabled(
            len(self.documentsList.selectedItems()) != 0
        )

    @pyqtSlot(str)
    def on_filterEdit_textChanged(self, _txt):
        """
        Private slot to react on changes of the document filter text.

        @param _txt current entry of the filter (unused)
        @type str
        """
        self.__applyDocumentsListFilter()

    @pyqtSlot()
    def __applyDocumentsListFilter(self):
        """
        Private slot to apply the current documents filter.
        """
        filterStr = self.filterEdit.text()
        for row in range(self.documentsList.count()):
            itm = self.documentsList.item(row)
            matches = filterStr == "" or filterStr in itm.text()

            if not matches:
                itm.setSelected(False)
            itm.setHidden(not matches)

    def setDocumentationSettings(self, settings):
        """
        Public method to set the reference to the QtHelp documentation
        configuration object.

        @param settings reference to the created QtHelpDocumentationSettings
            object
        @type QtHelpDocumentationSettings
        """
        self.__settings = settings

        self.documentsList.clear()

        for namespace in self.__settings.namespaces():
            itm = QListWidgetItem(namespace)
            self.documentsList.addItem(itm)
        self.__applyDocumentsListFilter()

        self.removeDocumentsButton.setEnabled(False)

    def documentationSettings(self):
        """
        Public method to get the reference to the QtHelp documentation
        configuration object.

        @return reference to the created QtHelpDocumentationSettings object
        @rtype QtHelpDocumentationSettings
        """
        return self.__settings
