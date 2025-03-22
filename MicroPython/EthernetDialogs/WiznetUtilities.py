# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing WIZnet 5x00 related utility functions.
"""


def mpyWiznetInit():
    """
    Function to get the WIZnet 5x00 initialization code for MicroPython.

    @return string containing the code to initialize the WIZnet 5x00 ethernet interface
    @rtype str
    """
    return """def w5x00_init():
    global nic

    try:
        nic
    except NameError:
        nic = None

    if nic is None:
        import network
        from machine import Pin, SPI

        spi = SPI(0, 2_000_000, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        nic = network.WIZNET5K(spi, Pin(17), Pin(20))
"""


def cpyWiznetInit():
    """
    Function to get the WIZnet 5x00 initialization code for CircuitPython.

    @return string containing the code to initialize the WIZnet 5x00 ethernet interface
    @rtype str
    """
    return """def w5x00_init():
    global nic

    try:
        nic
    except NameError:
        nic = None

    if nic is None:
        import board
        import busio
        import digitalio
        from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K

        SPI0_RX = board.GP16
        SPI0_CSn = board.GP17
        SPI0_SCK = board.GP18
        SPI0_TX = board.GP19
        W5x00_RSTn = board.GP20

        ethernetRst = digitalio.DigitalInOut(W5x00_RSTn)
        ethernetRst.direction = digitalio.Direction.OUTPUT

        cs = digitalio.DigitalInOut(SPI0_CSn)
        spi = busio.SPI(SPI0_SCK, MOSI=SPI0_TX, MISO=SPI0_RX)

        nic = WIZNET5K(spi, cs, reset=ethernetRst, is_dhcp=False)
"""
