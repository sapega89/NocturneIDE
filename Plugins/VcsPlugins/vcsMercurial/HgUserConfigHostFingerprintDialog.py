# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit a host fingerprint.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgUserConfigHostFingerprintDialog import Ui_HgUserConfigHostFingerprintDialog


class HgUserConfigHostFingerprintDialog(QDialog, Ui_HgUserConfigHostFingerprintDialog):
    """
    Class implementing a dialog to edit a host fingerprint.
    """

    supportedHashes = ("sha1", "sha256", "sha512")
    fingerprintLength = {
        "sha1": 40,
        "sha256": 64,
        "sha512": 128,
    }

    def __init__(self, parent=None, host="", fingerprint="", version=(0, 0, 0)):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param host host name
        @type str
        @param fingerprint fingerprint for the host
        @type str
        @param version Mercurial version info
        @type tuple of three integers
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__version = version

        self.hashComboBox.addItem("")
        self.hashComboBox.addItems(HgUserConfigHostFingerprintDialog.supportedHashes)
        if fingerprint and fingerprint.startswith("sha"):
            hashType, fingerprint = fingerprint.split(":", 1)
        else:
            hashType = ""

        index = self.hashComboBox.findText(hashType)
        self.hashComboBox.setCurrentIndex(index)
        self.hostEdit.setText(host)
        self.fingerprintEdit.setText(fingerprint)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.__updateOkButton()

    def __updateOkButton(self):
        """
        Private method to update the status of the Ok button.
        """
        enabled = bool(self.hostEdit.text()) and bool(self.fingerprintEdit.text())

        hashType = self.hashComboBox.currentText()
        enabled &= bool(hashType)
        if hashType:
            enabled &= (
                len(self.fingerprintEdit.text().replace(":", ""))
                == HgUserConfigHostFingerprintDialog.fingerprintLength[hashType]
            )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(str)
    def on_hostEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the host edit.

        @param txt current text
        @type str
        """
        self.__updateOkButton()

    @pyqtSlot(int)
    def on_hashComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle changes of the hash combo.

        @param index current index
        @type int
        """
        self.__updateOkButton()

    @pyqtSlot(str)
    def on_fingerprintEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the fingerprint edit.

        @param txt current text
        @type str
        """
        if txt != txt.strip():
            # get rid of whitespace
            txt = txt.strip()
            self.fingerprintEdit.setText(txt)

        if txt.startswith(
            tuple(h + ":" for h in HgUserConfigHostFingerprintDialog.supportedHashes)
        ):
            parts = txt.split(":", 1)
            if len(parts) == 2:
                self.fingerprintEdit.setText(parts[1])
                hashIndex = self.hashComboBox.findText(parts[0].strip())
                if hashIndex > -1:
                    self.hashComboBox.setCurrentIndex(hashIndex)

        self.__updateOkButton()

    def getData(self):
        """
        Public method to retrieve the data.

        @return tuple containig the host name and the fingerprint
        @rtype tuple of two str
        """
        fingerprint = "{0}:{1}".format(
            self.hashComboBox.currentText(), self.fingerprintEdit.text().strip()
        )

        return self.hostEdit.text().strip(), fingerprint
