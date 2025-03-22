# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the snapshot mode enumeration.
"""

import enum


class SnapshotModes(enum.Enum):
    """
    Class implementing the snapshot modes.
    """

    FULLSCREEN = 0
    SELECTEDSCREEN = 1
    RECTANGLE = 2
    FREEHAND = 3
    ELLIPSE = 4
    SELECTEDWINDOW = 5
