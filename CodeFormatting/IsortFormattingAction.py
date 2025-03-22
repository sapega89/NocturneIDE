# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an enum defining the various isort code formatting actions.
"""

import enum


class IsortFormattingAction(enum.Enum):
    """
    Class defining the various isort code formatting actions.
    """

    Sort = 0
    Check = 1
    Diff = 2
