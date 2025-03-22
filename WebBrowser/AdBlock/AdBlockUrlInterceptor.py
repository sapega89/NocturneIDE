# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an URL interceptor base class.
"""

from ..Network.UrlInterceptor import UrlInterceptor


class AdBlockUrlInterceptor(UrlInterceptor):
    """
    Class implementing an URL interceptor for AdBlock.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the AdBlock manager
        @type AdBlockManager
        @param parent referemce to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__manager = manager

    def interceptRequest(self, info):
        """
        Public method to intercept a request.

        @param info request info object
        @type QWebEngineUrlRequestInfo
        """
        if self.__manager.block(info):
            info.block(True)
