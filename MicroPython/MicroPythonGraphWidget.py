# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the MicroPython graph widget.
"""

import bisect
import contextlib
import csv
import os
import time

from collections import deque

from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp


class MicroPythonGraphWidget(QWidget):
    """
    Class implementing the MicroPython graph widget.

    @signal dataFlood emitted to indicate, that too much data is received
    """

    dataFlood = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__layout = QHBoxLayout()
        self.__layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.__layout)

        self.__chartView = QChartView(self)
        self.__chartView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.__layout.addWidget(self.__chartView)

        self.__verticalLayout = QVBoxLayout()
        self.__verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.__layout.addLayout(self.__verticalLayout)

        self.__saveButton = QToolButton(self)
        self.__saveButton.setIcon(EricPixmapCache.getIcon("fileSave"))
        self.__saveButton.setToolTip(self.tr("Press to save the raw data"))
        self.__saveButton.clicked.connect(self.on_saveButton_clicked)
        self.__verticalLayout.addWidget(self.__saveButton)
        self.__verticalLayout.setAlignment(
            self.__saveButton, Qt.AlignmentFlag.AlignHCenter
        )

        spacerItem = QSpacerItem(
            20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.__verticalLayout.addItem(spacerItem)

        label = QLabel(self.tr("max. X:"))
        self.__verticalLayout.addWidget(label)
        self.__verticalLayout.setAlignment(label, Qt.AlignmentFlag.AlignHCenter)

        self.__maxX = 100
        self.__maxXSpinBox = QSpinBox()
        self.__maxXSpinBox.setMinimum(100)
        self.__maxXSpinBox.setMaximum(1000)
        self.__maxXSpinBox.setSingleStep(100)
        self.__maxXSpinBox.setToolTip(
            self.tr("Enter the maximum number of data points to be plotted.")
        )
        self.__maxXSpinBox.setValue(self.__maxX)
        self.__maxXSpinBox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.__verticalLayout.addWidget(self.__maxXSpinBox)

        # holds the data to be checked for plotable data
        self.__inputBuffer = []
        # holds the raw data
        self.__rawData = []
        self.__dirty = False

        self.__maxY = 1000
        self.__flooded = False  # flag indicating a data flood

        self.__data = [deque([0] * self.__maxX)]
        self.__series = [QLineSeries()]

        # Y-axis ranges
        self.__yRanges = [1, 5, 10, 25, 50, 100, 250, 500, 1000]

        # setup the chart
        self.__chart = QChart()
        self.__chart.legend().hide()
        self.__chart.addSeries(self.__series[0])

        self.__axisX = QValueAxis()
        self.__axisX.setLabelFormat("time")
        self.__chart.addAxis(self.__axisX, Qt.AlignmentFlag.AlignBottom)
        self.__series[0].attachAxis(self.__axisX)
        self.__axisX.setRange(0, self.__maxX)

        self.__axisY = QValueAxis()
        self.__axisY.setLabelFormat("%d")
        self.__chart.addAxis(self.__axisY, Qt.AlignmentFlag.AlignLeft)
        self.__series[0].attachAxis(self.__axisY)
        self.__axisY.setRange(-self.__maxY, self.__maxY)

        self.__chartView.setChart(self.__chart)
        self.__chartView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.preferencesChanged()

        self.__maxXSpinBox.valueChanged.connect(self.__handleMaxXChanged)

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot to apply changed preferences.
        """
        chartColorTheme = Preferences.getMicroPython("ChartColorTheme")
        if chartColorTheme == -1:
            # automatic selection of light or dark depending on desktop
            # color scheme
            if ericApp().usesDarkPalette():
                self.__chart.setTheme(QChart.ChartTheme.ChartThemeDark)
            else:
                self.__chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        else:
            self.__chart.setTheme(chartColorTheme)

    @pyqtSlot(bytes)
    def processData(self, data):
        """
        Public slot to process the raw data.

        It takes raw bytes, checks the data for a valid tuple of ints or
        floats and adds the data to the graph. If the the length of the bytes
        data is greater than 1024 then a dataFlood signal is emitted to ensure
        eric can take action to remain responsive.

        @param data raw data received from the connected device via the main
            device widget
        @type bytes
        """
        # flooding guard
        if self.__flooded:
            return

        if len(data) > 1024:
            self.__flooded = True
            self.dataFlood.emit()
            return

        # disable the inputs while processing data
        self.__saveButton.setEnabled(False)
        self.__maxXSpinBox.setEnabled(False)

        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        self.__inputBuffer.append(data)

        # check if the data contains a Python tuple containing numbers (int
        # or float) on a single line
        inputBytes = b"".join(self.__inputBuffer)
        lines = inputBytes.splitlines(True)
        for line in lines:
            if not line.endswith(b"\n"):
                # incomplete line (last line); skip it
                break

            line = line.strip()
            if line.startswith(b"(") and line.endswith(b")"):
                # it may be a tuple we are interested in
                rawValues = [val.strip() for val in line[1:-1].split(b",")]
                values = []
                for raw in rawValues:
                    with contextlib.suppress(ValueError):
                        values.append(int(raw))
                        # ok, it is an integer
                        continue
                    try:
                        values.append(float(raw))
                    except ValueError:
                        # it is not an int or float, ignore it
                        continue
                if values:
                    self.__addData(tuple(values))

        self.__inputBuffer = []
        if lines[-1] and not lines[-1].endswith(b"\n"):
            # Append any left over bytes for processing next time data is
            # received.
            self.__inputBuffer.append(lines[-1])

        # re-enable the inputs
        self.__saveButton.setEnabled(True)
        self.__maxXSpinBox.setEnabled(True)

    def __addData(self, values):
        """
        Private method to add a tuple of values to the graph.

        It ensures there are the required number of line series, adds the data
        to the line series and updates the range of the chart so the chart
        displays nicely.

        @param values tuple containing the data to be added
        @type tuple of int or float
        """
        # store incoming data to be able to dump it as CSV upon request
        self.__rawData.append(values)
        self.__dirty = True

        # check number of incoming values and adjust line series accordingly
        if len(values) != len(self.__series):
            valuesLen = len(values)
            seriesLen = len(self.__series)
            if valuesLen > seriesLen:
                # add a new line series
                for _index in range(valuesLen - seriesLen):
                    newSeries = QLineSeries()
                    self.__chart.addSeries(newSeries)
                    newSeries.attachAxis(self.__axisX)
                    newSeries.attachAxis(self.__axisY)
                    self.__series.append(newSeries)
                    self.__data.append(deque([0] * self.__maxX))
            else:
                # remove obsolete line series
                for oldSeries in self.__series[valuesLen:]:
                    self.__chart.removeSeries(oldSeries)
                self.__series = self.__series[:valuesLen]
                self.__data = self.__data[:valuesLen]

        # add the new values to the display and compute the maximum range
        maxRanges = []
        for index, value in enumerate(values):
            self.__data[index].appendleft(value)
            maxRanges.append(
                max([max(self.__data[index]), abs(min(self.__data[index]))])
            )
            if len(self.__data[index]) > self.__maxX:
                self.__data[index].pop()

        # re-scale the y-axis
        maxYRange = max(maxRanges)
        yRange = bisect.bisect_left(self.__yRanges, maxYRange)
        if yRange < len(self.__yRanges):
            self.__maxY = self.__yRanges[yRange]
        elif maxYRange > self.__maxY:
            self.__maxY += self.__maxY
        elif maxYRange < self.__maxY / 2:
            self.__maxY /= 2
        self.__axisY.setRange(-self.__maxY, self.__maxY)

        # ensure that floats are used to label the y-axis if the range is small
        if self.__maxY <= 5:
            self.__axisY.setLabelFormat("%2.2f")
        else:
            self.__axisY.setLabelFormat("%d")

        # update the line series
        for index, series in enumerate(self.__series):
            series.clear()
            xyValues = []
            for x in range(self.__maxX):
                value = self.__data[index][self.__maxX - 1 - x]
                xyValues.append((x, value))
            for xy in xyValues:
                series.append(*xy)

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to save the raw data to a CSV file.
        """
        self.saveData()

    def hasData(self):
        """
        Public method to check, if the chart contains some valid data.

        @return flag indicating valid data
        @rtype bool
        """
        return len(self.__rawData) > 0

    def isDirty(self):
        """
        Public method to check, if the chart contains unsaved data.

        @return flag indicating unsaved data
        @rtype bool
        """
        return self.hasData() and self.__dirty

    def saveData(self):
        """
        Public method to save the dialog's raw data.

        @return flag indicating success
        @rtype bool
        """
        baseDir = (
            Preferences.getMicroPython("MpyWorkspace")
            or Preferences.getMultiProject("Workspace")
            or os.path.expanduser("~")
        )
        dataDir = os.path.join(baseDir, "data_capture")

        if not os.path.exists(dataDir):
            os.makedirs(dataDir)

        # save the raw data as a CSV file
        fileName = "{0}.csv".format(time.strftime("%Y%m%d-%H%M%S"))
        fullPath = os.path.join(dataDir, fileName)
        try:
            with open(fullPath, "w") as csvFile:
                csvWriter = csv.writer(csvFile)
                csvWriter.writerows(self.__rawData)

            self.__dirty = False
            return True
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Save Chart Data"),
                self.tr(
                    """<p>The chart data could not be saved into file"""
                    """ <b>{0}</b>.</p><p>Reason: {1}</p>"""
                ).format(fullPath, str(err)),
            )
            return False

    @pyqtSlot(int)
    def __handleMaxXChanged(self, value):
        """
        Private slot handling a change of the max. X spin box.

        @param value value of the spin box
        @type int
        """
        delta = value - self.__maxX
        if delta == 0:
            # nothing to change
            return
        elif delta > 0:
            # range must be increased
            for deq in self.__data:
                deq.extend([0] * delta)
        else:
            # range must be decreased
            data = []
            for deq in self.__data:
                data.append(deque(list(deq)[:value]))
            self.__data = data

        self.__maxX = value
        self.__axisX.setRange(0, self.__maxX)
