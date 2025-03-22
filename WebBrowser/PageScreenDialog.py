# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to save a screenshot of a web page.
"""

import pathlib

from PyQt6.QtCore import QSize, Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7.EricWidgets import EricFileDialog, EricMessageBox

from .Ui_PageScreenDialog import Ui_PageScreenDialog


class PageScreenDialog(QDialog, Ui_PageScreenDialog):
    """
    Class implementing a dialog to save a screenshot of a web page.
    """

    def __init__(self, view, parent=None):
        """
        Constructor

        @param view reference to the web view containing the page to be saved
        @type WebBrowserView
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__view = view
        self.__createPixmap()
        self.pageScreenLabel.setPixmap(self.__pagePixmap)

    def __createPixmap(self):
        """
        Private slot to create a pixmap of the associated view's page.
        """
        res = self.__view.page().execJavaScript(
            "(function() {"
            "var res = {"
            "    width: 0,"
            "    height: 0,"
            "};"
            "res.width = document.body.scrollWidth;"
            "res.height = document.body.scrollHeight;"
            "return res;"
            "})()"
        )
        if res is not None:
            image = QImage(
                QSize(res["width"], self.__view.height()), QImage.Format.Format_ARGB32
            )
            painter = QPainter(image)
            self.__view.render(painter)
            painter.end()

            self.__pagePixmap = QPixmap.fromImage(image)

    def __savePageScreen(self):
        """
        Private slot to save the page screen.

        @return flag indicating success
        @rtype bool
        """
        fileName = EricFileDialog.getSaveFileName(
            self,
            self.tr("Save Page Screen"),
            self.tr("screen.png"),
            self.tr("Portable Network Graphics File (*.png)"),
            options=EricFileDialog.DontConfirmOverwrite,
        )
        if not fileName:
            return False

        if pathlib.Path(fileName).exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save Page Screen"),
                self.tr(
                    "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fileName),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return False

        res = self.__pagePixmap.save(fileName)
        if not res:
            EricMessageBox.warning(
                self,
                self.tr("Save Page Screen"),
                self.tr("Cannot write file '{0}'.").format(fileName),
            )
            return False

        return True

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot to handle clicks of the dialog buttons.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.reject()
        elif (
            button == self.buttonBox.button(QDialogButtonBox.StandardButton.Save)
            and self.__savePageScreen()
        ):
            self.accept()
