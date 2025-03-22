# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the feature permission bar widget.
"""

import contextlib

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricAnimatedWidget import EricAnimatedWidget


class FeaturePermissionBar(EricAnimatedWidget):
    """
    Class implementing the feature permission bar widget.

    Note: This is not needed for Qt 6.8+.
    """

    DefaultHeight = 30

    def __init__(self, page, origin, feature, manager):
        """
        Constructor

        @param page reference to the web page
        @type QWebView
        @param origin security origin requesting the feature
        @type QUrl
        @param feature requested feature
        @type QWebPage.Feature
        @param manager reference to the feature permissions manager
        @type FeaturePermissionManager
        """
        super().__init__(parent=page.view())

        self.__origin = QUrl(origin)
        self.__feature = feature
        self.__page = page
        self.__manager = manager

        self.__permissionFeatureTexts = {
            QWebEnginePage.Feature.Geolocation: self.tr(
                "{0} wants to use your position."
            ),
            QWebEnginePage.Feature.MediaAudioCapture: self.tr(
                "{0} wants to use your microphone."
            ),
            QWebEnginePage.Feature.MediaVideoCapture: self.tr(
                "{0} wants to use your camera."
            ),
            QWebEnginePage.Feature.MediaAudioVideoCapture: self.tr(
                "{0} wants to use your microphone and camera."
            ),
            QWebEnginePage.Feature.MouseLock: self.tr("{0} wants to lock your mouse."),
            QWebEnginePage.Feature.DesktopVideoCapture: self.tr(
                "{0} wants to capture video of your screen."
            ),
            QWebEnginePage.Feature.DesktopAudioVideoCapture: self.tr(
                "{0} wants to capture audio and video of your screen."
            ),
            QWebEnginePage.Feature.Notifications: self.tr(
                "{0} wants to use desktop notifications."
            ),
        }

        self.__permissionFeatureIconNames = {
            QWebEnginePage.Feature.Geolocation: "geolocation",
            QWebEnginePage.Feature.MediaAudioCapture: "audiocapture",
            QWebEnginePage.Feature.MediaVideoCapture: "camera",
            QWebEnginePage.Feature.MediaAudioVideoCapture: "audio-video",
            QWebEnginePage.Feature.MouseLock: "mouse",
            QWebEnginePage.Feature.DesktopVideoCapture: "desktopVideoCapture",
            QWebEnginePage.Feature.DesktopAudioVideoCapture: "desktopAudioVideoCapture",
            QWebEnginePage.Feature.Notifications: "notification",
        }

        self.setAutoFillBackground(True)
        self.__layout = QHBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.setContentsMargins(9, 0, 0, 0)
        self.__iconLabel = QLabel(self)
        self.__layout.addWidget(self.__iconLabel)
        self.__messageLabel = QLabel(self)
        self.__layout.addWidget(self.__messageLabel)
        self.__layout.addStretch()
        self.__rememberButton = QPushButton(self.tr("Remember"), self)
        self.__rememberButton.setCheckable(True)
        self.__allowButton = QPushButton(self.tr("Allow"), self)
        self.__denyButton = QPushButton(self.tr("Deny"), self)
        self.__discardButton = QPushButton(EricPixmapCache.getIcon("close"), "", self)
        self.__allowButton.clicked.connect(self.__permissionGranted)
        self.__denyButton.clicked.connect(self.__permissionDenied)
        self.__discardButton.clicked.connect(self.__permissionUnknown)
        self.__layout.addWidget(self.__rememberButton)
        self.__layout.addWidget(self.__allowButton)
        self.__layout.addWidget(self.__denyButton)
        self.__layout.addWidget(self.__discardButton)

        with contextlib.suppress(KeyError):
            self.__iconLabel.setPixmap(
                EricPixmapCache.getPixmap(
                    self.__permissionFeatureIconNames[self.__feature]
                )
            )

        try:
            self.__messageLabel.setText(
                self.__permissionFeatureTexts[self.__feature].format(
                    self.__origin.host()
                )
            )
        except KeyError:
            self.__messageLabel.setText(
                self.tr("{0} wants to use an unknown feature.").format(
                    self.__origin.host()
                )
            )

        self.__page.loadStarted.connect(self.hide)

        self.resize(self.__page.view().width(), self.height())
        self.startAnimation()

    @pyqtSlot()
    def hide(self):
        """
        Public slot to hide the animated widget.
        """
        self.__page.loadStarted.disconnect(self.hide)
        super().hide()

    @pyqtSlot()
    def __permissionDenied(self):
        """
        Private slot handling the user pressing the deny button.
        """
        if self.__page is None or self.__manager is None:
            return

        self.__page.setFeaturePermission(
            self.__origin,
            self.__feature,
            QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
        )

        if self.__rememberButton.isChecked():
            self.__manager.rememberFeaturePermission(
                self.__page.url().host(),
                self.__feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            )

        self.hide()

    @pyqtSlot()
    def __permissionGranted(self):
        """
        Private slot handling the user pressing the allow button.
        """
        if self.__page is None or self.__manager is None:
            return

        self.__page.setFeaturePermission(
            self.__origin,
            self.__feature,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
        )

        if self.__rememberButton.isChecked():
            self.__manager.rememberFeaturePermission(
                self.__page.url().host(),
                self.__feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            )

        self.hide()

    @pyqtSlot()
    def __permissionUnknown(self):
        """
        Private slot handling the user closing the dialog without a selection.
        """
        if self.__page is None or self.__manager is None:
            return

        self.__page.setFeaturePermission(
            self.__origin,
            self.__feature,
            QWebEnginePage.PermissionPolicy.PermissionUnknown,
        )

        self.hide()
