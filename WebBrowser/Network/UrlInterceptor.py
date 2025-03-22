# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an URL interceptor base class.
"""

from PyQt6.QtCore import QObject


class UrlInterceptor(QObject):
    """
    Class implementing an URL interceptor base class.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent referemce to the parent object
        @type QObject
        """
        super().__init__(parent)

    def interceptRequest(self, info):
        """
        Public method to intercept a request.

        @param info request info object
        @type QWebEngineUrlRequestInfo
        """
        pass
