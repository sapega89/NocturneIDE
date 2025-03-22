# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Notifications configuration page.
"""

from PyQt6.QtCore import QPoint, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QColorDialog

from eric7 import Preferences
from eric7.UI.NotificationWidget import NotificationFrame, NotificationTypes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_NotificationsPage import Ui_NotificationsPage


class NotificationsPage(ConfigurationPageBase, Ui_NotificationsPage):
    """
    Class implementing the Notifications configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("NotificationsPage")

        geom = QApplication.screens()[0].availableVirtualGeometry()
        self.xSpinBox.setMinimum(geom.x())
        self.xSpinBox.setMaximum(geom.width())
        self.ySpinBox.setMinimum(geom.y())
        self.ySpinBox.setMaximum(geom.height())

        self.warningIcon.setPixmap(NotificationFrame.getIcon(NotificationTypes.WARNING))
        self.criticalIcon.setPixmap(
            NotificationFrame.getIcon(NotificationTypes.CRITICAL)
        )

        self.__notification = None
        self.__firstTime = True

        # set initial values
        self.timeoutSpinBox.setValue(Preferences.getUI("NotificationTimeout"))
        point = Preferences.getUI("NotificationPosition")
        self.xSpinBox.setValue(point.x())
        self.ySpinBox.setValue(point.y())

        self.xSpinBox.valueChanged.connect(self.__moveNotification)
        self.ySpinBox.valueChanged.connect(self.__moveNotification)

        self.__colors = {}
        self.__colors["NotificationWarningForeground"] = Preferences.getUI(
            "NotificationWarningForeground"
        )
        self.__colors["NotificationWarningBackground"] = Preferences.getUI(
            "NotificationWarningBackground"
        )
        self.__colors["NotificationCriticalForeground"] = Preferences.getUI(
            "NotificationCriticalForeground"
        )
        self.__colors["NotificationCriticalBackground"] = Preferences.getUI(
            "NotificationCriticalBackground"
        )

        self.warningFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationWarningForeground"],
                self.__colors["NotificationWarningBackground"],
            )
        )
        self.criticalFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationCriticalForeground"],
                self.__colors["NotificationCriticalBackground"],
            )
        )

    def save(self):
        """
        Public slot to save the Notifications configuration.
        """
        Preferences.setUI("NotificationTimeout", self.timeoutSpinBox.value())
        Preferences.setUI(
            "NotificationPosition", QPoint(self.xSpinBox.value(), self.ySpinBox.value())
        )

        for key in self.__colors:
            Preferences.setUI(key, self.__colors[key])

    @pyqtSlot(bool)
    def on_visualButton_clicked(self, checked):
        """
        Private slot to select the position visually.

        @param checked state of the button
        @type bool
        """
        from eric7.UI.NotificationWidget import NotificationWidget

        if checked:
            self.__notification = NotificationWidget(parent=self, setPosition=True)
            self.__notification.showNotification(
                NotificationFrame.getIcon(NotificationTypes.OTHER),
                self.tr("Visual Selection"),
                self.tr(
                    "Drag the notification window to"
                    " the desired place and release the button."
                ),
                timeout=0,
            )
            self.__notification.move(
                QPoint(self.xSpinBox.value(), self.ySpinBox.value())
            )
            if self.__firstTime:
                # adjust the maximum values to the width of the notification
                self.xSpinBox.setMaximum(
                    self.xSpinBox.maximum() - self.__notification.width()
                )
                self.ySpinBox.setMaximum(
                    self.ySpinBox.maximum() - self.__notification.height()
                )
                self.__firstTime = False
        else:
            # retrieve the position
            point = self.__notification.frameGeometry().topLeft()
            self.xSpinBox.setValue(point.x())
            self.ySpinBox.setValue(point.y())
            self.__notification.close()
            self.__notification = None

    @pyqtSlot()
    def __moveNotification(self):
        """
        Private slot to move the notification widget.
        """
        if self.visualButton.isChecked():
            self.__notification.move(self.xSpinBox.value(), self.ySpinBox.value())

    ##################################################################
    ## colors for warning notifications
    ##################################################################

    @pyqtSlot()
    def on_warningFgButton_clicked(self):
        """
        Private slot to set the foreground color of the warning notifications.
        """
        color = QColorDialog.getColor(
            QColor(self.__colors["NotificationWarningForeground"])
        )
        if color.isValid():
            self.__colors["NotificationWarningForeground"] = color.name()
            self.warningFrame.setStyleSheet(
                NotificationFrame.NotificationStyleSheetTemplate.format(
                    self.__colors["NotificationWarningForeground"],
                    self.__colors["NotificationWarningBackground"],
                )
            )

    @pyqtSlot()
    def on_warningBgButton_clicked(self):
        """
        Private slot to set the background color of the warning notifications.
        """
        color = QColorDialog.getColor(
            QColor(self.__colors["NotificationWarningBackground"])
        )
        if color.isValid():
            self.__colors["NotificationWarningBackground"] = color.name()
            self.warningFrame.setStyleSheet(
                NotificationFrame.NotificationStyleSheetTemplate.format(
                    self.__colors["NotificationWarningForeground"],
                    self.__colors["NotificationWarningBackground"],
                )
            )

    @pyqtSlot()
    def on_warningResetButton_clicked(self):
        """
        Private slot to reset the colors for warning notifications to their
        current values.
        """
        self.__colors["NotificationWarningForeground"] = Preferences.getUI(
            "NotificationWarningForeground"
        )
        self.__colors["NotificationWarningBackground"] = Preferences.getUI(
            "NotificationWarningBackground"
        )
        self.warningFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationWarningForeground"],
                self.__colors["NotificationWarningBackground"],
            )
        )

    @pyqtSlot()
    def on_warningDefaultButton_clicked(self):
        """
        Private slot to reset the colors for warning notifications to their
        default values.
        """
        self.__colors["NotificationWarningForeground"] = Preferences.Prefs.uiDefaults[
            "NotificationWarningForeground"
        ]
        self.__colors["NotificationWarningBackground"] = Preferences.Prefs.uiDefaults[
            "NotificationWarningBackground"
        ]
        self.warningFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationWarningForeground"],
                self.__colors["NotificationWarningBackground"],
            )
        )

    ##################################################################
    ## colors for critical notifications
    ##################################################################

    @pyqtSlot()
    def on_criticalFgButton_clicked(self):
        """
        Private slot to set the foreground color of the critical notifications.
        """
        color = QColorDialog.getColor(
            QColor(self.__colors["NotificationCriticalForeground"])
        )
        if color.isValid():
            self.__colors["NotificationCriticalForeground"] = color.name()
            self.criticalFrame.setStyleSheet(
                NotificationFrame.NotificationStyleSheetTemplate.format(
                    self.__colors["NotificationCriticalForeground"],
                    self.__colors["NotificationCriticalBackground"],
                )
            )

    @pyqtSlot()
    def on_criticalBgButton_clicked(self):
        """
        Private slot to set the background color of the critical notifications.
        """
        color = QColorDialog.getColor(
            QColor(self.__colors["NotificationCriticalBackground"])
        )
        if color.isValid():
            self.__colors["NotificationCriticalBackground"] = color.name()
            self.criticalFrame.setStyleSheet(
                NotificationFrame.NotificationStyleSheetTemplate.format(
                    self.__colors["NotificationCriticalForeground"],
                    self.__colors["NotificationCriticalBackground"],
                )
            )

    @pyqtSlot()
    def on_criticalResetButton_clicked(self):
        """
        Private slot to reset the colors for critical notifications to their
        current values.
        """
        self.__colors["NotificationCriticalForeground"] = Preferences.getUI(
            "NotificationCriticalForeground"
        )
        self.__colors["NotificationCriticalBackground"] = Preferences.getUI(
            "NotificationCriticalBackground"
        )
        self.criticalFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationCriticalForeground"],
                self.__colors["NotificationCriticalBackground"],
            )
        )

    @pyqtSlot()
    def on_criticalDefaultButton_clicked(self):
        """
        Private slot to reset the colors for critical notifications to their
        default values.
        """
        self.__colors["NotificationCriticalForeground"] = Preferences.Prefs.uiDefaults[
            "NotificationCriticalForeground"
        ]
        self.__colors["NotificationCriticalBackground"] = Preferences.Prefs.uiDefaults[
            "NotificationCriticalBackground"
        ]
        self.criticalFrame.setStyleSheet(
            NotificationFrame.NotificationStyleSheetTemplate.format(
                self.__colors["NotificationCriticalForeground"],
                self.__colors["NotificationCriticalBackground"],
            )
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = NotificationsPage()
    return page
