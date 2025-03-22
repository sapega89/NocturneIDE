# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a label widget showing an animated pixmap.
"""

from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from eric7.EricGui import EricPixmapCache


class EricAnimatedLabel(QLabel):
    """
    Class implementing a label widget showing an animated pixmap.
    """

    def __init__(self, parent=None, *, animationFile="", interval=100):
        """
        Constructor

        @param parent reference to the parent window
        @type QWidget
        @keyparam animationFile path to the file containing the animation data
        @type str
        @keyparam interval interval in milliseconds between animation frames
        @type int
        """
        super().__init__(parent)

        self.__timer = QTimer(self)
        self.__timer.setInterval(interval)
        self.__timer.timeout.connect(self.__animate)

        self.__currentFrame = 0
        self.__frames = 0
        self.__pixmap = None
        self.__pixmapHeight = 0
        self.__animationFile = ""
        self.__animationFileLoaded = False

        self.__loadAnimationFile(animationFile)

    def __loadAnimationFile(self, animationFile):
        """
        Private method to load an animation file.

        @param animationFile path to the file containing the animation data
        @type str
        """
        self.__animationFile = animationFile

        pixmap = EricPixmapCache.getPixmap(animationFile)
        if not pixmap.isNull():
            self.__pixmap = pixmap
            self.__pixmapHeight = pixmap.height()
            self.__frames = pixmap.width() // pixmap.height()
            # assume quadratic animation frames
            self.__animationFileLoaded = True
        else:
            self.__pixmap = QPixmap()
            self.__pixmapHeight = 0
            self.__frames = 0
            self.__animationFileLoaded = False

        self.reset()

    @pyqtSlot()
    def __animate(self):
        """
        Private slot to animate the pixmap.
        """
        if self.__animationFileLoaded:
            self.__currentFrame = (self.__currentFrame + 1) % self.__frames
            super().setPixmap(
                self.__pixmap.copy(
                    self.__currentFrame * self.__pixmapHeight,
                    0,
                    self.__pixmapHeight,
                    self.__pixmapHeight,
                )
            )
        else:
            self.clear()

    @pyqtSlot()
    def reset(self):
        """
        Public slot to reset the animation.
        """
        self.__currentFrame = -1
        self.__animate()

    @pyqtSlot()
    def start(self):
        """
        Public slot to start the animation.
        """
        if self.__animationFileLoaded:
            self.__timer.start()

    @pyqtSlot()
    def stop(self):
        """
        Public slot to stop the animation.
        """
        self.__timer.stop()

    def isActive(self):
        """
        Public method to check, if the animation is active.

        @return flag indicating an active animation
        @rtype bool
        """
        return self.__timer.isActive() and self.__animationFileLoaded

    def setAnimationFile(self, animationFile):
        """
        Public method to set the name of the animation file.

        @param animationFile path to the file containing the animation data
        @type str
        """
        active = self.__timer.isActive()
        self.__timer.stop()
        self.__loadAnimationFile(animationFile)
        if active and self.__animationFileLoaded:
            self.__timer.start()

    def getAnimationFile(self):
        """
        Public method to get the name of the animation file.

        @return path to the file containing the animation data
        @rtype str
        """
        return self.__animationFile

    def isAnimationFileLoaded(self):
        """
        Public method to check, if the animation file was loaded.

        @return flag indicating a successfully loaded animation file
        @rtype bool
        """
        return self.__animationFileLoaded

    def setInterval(self, interval):
        """
        Public method to set the interval between the animated frames.

        @param interval interval in milliseconds between animation frames
        @type int
        """
        self.__timer.setInterval(interval)

    def getInterval(self):
        """
        Public method to get the interval between the animated frames.

        @return interval in milliseconds between animation frames
        @rtype int
        """
        return self.__timer.interval()

    def setPixmap(self, pixmap):
        """
        Public slot to set the pixmap of the label.

        Setting a standard pixmap will stop the animation and set the given
        pixmap without animating it. Thereafter the animation has to be
        restarted with the start() method.

        @param pixmap pixmap to be set
        @type QPixmap
        """
        self.stop()
        super().setPixmap(pixmap)
