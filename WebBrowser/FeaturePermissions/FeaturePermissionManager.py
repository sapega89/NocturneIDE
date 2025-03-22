# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the feature permission manager object.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities, Preferences
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class FeaturePermissionManager(QObject):
    """
    Class implementing the feature permission manager object.

    Note: This is not needed for Qt 6.8+.
    """

    SettingsKeyFormat = "WebBrowser/FeaturePermissions/{0}"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__featurePermissions = {
            QWebEnginePage.Feature.Geolocation: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.MediaAudioCapture: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.MediaVideoCapture: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.MediaAudioVideoCapture: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.MouseLock: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.DesktopVideoCapture: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.DesktopAudioVideoCapture: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
            QWebEnginePage.Feature.Notifications: {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            },
        }

        self.__featurePermissionsKeys = {
            (
                QWebEnginePage.Feature.Geolocation,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "GeolocationGranted",
            (
                QWebEnginePage.Feature.Geolocation,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "GeolocationDenied",
            (
                QWebEnginePage.Feature.MediaAudioCapture,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "MediaAudioCaptureGranted",
            (
                QWebEnginePage.Feature.MediaAudioCapture,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "MediaAudioCaptureDenied",
            (
                QWebEnginePage.Feature.MediaVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "MediaVideoCaptureGranted",
            (
                QWebEnginePage.Feature.MediaVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "MediaVideoCaptureDenied",
            (
                QWebEnginePage.Feature.MediaAudioVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "MediaAudioVideoCaptureGranted",
            (
                QWebEnginePage.Feature.MediaAudioVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "MediaAudioVideoCaptureDenied",
            (
                QWebEnginePage.Feature.MouseLock,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "MouseLockGranted",
            (
                QWebEnginePage.Feature.MouseLock,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "MouseLockDenied",
            (
                QWebEnginePage.Feature.DesktopVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "DesktopVideoCaptureGranted",
            (
                QWebEnginePage.Feature.DesktopVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "DesktopVideoCaptureDenied",
            (
                QWebEnginePage.Feature.DesktopAudioVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "DesktopAudioVideoCaptureGranted",
            (
                QWebEnginePage.Feature.DesktopAudioVideoCapture,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "DesktopAudioVideoCaptureDenied",
            (
                QWebEnginePage.Feature.Notifications,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            ): "NotificationsGranted",
            (
                QWebEnginePage.Feature.Notifications,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            ): "NotificationsDenied",
        }

        self.__loaded = False

    def requestFeaturePermission(self, page, origin, feature):
        """
        Public method to request a feature permission.

        @param page reference to the requesting web page
        @type QWebEnginePage
        @param origin security origin requesting the feature
        @type QUrl
        @param feature requested feature
        @type QWebEnginePage.Feature
        """
        from .FeaturePermissionBar import FeaturePermissionBar

        if origin is None or origin.isEmpty():
            return

        if not self.__loaded:
            self.__loadSettings()

        host = origin.host()

        if feature in self.__featurePermissions:
            for permission in self.__featurePermissions[feature]:
                if host in self.__featurePermissions[feature][permission]:
                    page.setFeaturePermission(origin, feature, permission)
                    return

        bar = FeaturePermissionBar(page, origin, feature, self)
        bar.show()

    def rememberFeaturePermission(self, host, feature, permission):
        """
        Public method to remember a user decision for a feature permission.

        @param host host name to remember the decision for
        @type str
        @param feature feature to be remembered
        @type QWebEnginePage.Feature
        @param permission feature permission to be remembered
        @type QWebEnginePage.PermissionPolicy
        """
        if (
            feature in self.__featurePermissions
            and host not in self.__featurePermissions[feature][permission]
        ):
            self.__featurePermissions[feature][permission].append(host)
            self.__saveSettings()

    def __loadSettings(self):
        """
        Private method to load the remembered feature permissions.
        """
        if self.__loaded:
            # no reloading allowed
            return

        for (feature, permission), key in self.__featurePermissionsKeys.items():
            self.__featurePermissions[feature][permission] = EricUtilities.toList(
                Preferences.getSettings().value(
                    FeaturePermissionManager.SettingsKeyFormat.format(key), []
                )
            )

        self.__loaded = True

    def __saveSettings(self):
        """
        Private method to save the remembered feature permissions.
        """
        if not self.__loaded:
            return

        if WebBrowserWindow.isPrivate():
            return

        for (feature, permission), key in self.__featurePermissionsKeys.items():
            Preferences.getSettings().setValue(
                FeaturePermissionManager.SettingsKeyFormat.format(key),
                self.__featurePermissions[feature][permission],
            )

    def showFeaturePermissionsDialog(self, parent=None):
        """
        Public method to show a dialog to manage the remembered feature
        permissions.

        @param parent reference to the parent widget
        @type QWidget
        """
        from .FeaturePermissionsDialog import FeaturePermissionsDialog

        if not self.__loaded:
            self.__loadSettings()

        dlg = FeaturePermissionsDialog(self.__featurePermissions, parent=parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newFeaturePermissions = dlg.getData()
            self.__featurePermissions = newFeaturePermissions
            self.__saveSettings()
