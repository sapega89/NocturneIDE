# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>

"""
Module defining additions to the standard Python profile.py.
"""

import atexit
import contextlib
import marshal
import os
import pickle  # secok
import profile


class PyProfile(profile.Profile):
    """
    Class extending the standard Python profiler with additional methods.

    This class extends the standard Python profiler by the functionality to
    save the collected timing data in a timing cache, to restore these data
    on subsequent calls, to store a profile dump to a standard filename and
    to erase these caches.
    """

    def __init__(self, basename, timer=None, bias=None):
        """
        Constructor

        @param basename name of the script to be profiled
        @type str
        @param timer function defining the timing calculation
        @type function
        @param bias calibration value
        @type float
        """
        try:
            profile.Profile.__init__(self, timer, bias)
        except TypeError:
            profile.Profile.__init__(self, timer)

        self.dispatch = self.__class__.dispatch

        basename = os.path.splitext(basename)[0]
        self.profileCache = "{0}.profile".format(basename)
        self.timingCache = "{0}.timings".format(basename)

        self.__restore()
        atexit.register(self.save)

    def __restore(self):
        """
        Private method to restore the timing data from the timing cache.
        """
        if not os.path.exists(self.timingCache):
            return

        with contextlib.suppress(OSError, EOFError, ValueError, TypeError), open(
            self.timingCache, "rb"
        ) as cache:
            timings = marshal.load(cache)  # secok
            if isinstance(timings, dict):
                self.timings = timings

    def save(self):
        """
        Public method to store the collected profile data.
        """
        # dump the raw timing data
        with contextlib.suppress(OSError), open(self.timingCache, "wb") as cache:
            marshal.dump(self.timings, cache)

        # dump the profile data
        self.dump_stats(self.profileCache)

    def dump_stats(self, file):
        """
        Public method to dump the statistics data.

        @param file name of the file to write to
        @type str
        """
        self.create_stats()
        with contextlib.suppress(OSError, pickle.PickleError), open(file, "wb") as f:
            pickle.dump(self.stats, f, 4)

    def erase(self):
        """
        Public method to erase the collected timing data.
        """
        self.timings = {}
        if os.path.exists(self.timingCache):
            os.remove(self.timingCache)

    def fix_frame_filename(self, frame):
        """
        Public method used to fix up the filename for a given frame.

        The logic employed here is that if a module was loaded
        from a .pyc file, then the correct .py to operate with
        should be in the same path as the .pyc. The reason this
        logic is needed is that when a .pyc file is generated, the
        filename embedded and thus what is readable in the code object
        of the frame object is the fully qualified filepath when the
        pyc is generated. If files are moved from machine to machine
        this can break debugging as the .pyc will refer to the .py
        on the original machine. Another case might be sharing
        code over a network... This logic deals with that.

        @param frame frame object
        @type frame
        @return fixed up file name
        @rtype str
        """
        versionExt = ".py3"

        # get module name from __file__
        if (
            not isinstance(frame, profile.Profile.fake_frame)
            and "__file__" in frame.f_globals
        ):
            root, ext = os.path.splitext(frame.f_globals["__file__"])
            if ext in [".pyc", ".py", versionExt, ".pyo"]:
                fixedName = root + ".py"
                if os.path.exists(fixedName):
                    return fixedName

                fixedName = root + versionExt
                if os.path.exists(fixedName):
                    return fixedName

        return frame.f_code.co_filename

    def trace_dispatch_call(self, frame, t):
        """
        Public method used to trace functions calls.

        This is a variant of the one found in the standard Python
        profile.py calling fix_frame_filename above.

        @param frame reference to the call frame
        @type frame
        @param t arguments
        @type list of Any
        @return flag indicating a successful handling
        @rtype int
        """
        if self.cur and frame.f_back is not self.cur[-2]:
            _rpt, _rit, _ret, rfn, rframe, _rcur = self.cur
            if not isinstance(rframe, profile.Profile.fake_frame):
                assert rframe.f_back is frame.f_back, (  # secok
                    "Bad call",
                    rfn,
                    rframe,
                    rframe.f_back,
                    frame,
                    frame.f_back,
                )
                self.trace_dispatch_return(rframe, 0)
                assert self.cur is None or frame.f_back is self.cur[-2], (  # secok
                    "Bad call",
                    self.cur[-3],
                )
        fcode = frame.f_code
        fn = (self.fix_frame_filename(frame), fcode.co_firstlineno, fcode.co_name)
        self.cur = (t, 0, 0, fn, frame, self.cur)
        timings = self.timings
        if fn in timings:
            cc, ns, tt, ct, callers = timings[fn]
            timings[fn] = cc, ns + 1, tt, ct, callers
        else:
            timings[fn] = 0, 0, 0, 0, {}
        return 1

    dispatch = {
        "call": trace_dispatch_call,
        "exception": profile.Profile.trace_dispatch_exception,
        "return": profile.Profile.trace_dispatch_return,
        "c_call": profile.Profile.trace_dispatch_c_call,
        "c_exception": profile.Profile.trace_dispatch_return,
        # the C function returned
        "c_return": profile.Profile.trace_dispatch_return,
    }
