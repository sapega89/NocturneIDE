# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to store and parse diff output.
"""

import os
import re


class GitDiffParser:
    """
    Class implementing a class to store and parse diff output.
    """

    HunkHeaderRegexp = re.compile(r"^@@ -([0-9,]+) \+([0-9,]+) @@(.*)", re.DOTALL)

    def __init__(self, diff):
        """
        Constructor

        @param diff output of the diff command
        @type list of str
        """
        self.__diff = diff[:]

        self.__headerLines = []
        self.__hunks = []
        self.__parsed = False
        # diff parsing is done on demand

    def __initHunk(self):
        """
        Private method to initialize a hunk data structure.

        @return hunk data structure
        @rtype dict
        """
        hunk = {
            "start": -1,
            "end": -1,
            "lines": [],
            "oldStart": -1,
            "oldCount": -1,
            "newStart": -1,
            "newCount": -1,
            "heading": "",
        }
        return hunk

    def __parseRange(self, headerRange):
        """
        Private method to parse the hunk header range part.

        @param headerRange hunk header range
        @type str
        @return tuple of hunk start and hunk length
        @rtype tuple of (int, int)
        """
        if "," in headerRange:
            begin, end = headerRange.split(",", 1)
            return int(begin), int(end)
        else:
            return int(headerRange), 1

    def __parseDiff(self):
        """
        Private method to parse the diff output.

        @exception AssertionError raised when a malformed hunk header is
            encountered
        """
        if not self.__parsed:
            # step 1: extract the diff header
            for line in self.__diff:
                if not line.startswith("@@ "):
                    self.__headerLines.append(line)
                else:
                    break

            # step 2: break the rest into diff hunks
            for lineIdx, line in enumerate(self.__diff[len(self.__headerLines) :]):
                # disect the hunk header line
                m = self.HunkHeaderRegexp.match(line)
                if m:
                    self.__hunks.append(self.__initHunk())
                    self.__hunks[-1]["start"] = lineIdx
                    (
                        self.__hunks[-1]["oldStart"],
                        self.__hunks[-1]["oldCount"],
                    ) = self.__parseRange(m.group(1))
                    (
                        self.__hunks[-1]["newStart"],
                        self.__hunks[-1]["newCount"],
                    ) = self.__parseRange(m.group(2))
                    self.__hunks[-1]["heading"] = m.group(3)
                elif not self.__hunks:
                    raise AssertionError("Malformed hunk header: '{0}'".format(line))
                self.__hunks[-1]["lines"].append(line)
            # step 3: calculate hunk end lines
            for hunk in self.__hunks:
                hunk["end"] = hunk["start"] + len(hunk["lines"]) - 1

    def __generateRange(self, start, count):
        """
        Private method to generate a hunk header range.

        @param start start line
        @type int
        @param count line count
        @type int
        @return hunk header range
        @rtype str
        """
        if count == 1:
            return "{0}".format(start)
        else:
            return "{0},{1}".format(start, count)

    def __generateHunkHeader(
        self, oldStart, oldCount, newStart, newCount, heading=os.linesep
    ):
        """
        Private method to generate a hunk header line.

        @param oldStart start line of the old part
        @type int
        @param oldCount line count of the old part
        @type int
        @param newStart start line of the new part
        @type int
        @param newCount line count of the new part
        @type int
        @param heading hunk heading
        @type str
        @return hunk header
        @rtype str
        """
        return "@@ -{0} +{1} @@{2}".format(
            self.__generateRange(oldStart, oldCount),
            self.__generateRange(newStart, newCount),
            heading,
        )

    def headerLength(self):
        """
        Public method to get the header length.

        @return length of the header
        @rtype int
        """
        self.__parseDiff()
        return len(self.__headerLines)

    def createHunkPatch(self, lineIndex):
        """
        Public method to create a hunk based patch.

        @param lineIndex line number of the hunk
        @type int
        @return diff lines of the patch
        @rtype str
        """
        self.__parseDiff()

        patch = self.__headerLines[:]
        for hunk in self.__hunks:
            if hunk["start"] <= lineIndex <= hunk["end"]:
                patch.extend(hunk["lines"])
                break

        return "".join(patch)

    def createLinesPatch(self, startIndex, endIndex, reverse=False):
        """
        Public method to create a selected lines based patch.

        @param startIndex start line number
        @type int
        @param endIndex end line number
        @type int
        @param reverse flag indicating a reverse patch
        @type bool
        @return diff lines of the patch
        @rtype str
        """
        self.__parseDiff()

        ADDITION = "+"
        DELETION = "-"
        CONTEXT = " "
        NONEWLINE = "\\"

        patch = []
        startOffset = 0

        for hunk in self.__hunks:
            if hunk["end"] < startIndex:
                # skip hunks before the selected lines
                continue

            if hunk["start"] > endIndex:
                # done, exit the loop
                break

            counts = {
                ADDITION: 0,
                DELETION: 0,
                CONTEXT: 0,
            }
            previousLineSkipped = False
            processedLines = []

            for lineIndex, line in enumerate(
                hunk["lines"][1:], start=hunk["start"] + 1
            ):
                lineType = line[0]
                lineContent = line[1:]

                if not (startIndex <= lineIndex <= endIndex):
                    if (not reverse and lineType == ADDITION) or (
                        reverse and lineType == DELETION
                    ):
                        previousLineSkipped = True
                        continue

                    elif (not reverse and lineType == DELETION) or (
                        reverse and lineType == ADDITION
                    ):
                        lineType = CONTEXT

                if lineType == NONEWLINE and previousLineSkipped:
                    continue

                processedLines.append(lineType + lineContent)
                counts[lineType] += 1
                previousLineSkipped = False

            # hunks consisting of pure context lines are excluded
            if counts[ADDITION] == 0 and counts[DELETION] == 0:
                continue

            oldCount = counts[CONTEXT] + counts[DELETION]
            newCount = counts[CONTEXT] + counts[ADDITION]
            oldStart = hunk["oldStart"]
            newStart = oldStart + startOffset
            if oldCount == 0:
                newStart += 1
            if newCount == 0:
                newStart -= 1

            startOffset += counts[ADDITION] - counts[DELETION]

            patch.append(
                self.__generateHunkHeader(
                    oldStart, oldCount, newStart, newCount, hunk["heading"]
                )
            )
            patch.extend(processedLines)

        if not patch:
            return ""
        else:
            return "".join(self.__headerLines[:] + patch)
