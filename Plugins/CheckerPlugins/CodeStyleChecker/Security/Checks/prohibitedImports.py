# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for prohibited imports.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2016 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

_prohibitedImports = {
    "S401": (["telnetlib"], "H"),
    "S402": (["ftplib"], "H"),
    "S403": (["pickle", "cPickle", "dill", "shelve"], "L"),
    "S404": (["subprocess"], "L"),
    "S405": (["xml.etree.cElementTree", "xml.etree.ElementTree"], "L"),
    "S406": (["xml.sax"], "L"),
    "S407": (["xml.dom.expatbuilder"], "L"),
    "S408": (["xml.dom.minidom"], "L"),
    "S409": (["xml.dom.pulldom"], "L"),
    "S410": (["lxml"], "L"),
    "S411": (["xmlrpc"], "H"),
    "S412": (
        [
            "wsgiref.handlers.CGIHandler",
            "twisted.web.twcgi.CGIScript",
            "twisted.web.twcgi.CGIDirectory",
        ],
        "H",
    ),
    "S413": (
        [
            "Crypto.Cipher",
            "Crypto.Hash",
            "Crypto.IO",
            "Crypto.Protocol",
            "Crypto.PublicKey",
            "Crypto.Random",
            "Crypto.Signature",
            "Crypto.Util",
        ],
        "H",
    ),
    "S414": (["pyghmi"], "H"),
}


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Import": [
            (checkProhibitedImports, tuple(_prohibitedImports)),
        ],
        "ImportFrom": [
            (checkProhibitedImports, tuple(_prohibitedImports)),
        ],
        "Call": [
            (checkProhibitedImports, tuple(_prohibitedImports)),
        ],
    }


def checkProhibitedImports(reportError, context, _config):
    """
    Function to check for prohibited imports.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    nodeType = context.node.__class__.__name__

    if nodeType.startswith("Import"):
        prefix = ""
        if nodeType == "ImportFrom" and context.node.module is not None:
            prefix = context.node.module + "."

        for code in _prohibitedImports:
            qualnames, severity = _prohibitedImports[code]
            for name in context.node.names:
                for qualname in qualnames:
                    if (prefix + name.name).startswith(qualname):
                        reportError(
                            context.node.lineno - 1,
                            context.node.col_offset,
                            code,
                            severity,
                            "H",
                            name.name,
                        )
