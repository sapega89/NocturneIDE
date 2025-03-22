# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an enum for the various service categories.
"""

import enum


class EricRequestCategory(enum.IntEnum):
    """
    Class defining the service categories of the eric remote server.
    """

    FileSystem = 0
    Project = 1
    Debugger = 2
    Coverage = 3
    EditorConfig = 4

    Echo = 252
    Server = 253
    Error = 254  # only sent by the server to report an issue
    Generic = 255

    # user/plugins may define own categories starting with this value
    UserCategory = 1024
