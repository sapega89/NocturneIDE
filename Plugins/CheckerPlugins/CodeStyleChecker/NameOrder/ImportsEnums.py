# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some enums for the import order checker.
"""

#
# adapted from flake8-alphabetize v0.0.21
#

import enum


class GroupEnum(enum.IntEnum):
    """
    Class representing the various import groups.
    """

    FUTURE = 1
    STDLIB = 2
    THIRDPARTY = 3
    FIRSTPARTY = 4
    LOCALPATH = 5


class NodeTypeEnum(enum.IntEnum):
    """
    Class representing the import node types.
    """

    IMPORT = 1
    IMPORT_FROM = 2
