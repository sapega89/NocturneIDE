# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for potentially hardcoded AWS passwords.
"""

#
# This is a modified version of the one found at
# https://pypi.org/project/bandit-aws/.
#
# Original Copyright 2020 CMCRC (devcdt@cmcrc.com)
#
# Original License: GPLv3
#

import math
import re
import string

from collections import Counter


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Str": [
            (checkHardcodedAwsKey, ("S801", "S802")),
        ],
    }


AWS_ACCESS_KEY_ID_SYMBOLS = string.ascii_uppercase + string.digits
AWS_ACCESS_KEY_ID_REGEX = re.compile("[" + AWS_ACCESS_KEY_ID_SYMBOLS + "]{20}")
AWS_ACCESS_KEY_ID_MAX_ENTROPY = 3

AWS_SECRET_ACCESS_KEY_SYMBOLS = string.ascii_letters + string.digits + "/+="
AWS_SECRET_ACCESS_KEY_REGEX = re.compile("[" + AWS_SECRET_ACCESS_KEY_SYMBOLS + "]{40}")
AWS_SECRET_ACCESS_KEY_MAX_ENTROPY = 4.5


def shannonEntropy(data, symbols):
    """
    Function to caclculate the Shannon entropy of some given data.

    Source:
    http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html

    @param data data to calculate the entropy for
    @type str
    @param symbols allowed symbols
    @type str
    @return Shannon entropy of the given data
    @rtype float
    """
    if not data:
        return 0
    entropy = 0
    counts = Counter(data)
    for x in symbols:
        p_x = float(counts[x]) / len(data)
        if p_x > 0:
            entropy += -p_x * math.log(p_x, 2)
    return entropy


def checkHardcodedAwsKey(reportError, context, _config):
    """
    Function to check for potentially hardcoded AWS passwords.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    node = context.node
    if AWS_ACCESS_KEY_ID_REGEX.fullmatch(node.value):
        entropy = shannonEntropy(node.value, AWS_ACCESS_KEY_ID_SYMBOLS)
        if entropy > AWS_ACCESS_KEY_ID_MAX_ENTROPY:
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S801",
                "L",
                "M",
                node.value,
            )

    elif AWS_SECRET_ACCESS_KEY_REGEX.fullmatch(node.value):
        entropy = shannonEntropy(node.value, AWS_SECRET_ACCESS_KEY_SYMBOLS)
        if entropy > AWS_SECRET_ACCESS_KEY_MAX_ENTROPY:
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S802",
                "M",
                "M",
                node.value,
            )
