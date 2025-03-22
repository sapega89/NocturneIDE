# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a custom widget indicating the strength of a password.
"""

from PyQt6.QtWidgets import QProgressBar

from eric7.EricUtilities.EricPasswordChecker import PasswordChecker, PasswordStrength


class EricPasswordMeter(QProgressBar):
    """
    Class implementing a custom widget indicating the strength of a password.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        super().setTextVisible(False)
        super().setMaximum(100)
        self.__increment = 100 // (PasswordStrength.VeryStrong + 1)

        self.__indicatorColors = {
            PasswordStrength.VeryWeak: "#ff0000",  # red
            PasswordStrength.Weak: "#ff8800",  # orange
            PasswordStrength.Good: "#ffff00",  # yellow
            PasswordStrength.Strong: "#ccff00",  # yellow green
            PasswordStrength.VeryStrong: "#00ff00",  # green
        }
        self.__noIndicator = "#ffffff"

        self.__styleSheetTemplate = (
            "QProgressBar {{"
            " border: 2px solid black;"
            " border-radius: 5px;"
            " text-align: center; }}"
            "QProgressBar::chunk:horizontal {{"
            " background-color: {0}; }}"
        )
        self.setStyleSheet(self.__styleSheetTemplate.format(self.__noIndicator))

    def checkPasswordStrength(self, password):
        """
        Public slot to check the password strength and update the
        progress bar accordingly.

        @param password password to be checked
        @type str
        """
        strength = PasswordChecker().checkPassword(password)
        self.setStyleSheet(
            self.__styleSheetTemplate.format(self.__indicatorColors[strength])
        )
        super().setValue((strength + 1) * self.__increment)

    def setValue(self, _value):
        """
        Public method to set the value.

        Overwritten to do nothing.

        @param _value value (unused)
        @type int
        """
        pass

    def setMaximum(self, _value):
        """
        Public method to set the maximum value.

        Overwritten to do nothing.

        @param _value maximum value (unused)
        @type int
        """
        pass

    def setMinimum(self, _value):
        """
        Public method to set the minimal value.

        Overwritten to do nothing.

        @param _value minimum value (unused)
        @type int
        """
        pass


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    meter = EricPasswordMeter()
    meter.show()
    meter.checkPasswordStrength("Blah2+")
    app.exec()
