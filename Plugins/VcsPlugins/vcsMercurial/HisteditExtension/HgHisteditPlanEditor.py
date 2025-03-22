# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the history modification plan.
"""

from PyQt6.QtCore import QCoreApplication, pyqtSlot
from PyQt6.QtWidgets import QComboBox, QDialog, QTreeWidgetItem
from Ui_HgHisteditPlanEditor import Ui_HgHisteditPlanEditor

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox


class HgHisteditPlanActionComboBox(QComboBox):
    """
    Class implementing a combo box to select the action in the plan tree.
    """

    def __init__(self, item, column):
        """
        Constructor

        @param item reference to the item
        @type QTreeWidgetItem
        @param column column number inside the tree widget item
        @type int
        """
        super().__init__()

        self.__item = item
        self.__column = column

        self.addItems(["pick", "drop", "mess", "fold", "roll", "edit"])
        txt = self.__item.text(self.__column)
        index = self.findText(txt)
        if index > -1:
            self.setCurrentIndex(index)

        self.currentIndexChanged.connect(self.__changeItem)

    @pyqtSlot(int)
    def __changeItem(self, index):
        """
        Private slot to handle the selection of a plan action.

        This method sets the text of the associated item for the specified
        cell in order to be able to retrieve it with a call of the text()
        method of the item.

        @param index index of the selected action
        @type int
        """
        self.__item.setText(self.__column, self.currentText())
        self.__item.treeWidget().setCurrentItem(self.__item)

    def showPopup(self):
        """
        Public method to show the list of items of the combo box.

        This is reimplemented in order to set the associated item as the
        current item of the tree widget.
        """
        self.__item.treeWidget().setCurrentItem(self.__item)
        super().showPopup()


class HgHisteditPlanEditor(QDialog, Ui_HgHisteditPlanEditor):
    """
    Class implementing a dialog to edit the history modification plan.
    """

    def __init__(self, fileName, parent=None):
        """
        Constructor

        @param fileName name of the file containing the history edit plan
            to be edited
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.downButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        self.planTreeWidget.headerItem().setText(self.planTreeWidget.columnCount(), "")

        self.__fileName = fileName
        self.__readFile()

        self.__updateButtons()

    def __readFile(self):
        """
        Private method to read the file containing the edit plan and
        populate the dialog.
        """
        try:
            with open(self.__fileName, "r") as f:
                txt = f.read()
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Edit Plan"),
                self.tr(
                    """<p>The file <b>{0}</b> could not be read.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(self.__fileName, str(err)),
            )
            self.on_buttonBox_rejected()
            return

        infoLines = []
        for line in txt.splitlines():
            if line.startswith("#"):
                infoLines.append(line[1:].lstrip())
            else:
                self.__createPlanItem(line)
        self.infoEdit.setPlainText("\n".join(infoLines))

        self.__resizeSections()

    def __addActionCombo(self, item):
        """
        Private method to add an edit action combo to an item.

        @param item reference to the tree widget item
        @type QTreeWidgetItem
        """
        actionCombo = HgHisteditPlanActionComboBox(item, 0)
        self.planTreeWidget.setItemWidget(item, 0, actionCombo)
        item.setSizeHint(0, actionCombo.sizeHint())

    def __createPlanItem(self, text):
        """
        Private method to create an edit plan tree item.

        @param text line of text to be parsed
        @type str
        """
        if not text.lstrip():
            return

        parts = text.split(" ", 3)
        action = parts[0]
        try:
            rev = int(parts[2])
            summary = parts[3] if len(parts) > 3 else ""
        except ValueError:
            rev = -1
            summary = " ".join(parts[2:])
        revision = "{0:>7}:{1}".format(rev, parts[1]) if rev > -1 else parts[1]

        itm = QTreeWidgetItem(
            self.planTreeWidget,
            [
                action,
                revision,
                summary,
            ],
        )
        self.__addActionCombo(itm)

    def __resizeSections(self):
        """
        Private method to resize the tree widget sections.
        """
        for column in range(self.planTreeWidget.columnCount()):
            self.planTreeWidget.resizeColumnToContents(column)
        self.planTreeWidget.header().setStretchLastSection(True)

    def __updateButtons(self):
        """
        Private method to set the enabled state of the up and down buttons.
        """
        if self.planTreeWidget.currentItem() is None:
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)
        else:
            row = self.planTreeWidget.indexOfTopLevelItem(
                self.planTreeWidget.currentItem()
            )
            self.upButton.setEnabled(row > 0)
            self.downButton.setEnabled(
                row < self.planTreeWidget.topLevelItemCount() - 1
            )

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_planTreeWidget_currentItemChanged(self, _current, _previous):
        """
        Private slot handling the change of the current edit plan item.

        @param _current reference to the current edit plan item (unused)
        @type QTreeWidgetItem
        @param _previous reference to the previous current edit plan item (unused)
        @type QTreeWidgetItem
        """
        self.__updateButtons()

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move the current entry up one line.
        """
        row = self.planTreeWidget.indexOfTopLevelItem(self.planTreeWidget.currentItem())
        if row > 0:
            targetRow = row - 1
            itm = self.planTreeWidget.takeTopLevelItem(row)
            self.planTreeWidget.insertTopLevelItem(targetRow, itm)
            self.__addActionCombo(itm)
            self.planTreeWidget.setCurrentItem(itm)

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move the current entry down one line.
        """
        row = self.planTreeWidget.indexOfTopLevelItem(self.planTreeWidget.currentItem())
        if row < self.planTreeWidget.topLevelItemCount() - 1:
            targetRow = row + 1
            itm = self.planTreeWidget.takeTopLevelItem(row)
            self.planTreeWidget.insertTopLevelItem(targetRow, itm)
            self.__addActionCombo(itm)
            self.planTreeWidget.setCurrentItem(itm)

    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Private slot called by the buttonBox accepted signal.
        """
        text = self.__assembleEditPlan()
        try:
            with open(self.__fileName, "w") as f:
                f.write(text)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Edit Plan"),
                self.tr(
                    """<p>The file <b>{0}</b> could not be read.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(self.__fileName, str(err)),
            )
            self.on_buttonBox_rejected()
            return

        self.close()
        QCoreApplication.exit(0)

    @pyqtSlot()
    def on_buttonBox_rejected(self):
        """
        Private slot called by the buttonBox rejected signal.
        """
        self.close()
        QCoreApplication.exit(1)

    def __assembleEditPlan(self):
        """
        Private method to assemble the edit plan into text suitable for the
        histedit file.

        @return assembled edit plan text
        @rtype str
        """
        lines = []
        for row in range(self.planTreeWidget.topLevelItemCount()):
            itm = self.planTreeWidget.topLevelItem(row)
            if ":" in itm.text(1):
                rev, changeset = itm.text(1).split(":", 1)
                rev = "{0} {1}".format(changeset.strip(), rev.strip())
            else:
                rev = itm.text(1).strip()

            lines.append("{0} {1} {2}".format(itm.text(0).strip(), rev, itm.text(2)))

        return "\n".join(lines)
