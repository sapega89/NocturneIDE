# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for use of SSL/TLS with insecure protocols.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

from Security.SecurityDefaults import SecurityDefaults


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkInsecureSslProtocolVersion, ("S502",)),
            (checkSslWithoutVersion, ("S504",)),
        ],
        "FunctionDef": [
            (checkInsecureSslDefaults, ("S503",)),
        ],
    }


def checkInsecureSslProtocolVersion(reportError, context, config):
    """
    Function to check for use of insecure SSL protocol version.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    insecureProtocolVersions = (
        config["insecure_ssl_protocol_versions"]
        if config and "insecure_ssl_protocol_versions" in config
        else SecurityDefaults["insecure_ssl_protocol_versions"]
    )

    if context.callFunctionNameQual == "ssl.wrap_socket":
        if context.checkCallArgValue("ssl_version", insecureProtocolVersions):
            reportError(
                context.getLinenoForCallArg("ssl_version") - 1,
                context.getOffsetForCallArg("ssl_version"),
                "S502.1",
                "H",
                "H",
            )

    elif context.callFunctionNameQual == "pyOpenSSL.SSL.Context":
        if context.checkCallArgValue("method", insecureProtocolVersions):
            reportError(
                context.getLinenoForCallArg("method") - 1,
                context.getOffsetForCallArg("method"),
                "S502.2",
                "H",
                "H",
            )

    elif (
        context.callFunctionNameQual != "ssl.wrap_socket"
        and context.callFunctionNameQual != "pyOpenSSL.SSL.Context"
    ):
        if context.checkCallArgValue("method", insecureProtocolVersions):
            reportError(
                context.getLinenoForCallArg("method") - 1,
                context.getOffsetForCallArg("method"),
                "S502.3",
                "H",
                "H",
            )

        elif context.checkCallArgValue("ssl_version", insecureProtocolVersions):
            reportError(
                context.getLinenoForCallArg("ssl_version") - 1,
                context.getOffsetForCallArg("ssl_version"),
                "S502.3",
                "H",
                "H",
            )


def checkInsecureSslDefaults(reportError, context, config):
    """
    Function to check for SSL use with insecure defaults specified.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    insecureProtocolVersions = (
        config["insecure_ssl_protocol_versions"]
        if config and "insecure_ssl_protocol_versions" in config
        else SecurityDefaults["insecure_ssl_protocol_versions"]
    )

    for default in context.functionDefDefaultsQual:
        val = default.split(".")[-1]
        if val in insecureProtocolVersions:
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S503",
                "M",
                "M",
            )


def checkSslWithoutVersion(reportError, context, _config):
    """
    Function to check for SSL use with no version specified.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if (
        context.callFunctionNameQual == "ssl.wrap_socket"
        and context.checkCallArgValue("ssl_version") is None
    ):
        # checkCallArgValue() returns False if the argument is found
        # but does not match the supplied value (or the default None).
        # It returns None if the argument passed doesn't exist. This
        # tests for that (ssl_version is not specified).
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S504",
            "L",
            "M",
        )
