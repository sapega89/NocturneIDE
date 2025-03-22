# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget and a dialog to show package details.
"""

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from eric7.Globals import dataString

from .Ui_CondaPackageDetailsWidget import Ui_CondaPackageDetailsWidget


class CondaPackageDetailsWidget(QWidget, Ui_CondaPackageDetailsWidget):
    """
    Class implementing a widget to show package details.
    """

    def __init__(self, details, parent=None):
        """
        Constructor

        @param details dictionary containing the package details
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.headerLabel.setText(
            self.tr("<b>{0} / {1} / {2}</b>").format(
                details["name"], details["version"], details["build"]
            )
        )
        if "fn" in details:
            self.filenameLabel.setText(details["fn"])
        if "size" in details:
            self.sizeLabel.setText(dataString(details["size"]))
        if "channel" in details:
            self.channelLabel.setText(details["channel"])
        if "url" in details:
            self.urlLabel.setText(details["url"])
        if "md5" in details:
            self.md5Label.setText(details["md5"])
        if "license" in details:
            self.licenseLabel.setText(details["license"])
        if "subdir" in details:
            self.platformLabel.setText(details["subdir"])
        elif "platform" in details:
            self.platformLabel.setText(details["platform"])
        else:
            self.platformLabel.setText(self.tr("unknown"))
        if "depends" in details:
            self.dependenciesEdit.setPlainText("\n".join(details["depends"]))

        if "timestamp" in details:
            dt = QDateTime.fromMSecsSinceEpoch(details["timestamp"], Qt.TimeSpec.UTC)
            self.timestampLabel.setText(dt.toString("yyyy-MM-dd hh:mm:ss t"))

        self.resize(600, 450)


class CondaPackageDetailsDialog(QDialog):
    """
    Class implementing a dialog to show package details.
    """

    def __init__(self, details, parent=None):
        """
        Constructor

        @param details dictionary containing the package details
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setSizeGripEnabled(True)

        self.__layout = QVBoxLayout(self)
        self.setLayout(self.__layout)

        self.__cw = CondaPackageDetailsWidget(details, self)
        size = self.__cw.size()
        self.__layout.addWidget(self.__cw)
        self.__buttonBox = QDialogButtonBox(self)
        self.__buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)
        self.__layout.addWidget(self.__buttonBox)

        self.resize(size)
        self.setWindowTitle(self.tr("Package Details"))

        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)
