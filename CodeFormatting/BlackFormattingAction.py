# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an enum defining the various Black code formatting actions.
"""

import enum


class BlackFormattingAction(enum.Enum):
    """
    Class defining the various Black code formatting actions.
    """

    Format = 0
    Check = 1
    Diff = 2
