# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the breakpoint and watch class.
"""

import contextlib
import os


class Breakpoint:
    """
    Breakpoint class.

    Implements temporary breakpoints, ignore counts, disabling and
    (re)-enabling, and conditionals.

    Breakpoints are indexed by the file,line tuple using breaks. It
    points to a single Breakpoint instance. This is rather different to
    the original bdb, since there may be more than one breakpoint per line.

    To test for a specific line in a file there is another dict breakInFile,
    which is indexed only by filename and holds all line numbers where
    breakpoints are.
    """

    breaks = {}  # indexed by (filename, lineno) tuple: Breakpoint
    breakInFile = {}  # indexed by filename: [lineno]
    breakInFrameCache = {}

    def __init__(self, filename, lineno, temporary=False, cond=None):
        """
        Constructor

        @param filename file name where a breakpoint is set
        @type str
        @param lineno line number of the breakpoint
        @type int
        @param temporary flag to indicate a temporary breakpoint
        @type bool
        @param cond Python expression which dynamically enables this bp
        @type str
        """
        filename = os.path.abspath(filename)
        self.file = filename
        self.line = lineno
        self.temporary = temporary
        self.cond = cond
        self.enabled = True
        self.ignore = 0
        self.hits = 0
        Breakpoint.breaks[(filename, lineno)] = self
        lines = Breakpoint.breakInFile.setdefault(filename, [])
        if lineno not in lines:
            lines.append(lineno)
        Breakpoint.breakInFrameCache.clear()

    def deleteMe(self):
        """
        Public method to clear this breakpoint.
        """
        with contextlib.suppress(KeyError):
            del Breakpoint.breaks[(self.file, self.line)]
            Breakpoint.breakInFile[self.file].remove(self.line)
            if not Breakpoint.breakInFile[self.file]:
                del Breakpoint.breakInFile[self.file]

    def enable(self):
        """
        Public method to enable this breakpoint.
        """
        self.enabled = True

    def disable(self):
        """
        Public method to disable this breakpoint.
        """
        self.enabled = False

    @staticmethod
    def clear_break(filename, lineno):
        """
        Static method reimplemented from bdb.py to clear a breakpoint.

        @param filename file name of the bp to retrieve
        @type str
        @param lineno line number of the bp to retrieve
        @type int
        """
        bp = Breakpoint.breaks.get((filename, lineno))
        if bp:
            bp.deleteMe()
        Breakpoint.breakInFrameCache.clear()

    @staticmethod
    def clear_all_breaks():
        """
        Static method to clear all breakpoints.
        """
        Breakpoint.breaks.clear()
        Breakpoint.breakInFile.clear()
        Breakpoint.breakInFrameCache.clear()

    @staticmethod
    def get_break(filename, lineno):
        """
        Static method to get the breakpoint of a particular line.

        Because eric supports only one breakpoint per line, this
        method will return only one breakpoint.

        @param filename file name of the bp to retrieve
        @type str
        @param lineno line number of the bp to retrieve
        @type int
        @return Breakpoint or None, if there is no bp
        @rtype Breakpoint object or None
        """
        return Breakpoint.breaks.get((filename, lineno))

    @staticmethod
    def effectiveBreak(filename, lineno, frame):
        """
        Static method to determine which breakpoint for this filename:lineno
        is to be acted upon.

        Called only if we know there is a bpt at this
        location.  Returns breakpoint that was triggered and a flag
        that indicates if it is ok to delete a temporary bp.

        @param filename file name of the bp to retrieve
        @type str
        @param lineno line number of the bp to retrieve
        @type int
        @param frame the current execution frame
        @type frame object
        @return tuple of Breakpoint and a flag to indicate, that a
            temporary breakpoint may be deleted
        @rtype tuple of Breakpoint, bool
        """
        b = Breakpoint.breaks[filename, lineno]
        if not b.enabled:
            return (None, False)

        # Count every hit when bp is enabled
        b.hits += 1
        if not b.cond:
            # If unconditional, and ignoring,
            # go on to next, else break
            if b.ignore > 0:
                b.ignore -= 1
                return (None, False)
            else:
                # breakpoint and marker that's ok
                # to delete if temporary
                return (b, True)
        else:
            # Conditional bp.
            # Ignore count applies only to those bpt hits where the
            # condition evaluates to true.
            try:
                val = eval(b.cond, frame.f_globals, frame.f_locals)  # secok
                if val:
                    if b.ignore > 0:
                        b.ignore -= 1
                        # continue
                    else:
                        return (b, True)
            except Exception:
                # if eval fails, most conservative
                # thing is to stop on breakpoint
                # regardless of ignore count.
                # Don't delete temporary,
                # as another hint to user.
                return (b, False)
        return (None, False)


class Watch:
    """
    Watch class.

    Implements temporary watches, ignore counts, disabling and
    (re)-enabling, and conditionals.
    """

    watches = []

    def __init__(self, cond, compiledCond, flag, temporary=False):
        """
        Constructor

        @param cond condition as string with flag
        @type str
        @param compiledCond precompiled condition
        @type code object
        @param flag indicates type of watch (created or changed)
        @type str
        @param temporary flag for temporary watches
        @type bool
        """
        # Should not occur
        if not cond:
            return

        self.cond = cond
        self.compiledCond = compiledCond
        self.temporary = temporary

        self.enabled = True
        self.ignore = 0

        self.created = False
        self.changed = False
        if flag == "??created??":
            self.created = True
        elif flag == "??changed??":
            self.changed = True

        self.values = {}
        Watch.watches.append(self)

    def deleteMe(self):
        """
        Public method to clear this watch expression.
        """
        with contextlib.suppress(ValueError):
            del Watch.watches[self]

    def enable(self):
        """
        Public method to enable this watch.
        """
        self.enabled = True

    def disable(self):
        """
        Public method to disable this watch.
        """
        self.enabled = False

    @staticmethod
    def clear_watch(cond):
        """
        Static method to clear a watch expression.

        @param cond expression of the watch expression to be cleared
        @type str
        """
        with contextlib.suppress(ValueError):
            Watch.watches.remove(Watch.get_watch(cond))

    @staticmethod
    def clear_all_watches():
        """
        Static method to clear all watch expressions.
        """
        del Watch.watches[:]

    @staticmethod
    def get_watch(cond):
        """
        Static method to get a watch expression.

        @param cond expression of the watch expression to be cleared
        @type str
        @return reference to the watch point
        @rtype Watch or None
        """
        for b in Watch.watches:
            if b.cond == cond:
                return b

        return None

    @staticmethod
    def effectiveWatch(frame):
        """
        Static method to determine, if a watch expression is effective.

        @param frame the current execution frame
        @type frame object
        @return tuple of watch expression and a flag to indicate, that a
            temporary watch expression may be deleted
        @rtype tuple of Watch, int
        """
        for b in Watch.watches:
            if not b.enabled:
                continue
            try:
                val = eval(b.compiledCond, frame.f_globals, frame.f_locals)
                # secok
                if b.created:
                    if frame in b.values:
                        continue
                    else:
                        b.values[frame] = [1, val, b.ignore]
                        return (b, True)

                elif b.changed:
                    try:
                        if b.values[frame][1] != val:
                            b.values[frame][1] = val
                        else:
                            continue
                    except KeyError:
                        b.values[frame] = [1, val, b.ignore]

                    if b.values[frame][2] > 0:
                        b.values[frame][2] -= 1
                        continue
                    else:
                        return (b, True)

                elif val:
                    if b.ignore > 0:
                        b.ignore -= 1
                        continue
                    else:
                        return (b, True)
            except Exception:  # secok
                continue
        return (None, False)
