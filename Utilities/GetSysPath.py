# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module to get sys.path of an external interpreter.
"""

import json
import sys

if __name__ == "__main__":
    # print sys.path to stdout
    print(json.dumps(sys.path))

    sys.exit(0)

#
# eflag: noqa = M701, M801
