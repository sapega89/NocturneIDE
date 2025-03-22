# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a zoom widget for the status bar.
"""

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QWidget

from .Ui_EricZoomWidget import Ui_EricZoomWidget


class EricZoomWidget(QWidget, Ui_EricZoomWidget):
    """
    Class implementing a zoom widget for the status bar.

    @signal valueChanged(value) emitted to indicate the new zoom value (int)
    """

    valueChanged = pyqtSignal(int)

    def __init__(self, outPix, inPix, resetPix, parent=None):
        """
        Constructor

        @param outPix pixmap for the zoom out button
        @type QPixmap
        @param inPix pixmap for the zoom in button
        @type QPixmap
        @param resetPix pixmap for the zoom reset button
        @type QPixmap
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.zoomOutLabel.setPixmap(outPix.scaled(16, 16))
        self.zoomInLabel.setPixmap(inPix.scaled(16, 16))
        self.zoomResetLabel.setPixmap(resetPix.scaled(16, 16))

        self.zoomOutLabel.clicked.connect(self.__zoomOut)
        self.zoomInLabel.clicked.connect(self.__zoomIn)
        self.zoomResetLabel.clicked.connect(self.__zoomReset)

        self.slider.valueChanged.connect(self._sliderValueChanged)

        self.__default = 0
        self.__percent = False

        # mapped slider
        self.__mapped = False
        self.__mapping = []

        self.__setValueLabelWidth()

    @pyqtSlot(int)
    def on_slider_sliderMoved(self, value):
        """
        Private slot to handle changes of the zoom value.

        @param value value of the slider
        @type int
        """
        if self.__mapped:
            self.valueChanged.emit(self.__mapping[value])
        else:
            self.valueChanged.emit(value)

    def setValue(self, value):
        """
        Public slot to set the value.

        @param value new zoom value
        @type int
        """
        self.slider.setValue(self.__indexForValue(value))

    def value(self):
        """
        Public method to get the current value.

        @return current zoom value
        @rtype int
        """
        if self.__mapped:
            return self.__mapping[self.slider.value()]
        else:
            return self.slider.value()

    def setMinimum(self, minimum):
        """
        Public method to set the minimum value.

        @param minimum new minimum value
        @type int
        """
        if not self.__mapped:
            self.slider.setMinimum(minimum)
            self.__setValueLabelWidth()

    def minimum(self):
        """
        Public method to get the minimum value.

        @return minimum value
        @rtype int
        """
        if self.__mapped:
            return self.__mapping[0]
        else:
            return self.slider.minimum()

    def setMaximum(self, maximum):
        """
        Public method to set the maximum value.

        @param maximum new maximum value
        @type int
        """
        if not self.__mapped:
            self.slider.setMaximum(maximum)
            self.__setValueLabelWidth()

    def maximum(self):
        """
        Public method to get the maximum value.

        @return maximum value
        @rtype int
        """
        if self.__mapped:
            return self.__mapping[-1]
        else:
            return self.slider.maximum()

    def setSingleStep(self, value):
        """
        Public method to set the single step value.

        @param value value for the single step
        @type int
        """
        self.slider.setSingleStep(value)

    def singleStep(self):
        """
        Public method to get the single step value.

        @return single step value
        @rtype int
        """
        return self.slider.singleStep()

    def setPageStep(self, value):
        """
        Public method to set the page step value.

        @param value page step value
        @type int
        """
        self.slider.setPageStep(value)

    def pageStep(self):
        """
        Public method to get the page step value.

        @return page step value
        @rtype int
        """
        return self.slider.pageStep()

    def setDefault(self, value):
        """
        Public method to set the default zoom value.

        @param value default zoom value
        @type int
        """
        self.__default = self.__indexForValue(value)

    def default(self):
        """
        Public method to get the default zoom value.

        @return default zoom value
        @rtype int
        """
        if self.__mapped:
            return self.__mapping[self.__default]
        else:
            return self.__default

    def setPercent(self, on):
        """
        Public method to set the percent mode of the widget.

        @param on flag indicating percent mode
        @type bool
        """
        self.__percent = on
        self.__setValueLabelWidth()

    def isPercent(self):
        """
        Public method to get the percent mode.

        @return flag indicating percent mode
        @rtype bool
        """
        return self.__percent

    def setMapping(self, mapping, default, percent=True):
        """
        Public method to set a zoom level mapping.

        When zoom level mapping is activated, the slider covers
        values from 0 to the max. index of the mapping list. The
        default value is the value of the default zoom level. If
        percent is given, the zoom level is shown as a percent value.

        @param mapping list of mapping values
        @type list of int
        @param default index of the default value
        @type int
        @param percent flag indicating to show zoom value in percent
        @type bool
        """
        if mapping:
            self.__mapping = mapping[:]
            self.__mapped = True
            self.slider.setMinimum(0)
            self.slider.setMaximum(len(self.__mapping) - 1)
            self.__default = self.__indexForValue(default)
            self.__percent = percent
            self.slider.setValue(self.__default)
        else:
            # switch back to default values
            self.__mapping = []
            self.__mapped = False
            self.slider.setMinimum(-10)
            self.slider.setMaximum(20)
            self.__default = 0
            self.__percent = False
            self.slider.setValue(0)
        self.__setValueLabelWidth()

    def mapping(self):
        """
        Public method to get the current mapping.

        @return tuple of the mapping and the default index
        @rtype tuple of (list of integer, integer)
        """
        return self.__mapping[:], self.__default

    def isMapped(self):
        """
        Public method to check for a mapped zoom widget.

        @return flag indicating a mapped zoom widget
        @rtype bool
        """
        return self.__mapped

    def __zoomReset(self):
        """
        Private slot to reset the value.
        """
        self.slider.setValue(self.__default)
        self.valueChanged.emit(self.value())

    def __zoomOut(self):
        """
        Private slot to zoom out one step.
        """
        self.slider.setValue(self.slider.value() - self.slider.singleStep())
        self.valueChanged.emit(self.value())

    def __zoomIn(self):
        """
        Private slot to zoom in one step.
        """
        self.slider.setValue(self.slider.value() + self.slider.singleStep())
        self.valueChanged.emit(self.value())

    def _sliderValueChanged(self, value):
        """
        Protected slot to handle changes of the slider value.

        @param value slider value
        @type int
        """
        val = self.__mapping[value] if self.__mapped else value
        fmtStr = "{0}%" if self.__percent else "{0}"
        self.valueLabel.setText(fmtStr.format(val))
        self.valueChanged.emit(val)

    def __setValueLabelWidth(self):
        """
        Private slot to determine the width of the zoom value label.
        """
        labelLen = (
            max(len(str(v)) for v in self.__mapping)
            if self.__mapped
            else max(len(str(self.slider.maximum())), len(str(self.slider.minimum())))
        )
        fmtStr = "{0}%" if self.__percent else "{0}"
        label = fmtStr.format("0" * labelLen)
        width = self.valueLabel.fontMetrics().horizontalAdvance(label)
        self.valueLabel.setMinimumWidth(width)
        self.valueLabel.setMaximumWidth(width)

    def __indexForValue(self, value):
        """
        Private method to get the nearest index for a given value.

        @param value value to get the index for
        @type int
        @return index into the mapping list or the unchanged value,
            if mapping is not set
        @rtype int
        """
        if self.__mapped:
            try:
                index = self.__mapping.index(value)
            except ValueError:
                for index in range(len(self.__mapping)):
                    if value <= self.__mapping[index]:
                        break
        else:
            index = value
        return index
