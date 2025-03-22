# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the request handler base class of the eric-ide server.
"""

from .EricRequestCategory import EricRequestCategory


class EricServerBaseRequestHandler:
    """
    Class implementing the request handler base class of the eric-ide server.
    """

    def __init__(self, server):
        """
        Constructor

        @param server reference to the eric-ide server object
        @type EricServer
        """
        self._server = server

        self._category = EricRequestCategory.Generic
        # must be changed by derived classes

        self._requestMethodMapping = {}
        # must be filled by derived classes

    def handleRequest(self, request, params, reqestUuid):
        """
        Public method handling the received file system requests.

        @param request request name
        @type str
        @param params dictionary containing the request parameters
        @type dict
        @param reqestUuid UUID of the associated request as sent by the eric IDE
        @type str
        """
        try:
            result = self._requestMethodMapping[request](params)
            if result is not None:
                self._server.sendJson(
                    category=self._category,
                    reply=request,
                    params=result,
                    reqestUuid=reqestUuid,
                )

        except KeyError:
            self.sendError(request=request, reqestUuid=reqestUuid)

    def sendError(self, request, reqestUuid=""):
        """
        Public method to send an error report to the IDE.

        @param request request name
        @type str
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        """
        self._server.sendJson(
            category=self._category,
            reply=request,
            params={"Error": f"Request type '{request}' is not supported."},
            reqestUuid=reqestUuid,
        )
