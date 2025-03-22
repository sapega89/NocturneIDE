# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containing the device interface modules and device specific dialogs.
"""

import contextlib
import importlib
import logging

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtSerialPort import QSerialPortInfo

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities

from .DeviceBase import BaseDevice

SupportedBoards = {
    "bbc_microbit": {
        "ids": ((0x0D28, 0x0204),),  # micro:bit
        "description": "BBC micro:bit",
        "icon": "microbitDevice",
        "port_description": "BBC micro:bit CMSIS-DAP",
        "module": ".MicrobitDevices",
    },
    "calliope": {
        "ids": ((0x0D28, 0x0204),),  # Calliope mini
        "description": "Calliope mini",
        "icon": "calliope_mini",
        "port_description": "DAPLink CMSIS-DAP",
        "module": ".MicrobitDevices",
    },
    "circuitpython": {
        "ids": (
            (0x0456, 0x003C),  # Analog Devices, Inc. MAX32690 APARD
            (0x0456, 0x003D),  # Analog Devices, Inc. MAX32690 EvKit
            (0x0483, 0x572A),  # STMicroelectronics NUCLEO-F446RE - CPy
            (0x04D8, 0xE799),  # Cytron Maker Zero SAMD21
            (0x04D8, 0xEA2A),  # BHDynamics DynaLoRa_USB
            (0x04D8, 0xEAD1),  # BH Dynamics DynOSSAT-EDU-EPS-v1.0
            (0x04D8, 0xEAD2),  # BH Dynamics DynOSSAT-EDU-OBC-v1.0
            (0x04D8, 0xEC44),  # maholli PyCubed
            (0x04D8, 0xEC63),  # Kevin Neubauer CircuitBrains Basic
            (0x04D8, 0xEC64),  # Kevin Neubauer CircuitBrains Deluxe
            (0x04D8, 0xEC72),  # XinaBox CC03
            (0x04D8, 0xEC75),  # XinaBox CS11
            (0x04D8, 0xED5F),  # Itaca Innovation uChip CircuitPython
            (0x04D8, 0xED94),  # maholli kicksat-sprite
            (0x04D8, 0xEDB3),  # Capable Robot Programmable USB Hub
            (0x04D8, 0xEDBE),  # maholli SAM32
            (0x04D8, 0xEE8C),  # J&J Studios LLC datum-Distance
            (0x04D8, 0xEE8D),  # J&J Studios LLC datum-IMU
            (0x04D8, 0xEE8E),  # J&J Studios LLC datum-Light
            (0x04D8, 0xEE8F),  # J&J Studios LLC datum-Weather
            (0x04D8, 0xEF67),  # senseBox MCU
            (0x04E9, 0x80FF),  # PCTEL WSC-1450
            (0x054C, 0x0BC2),  # Sony Spresense
            (0x1209, 0x0001),  # Solder Party ESP32-P4 Stamp XL
            (0x1209, 0x2017),  # Benjamin Shockley Mini SAM M4
            (0x1209, 0x2023),  # Lilygo T-Display
            (0x1209, 0x2031),  # Czech maker ES3ink
            (0x1209, 0x3141),  # CrumpSpace CrumpS2
            (0x1209, 0x3252),  # Targett Module Clip w/Wroom
            (0x1209, 0x3253),  # Targett Module Clip w/Wrover
            (0x1209, 0x4203),  # 42. Keebs Frood
            (0x1209, 0x4D43),  # Robotics Masters Robo HAT MM1 M4
            (0x1209, 0x4DDD),  # ODT CP Sapling
            (0x1209, 0x4DDE),  # ODT CP Sapling M0 w/ SPI Flash
            (0x1209, 0x4DDF),  # ODT CP Sapling Rev B
            (0x1209, 0x4DF0),  # Oak Dev Tech Pixelwing ESP32S2
            (0x1209, 0x4DF1),  # Oak Dev Tech BREAD2040
            (0x1209, 0x4DF2),  # Oak Dev Tech CAST AWAY RP2040
            (0x1209, 0x4DF6),  # Oak Dev Tech RPGA Feather
            (0x1209, 0x5687),  # Bradán Lane STUDIO Coin M0
            (0x1209, 0x5A52),  # ZRichard RP2.65-F
            (0x1209, 0x5BF0),  # Foosn Fomu
            (0x1209, 0x6036),  # Weekin WK-50
            (0x1209, 0x7150),  # Electronic Cats Hunter Cat NFC
            (0x1209, 0x7382),  # Invector Labs AB iLabs Challenger 840
            (0x1209, 0x805A),  # Electronic Cats BastBLE
            (0x1209, 0x8CAE),  # takayoshiotake Octave RP2040
            (0x1209, 0x9000),  # Hack Club Sprig
            (0x1209, 0xA182),  # Solder Party RP2040 Stamp
            (0x1209, 0xA183),  # Solder Party RP2350 Stamp
            (0x1209, 0xA184),  # Solder Party RP2350 Stamp XL
            (0x1209, 0xADF0),  # ICBbuy SuperMini NRF52840
            (0x1209, 0xB182),  # Solder Party BBQ20 Keyboard
            (0x1209, 0xBAB0),  # Electronic Cats Bast WiFi
            (0x1209, 0xBAB1),  # Electronic Cats Meow Meow
            (0x1209, 0xBAB2),  # Electronic Cats CatWAN USBStick
            (0x1209, 0xBAB3),  # Electronic Cats Bast Pro Mini M0
            (0x1209, 0xBAB6),  # Electronic Cats Escornabot Makech
            (0x1209, 0xBAB8),  # Electronic Cats NFC Copy Cat
            (0x1209, 0xC051),  # Betrusted Simmel
            (0x1209, 0xCB65),  # 0xCB Gemini
            (0x1209, 0xCB74),  # 0xCB Helios
            (0x1209, 0xD10D),  # Diodes Delight Piunora
            (0x1209, 0xD1B5),  # Radomir Dopieralski PewPew LCD
            (0x1209, 0xD1B6),  # Radomir Dopieralski uGame22
            (0x1209, 0xE3E3),  # StackRduino M0 PRO
            (0x1209, 0xEF00),  # 2231puppy E-Fidget
            (0x1209, 0xF123),  # Electrolama minik
            (0x1209, 0xF500),  # Silicognition LLC M4-Shim
            (0x1209, 0xF502),  # Silicognition LLC RP2040-Shim
            (0x1209, 0xFF40),  # RF.Guru RP2040
            (0x1354, 0x4004),  # FACTS Engineering LLC P1AM-200 CircuitPython
            (0x16D0, 0x07F2),  # Autosport Labs ESP32-CAN-X2
            (0x16D0, 0x08C6),  # Pimoroni Keybow 2040
            (0x16D0, 0x08C7),  # Pimoroni Tiny 2040 (8MB)
            (0x16D0, 0x08C8),  # Pimoroni PicoSystem
            (0x16D0, 0x10ED),  # Mechwild PillBug
            (0x1915, 0xB001),  # Makerdiary Pitaya Go
            (0x192F, 0xB1B2),  # WarmBit BluePixel nRF52840
            (0x1B4F, 0x0015),  # SparkFun RedBoard Turbo Board
            (0x1B4F, 0x0016),  # SparkFun SAMD51 Thing+
            (0x1B4F, 0x0017),  # SparkFun LUMIDrive Board
            (0x1B4F, 0x0020),  # SparkFun MicroMod SAMD51 Processor
            (0x1B4F, 0x0021),  # SparkFun MicroMod nRF52840 Processor
            (0x1B4F, 0x0024),  # SparkFun MicroMod RP2040 Processor
            (0x1B4F, 0x0025),  # SparkFun Thing Plus RP2040
            (0x1B4F, 0x0026),  # SparkFun Pro Micro RP2040
            (0x1B4F, 0x0027),  # SparkFun STM32 MicroMod Processor
            (0x1B4F, 0x0028),  # SparkFun Thing Plus - STM32
            (0x1B4F, 0x002E),  # PJRC/Sparkfun Teensy MicroMod
            (0x1B4F, 0x0038),  # SparkFun Thing Plus RP2350
            (0x1B4F, 0x0039),  # SparkFun Pro Micro RP2350
            (0x1B4F, 0x5289),  # SparkFun SFE_nRF52840_Mini
            (0x1B4F, 0x8D22),  # SparkFun SAMD21 Mini Breakout
            (0x1B4F, 0x8D23),  # SparkFun SAMD21 Dev Breakout
            (0x1B4F, 0x8D24),  # SparkFun Qwiic Micro
            (0x1D50, 0x60E8),  # Radomir Dopieralski PewPew M4
            (0x1D50, 0x6152),  # nrf52.jpconstantineau.com BlueMicro833
            (0x1D50, 0x6153),
            # JPConstantineau PyKey18
            # JPConstantineau PyKey44
            # JPConstantineau PyKey60
            # JPConstantineau PyKey87
            (0x1D50, 0x6154),  # JPConstantineau EncoderPad RP2040
            (0x1D50, 0x6161),  # nrf52.jpconstantineau.com BlueMicro840
            (0x2019, 0x7103),  # Benjamin Shockley Fig Pi
            (0x2341, 0x056B),  # Arduino Nano ESP32
            (0x2341, 0x8053),  # Arduino MKR1300
            (0x2341, 0x8057),  # Arduino Nano 33 IoT
            (0x2341, 0x805A),  # Arduino Arduino_Nano_33_BLE
            (0x2341, 0x824D),  # Arduino Zero
            (0x2786, 0x9207),  # Switch Sc. BLE-SS dev board Multi Sensor
            (0x2786, 0x920D),  # Switch Sc. SSCI ISP1807 Dev Board
            (0x2786, 0x920F),  # Switch Sc. SSCI ISP1807 Micro Board
            (0x2886, 0x002F),  # Seeed Seeeduino XIAO
            (0x2886, 0x0042),  # Seeed Seeeduino XIAO RP2040
            (0x2886, 0x0045),  # Seeed XIAO nRF52840 Sense
            (0x2886, 0x0058),  # Seeed Seeeduino XIAO RP2350
            (0x2886, 0x802D),  # Seeed Seeeduino Wio Terminal
            (0x2886, 0x802F),  # Seeed Seeeduino XIAO KB
            (0x2886, 0x8056),  # Seeed Studio Seeed Xiao ESP32-S3 Sense
            (0x2886, 0xF001),  # Makerdiary nRF52840 M.2 Developer Kit
            (0x2886, 0xF002),  # Makerdiary M60 Keyboard
            (0x2886, 0xF003),  # Makerdiary nRF52840 Connect Kit
            (0x2886, 0xF004),  # Makerdiary iMX RT1011 Nano Kit
            (0x2B04, 0xC00C),  # Particle Argon
            (0x2B04, 0xC00D),  # Particle Boron
            (0x2B04, 0xC00E),  # Particle Xenon
            (0x2E8A, 0x000B),  # Raspberry Pi Pico 2
            (0x2E8A, 0x1000),  # Cytron Maker Pi RP2040
            (0x2E8A, 0x1002),  # Pimoroni Pico LiPo (4MB)
            (0x2E8A, 0x1003),  # Pimoroni Pico LiPo (16MB)
            (0x2E8A, 0x1005),  # Melopero Shake RP2040
            (0x2E8A, 0x1006),  # Invector Labs Challenger RP2040 WiFi
            (0x2E8A, 0x1008),  # Pimoroni PGA2040
            (0x2E8A, 0x1009),  # Pimoroni Interstate 75
            (0x2E8A, 0x100A),  # Pimoroni Plasma 2040
            (0x2E8A, 0x100B),  # Invector Labs Challenger RP2040 LTE
            (0x2E8A, 0x100D),  # Invector Labs Challenger NB RP2040 WiFi
            (0x2E8A, 0x100E),  # Raspberry Pi Zero
            (0x2E8A, 0x100F),  # Cytron Maker Nano RP2040
            (0x2E8A, 0x1012),  # Raspberry Pi Compute Module 4 IO Board
            (0x2E8A, 0x1013),  # Raspberry Pi 4B
            (0x2E8A, 0x1014),  # Raspberry Pi Compute Module 4
            (0x2E8A, 0x1015),  # Raspberry Pi Zero 2W
            (0x2E8A, 0x1016),  # Pimoroni Tiny 2040 (2MB)
            (0x2E8A, 0x1018),  # Pimoroni Inky Frame 5.7
            (0x2E8A, 0x1019),  # Pimoroni Motor 2040
            (0x2E8A, 0x101A),  # Pimoroni Servo 2040
            (0x2E8A, 0x101B),  # Pimoroni Badger 2040
            (0x2E8A, 0x101E),  # Raspberry Pi Zero W
            (0x2E8A, 0x101F),  # Waveshare Electronics RP2040-Zero
            (0x2E8A, 0x1020),
            # Waveshare Electronics RP2040-Plus (16MB)
            # Waveshare Electronics RP2040-Plus (4MB)
            (0x2E8A, 0x1021),  # Waveshare Electronics Waveshare RP2040-LCD-0.96
            (0x2E8A, 0x1023),  # Invector Labs Challenger RP2040 LoRa
            (0x2E8A, 0x1026),  # ELECFREAKS Pico:ed
            (0x2E8A, 0x1027),  # WIZnet W5100S-EVB-Pico
            (0x2E8A, 0x1029),  # WIZnet W5500-EVB-Pico
            (0x2E8A, 0x102C),  # Invector Labs Challenger RP2040 WiFi/BLE
            (0x2E8A, 0x102D),  # Invector Labs Challenger RP2040 SD/RTC
            (0x2E8A, 0x102E),  # VCC-GND Studio YD-RP2040
            (0x2E8A, 0x1032),  # Invector Labs Challenger RP2040 SubGHz
            (0x2E8A, 0x1039),  # Waveshare Electronics Waveshare RP2040-LCD-1.28
            (0x2E8A, 0x103A),  # Waveshare Electronics RP2040-One
            (0x2E8A, 0x1043),  # NEWSAN ARCHI
            (0x2E8A, 0x1048),  # nullbits Bit-C PRO
            (0x2E8A, 0x104A),  # Boardsource BLOK
            (0x2E8A, 0x104B),  # Datanoise PicoADK
            (0x2E8A, 0x104C),  # Raspberry Pi COSMO-Pico
            (0x2E8A, 0x104F),  # Pimoroni Badger 2040 W
            (0x2E8A, 0x1056),  # Waveshare Electronics RP2040-GEEK
            (0x2E8A, 0x1057),  # Waveshare Electronics Waveshare RP2040-TOUCH-LCD-1.28
            (0x2E8A, 0x1058),  # Pimoroni Plasma 2040 W
            (0x2E8A, 0x1059),  # Pimoroni Pico DV Demo Base for Pico
            (0x2E8A, 0x105A),  # Pimoroni Pico DV Demo Base for Pico W
            (0x2E8A, 0x105E),  # Breadstick Innovations Raspberry Breadstick
            (0x2E8A, 0x1060),  # splitkb.com Liatris
            (0x2E8A, 0x1063),  # Pajenicko s.r.o. PicoPad
            (0x2E8A, 0x1067),  # WisdPi Ardu2040M
            (0x2E8A, 0x106A),  # WisdPi Tiny RP2040
            (0x2E8A, 0x1071),  # Cytron Maker Uno RP2040
            (0x2E8A, 0x1072),  # Maple Computing Elite-Pi
            (0x2E8A, 0x1073),  # Bradán Lane STUDIO Explorer Badge
            (0x2E8A, 0x1074),  # Cytron EDU PICO for Pico W
            (0x2E8A, 0x107D),  # HEIA-FR Picomo V2
            (0x2E8A, 0x1081),  # Pimoroni Inky Frame 7.3
            (0x2E8A, 0x1083),  # Waveshare Electronics RP2040-PiZero
            (0x2E8A, 0x1084),  # Waveshare Electronics RP2040-Tiny
            (0x2E8A, 0x1093),  # Cytron IRIV IO Controller
            (0x2E8A, 0x1096),  # Cytron MOTION 2350 Pro
            (0x2E8A, 0x109A),  # Invector Labs Challenger+ RP2350 WiFi6/BLE5
            (0x2E8A, 0x109B),  # Invector Labs Challenger+ RP2350 BConnect
            (0x2E8A, 0x109E),  # WIZnet W5100S-EVB-Pico2
            (0x2E8A, 0x10A2),  # Pimoroni Tiny FX
            (0x2E8A, 0x10A3),  # Pimoroni Pico Plus 2
            (0x2E8A, 0x10A4),  # Pimoroni Tiny 2350
            (0x2E8A, 0x10A5),  # Pimoroni Plasma 2350
            (0x2E8A, 0x10A6),  # Pimoroni PGA2350
            (0x2E8A, 0x10AE),  # Datanoise PicoADK V2
            (0x2E8A, 0x10B0),  # Waveshare Electronics RP2350-Zero
            (0x2E8A, 0x10B1),  # Waveshare Electronics RP2350-Plus
            (0x2E8A, 0x10B2),  # Waveshare Electronics RP2350-Tiny
            (0x2E8A, 0x10B3),  # Waveshare Electronics Waveshare RP2350-LCD-1.28
            (0x2E8A, 0x10B4),  # Waveshare Electronics Waveshare RP2350-TOUCH-LCD-1.28
            (0x2E8A, 0x10B5),  # Waveshare Electronics RP2350-One
            (0x2E8A, 0x10B6),  # Waveshare Electronics RP2350-GEEK
            (0x2E8A, 0x10B7),  # Waveshare Electronics Waveshare RP2350-LCD-0.96
            (0x2E8A, 0x10BD),  # Pimoroni Pico Plus 2 W
            (0x2E8A, 0x10BF),  # Pimoroni Plasma 2350 W
            (0x2E8A, 0x10C1),  # Music Thing Modular Workshop Computer
            (0x2E8A, 0x10C4),  # HEIA-FR Picomo V3
            (0x303A, 0x7001),  # Espressif ESP32-S2-HMI-DevKit-1
            (0x303A, 0x7003),
            # Espressif ESP32-S3-DevKitC-1
            # Espressif ESP32-S3-DevKitC-1-N16
            # Espressif ESP32-S3-DevKitC-1-N32R8
            # Espressif ESP32-S3-DevKitC-1-N8
            # Espressif ESP32-S3-DevKitC-1-N8R2
            # Espressif ESP32-S3-DevKitC-1-N8R8
            # Espressif ESP32-S3-DevKitC-1-nopsram
            (0x303A, 0x7005),  # Espressif ESP32-S3-Box-2.5
            (0x303A, 0x7007),  # Espressif ESP32-S3-DevKitM-1-N8
            (0x303A, 0x7009),
            # Espressif ESP32-S2-DevKitC-1-N4
            # Espressif ESP32-S2-DevKitC-1-N4R2
            # Espressif ESP32-S2-DevKitC-1-N8R2
            (0x303A, 0x700B),  # Espressif ESP32-S3-USB-OTG-N8
            (0x303A, 0x700D),  # Espressif ESP32-S3-Box-Lite
            (0x303A, 0x700F),  # Espressif ESP32-S3-EYE
            (0x303A, 0x7011),  # Espressif ESP32-S3-EV-LCD-Board_v1.5
            (0x303A, 0x7013),  # Espressif ESP32-P4-Function-EV
            (0x303A, 0x8002),  # UnexpectedMaker TinyS2
            (0x303A, 0x8007),  # LILYGO TTGO T8 ESP32-S2
            (0x303A, 0x800D),  # Gravitech Cucumber RS
            (0x303A, 0x80A1),  # Gravitech Cucumber R
            (0x303A, 0x80A4),  # Gravitech Cucumber M
            (0x303A, 0x80A7),  # Gravitech Cucumber MS
            (0x303A, 0x80AA),  # Espressif Franzininho WIFI w/Wroom
            (0x303A, 0x80AD),  # Espressif Franzininho WIFI w/Wrover
            (0x303A, 0x80AF),  # Artisense Reference Design RD00
            (0x303A, 0x80B2),  # Muselab nanoESP32-S2  w/Wrover
            (0x303A, 0x80B5),  # UnexpectedMaker FeatherS2 Neo
            (0x303A, 0x80B7),  # MORPHEANS MORPHESP-240
            (0x303A, 0x80C3),  # Lolin S2 Mini
            (0x303A, 0x80C6),  # Lolin S2 Pico
            (0x303A, 0x80C8),  # BrainBoardz Neuron
            (0x303A, 0x80D1),  # UnexpectedMaker TinyS3
            (0x303A, 0x80D4),  # UnexpectedMaker ProS3
            (0x303A, 0x80D7),  # UnexpectedMaker FeatherS3
            (0x303A, 0x80D9),  # FutureKeys HexKy_S2
            (0x303A, 0x80DD),  # CircuitArt ZeroS3
            (0x303A, 0x80E0),  # BananaPi BPI-Leaf-S3
            (0x303A, 0x80E6),  # BananaPi BPI-Bit-S2
            (0x303A, 0x80E8),  # HiiBot IoTs2
            (0x303A, 0x80EA),  # LILYGO TTGO T8 ESP32-S2-WROOM
            (0x303A, 0x80ED),  # LILYGO TTGO T8 ESP32-S2
            (0x303A, 0x80F9),  # Cytron Maker Feather AIoT S3
            (0x303A, 0x80FC),  # Espressif MixGo CE
            (0x303A, 0x80FD),  # Espressif MixGo CE
            (0x303A, 0x810A),  # Waveshare Electronics ESP32-S2-Pico
            (0x303A, 0x810C),  # Waveshare Electronics ESP32-S2-Pico-LCD
            (0x303A, 0x8111),  # Smart Bee Designs Bee-S3
            (0x303A, 0x8114),  # Smart Bee Designs Bee-Motion-S3
            (0x303A, 0x8117),  # WEMOS LOLIN S3 16MB Flash 8MB PSRAM
            (0x303A, 0x811A),  # M5Stack Core S3
            (0x303A, 0x8120),  # M5Stack AtomS3
            (0x303A, 0x812C),  # BananaPi BPI-PicoW-S3
            (0x303A, 0x813F),  # LILYGO T-Display S3
            (0x303A, 0x8142),  # Turkish Technology Team Foundation Deneyap Mini
            (0x303A, 0x8145),  # Turkish Technology Team Foundation Deneyap Mini v2
            (0x303A, 0x8148),  # Turkish Technology Team Foundation Deneyap Kart 1A v2
            (0x303A, 0x8151),  # LILYGO TEMBED ESP32S3
            (0x303A, 0x815D),  # Smart Bee Designs Bee-Data-Logger
            (0x303A, 0x815F),  # M5Stack AtomS3 Lite
            (0x303A, 0x8162),  # WEMOS LOLIN S3 PRO 16MB Flash 8MB PSRAM
            (0x303A, 0x8166),  # VCC-GND YD-ESP32-S3
            (0x303A, 0x8168),  # WEMOS LOLIN S3 MINI 4MB Flash 2MB PSRAM
            (0x303A, 0x816B),  # M5STACK M5Stack StampS3 - CircuitPython
            (0x303A, 0x817A),  # UnexpectedMaker NanoS3
            (0x303A, 0x817D),  # UnexpectedMaker BlizzardS3
            (0x303A, 0x8180),  # UnexpectedMaker BLING!
            (0x303A, 0x8187),  # M5Stack AtomS3U
            (0x303A, 0x81A3),  # Waveshare Electronics ESP32-S3-Pico
            (0x303A, 0x81AA),  # MakerM0 MagiClick S3 n4r2
            (0x303A, 0x81B1),  # UnexpectedMaker TinyWATCH S3
            (0x303A, 0x81B4),  # Waveshare Electronics Waveshare ESP32-S3-Zero
            (0x303A, 0x81B6),  # LILYGO T-Deck (Plus)
            (0x303A, 0x81B9),  # Espressif senseBox MCU-S2 ESP32S2
            (0x303A, 0x81BF),
            # MakerFabs MakerFabs-ESP32-S3-Parallel-TFT-With-Touch-7inch
            (0x303A, 0x81CF),  # Flipper Devices Inc. Flipper Zero Wi-Fi Dev
            (0x303A, 0x81D0),  # Double Take Labs COLUMBIA-DSL-SENSOR-BOARD-V1
            (0x303A, 0x81DA),  # M5STACK M5Stack Cardputer - CircuitPython
            (0x303A, 0x81DD),  # M5Stack M5stack - Dial
            (0x303A, 0x81EA),  # Waveshare Electronics ESP32-S3-GEEK
            (0x303A, 0x81F8),  # Waveshare Electronics ESP32-S3-Tiny
            (0x303A, 0x81FC),  # UnexpectedMaker FeatherS3 Neo
            (0x303A, 0x81FF),  # UnexpectedMaker RGB Touch Mini
            (0x303A, 0x8204),  # ThingPulse Pendrive S3
            (0x303A, 0x8211),  # LILYGO T-Display S3 Pro
            (0x303A, 0x821C),  # LILYGO T-Watch-S3
            (0x303A, 0x8225),  # UnexpectedMaker OMGS3
            (0x303A, 0x8244),  # Fablab Barcelona Barduino 4.0.2
            (0x303A, 0x826E),  # Waveshare Electronics Waveshare ESP32-S3-Matrix
            (0x303A, 0x82A7),  # Waveshare Electronics ESP32-S3-ETH
            (0x30A4, 0x0002),  # Blues Inc. Swan R5
            (0x3171, 0x0101),  # 8086.net Commander
            (0x3171, 0x010C),  # 8086.net USB Interposer
            (0x3171, 0x010D),  # 8086.net RP2040 Interfacer
            (0x31E2, 0x2001),  # BDMICRO LLC VINA-D21
            (0x31E2, 0x2011),  # BDMICRO LLC VINA-D51
            (0x31E2, 0x2021),  # BDMICRO LLC VINA-D51
            (0x32BD, 0x3001),  # Alorium Tech. AloriumTech Evo M51
            (0x3343, 0x83CF),  # DFRobot Firebeetle 2 ESP32-S3
            (0x4097, 0x0001),  # TG-Boards Datalore IP M4
            (0x612B, 0x80A7),  # Ai-Thinker ESP 12k NodeMCU
            # do not overwrite this entry
            (0x239A, None),  # Any Adafruit Boards
        ),
        "description": "CircuitPython",
        "icon": "circuitPythonDevice",
        "port_description": "",
        "module": ".CircuitPythonDevices",
    },
    "esp": {
        "ids": (
            (0x0403, 0x6001),  # M5Stack ESP32 device"),
            (0x0403, 0x6001),  # FT232/FT245 (XinaBox CW01, CW02)
            (0x0403, 0x6010),  # FT2232C/D/L/HL/Q (ESP-WROVER-KIT)
            (0x0403, 0x6011),  # FT4232
            (0x0403, 0x6014),  # FT232H
            (0x0403, 0x6015),  # Sparkfun ESP32
            (0x0403, 0x601C),  # FT4222H
            (0x10C4, 0xEA60),  # CP210x
            (0x1A86, 0x55D4),  # CH343
            (0x1A86, 0x7523),  # HL-340, CH340
            (0x2341, 0x056B),  # Arduino Nano ESP32
            (0x303A, 0x0002),  # ESP32-S2
            (0x303A, 0x1001),  # USB JTAG serial debug unit,
            (0x303A, 0x4001),  # Espressif Device
            (0x303A, 0x80D1),  # UnexpectedMaker TinyS3
            (0x303A, 0x80D4),  # UnexpectedMaker ProS3
            (0x303A, 0x80D7),  # UnexpectedMaker FeatherS3
            (0x303A, 0x817A),  # UnexpectedMaker NanoS3
            (0x303A, 0x81B1),  # UnexpectedMaker TinyWATCH S3
            (0x303A, 0x81FC),  # UnexpectedMaker FeatherS3 Neo
            (0x303A, 0x81FF),  # UnexpectedMaker RGB Touch Mini
            (0x303A, 0x8225),  # UnexpectedMaker OMGS3
        ),
        "description": "ESP32, ESP8266",
        "icon": "esp32Device",
        "port_description": "",
        "module": ".EspDevices",
    },
    "generic": {
        # only manually configured devices use this
        "ids": ((0xF055, 0x9802),),  # Board in FS mode
        "description": QCoreApplication.translate(
            "MicroPythonDevice", "Generic MicroPython Board"
        ),
        "icon": "micropython48",
        "port_description": "Board",
        "module": ".GenericMicroPythonDevices",
    },
    "pyboard": {
        "ids": (
            (0x2341, 0x045F),  # Arduino Nicla Vision
            (0x2341, 0x055B),  # Arduino Portenta H7
            (0x2341, 0x0566),  # Arduino GIGA R1 WiFi
            (0xF055, 0x9800),  # Pyboard in CDC+MSC mode
            (0xF055, 0x9801),  # Pyboard in CDC+HID mode
            (0xF055, 0x9802),  # Pyboard in CDC mode
            (0xF055, 0x9803),  # Pyboard in MSC mode
            (0xF055, 0x9804),  # Pyboard in CDC2+MSC mode
            (0xF055, 0x9805),  # Pyboard in CDC2 mode
            (0xF055, 0x9806),  # Pyboard in CDC3 mode
            (0xF055, 0x9807),  # Pyboard in CDC3+MSC mode
            (0xF055, 0x9808),  # Pyboard in CDC+MSC+HID mode
            (0xF055, 0x9809),  # Pyboard in CDC2+MSC+HID mode
            (0xF055, 0x980A),  # Pyboard in CDC3+MSC+HID mode
        ),
        "description": "PyBoard",
        "icon": "micropython48",
        "port_description": "Pyboard",
        "module": ".PyBoardDevices",
    },
    "rp2": {
        "ids": (
            (0x1209, 0xF502),  # Silicognition RP2040-Shim
            (0x16D0, 0x08C7),  # Pimoroni Tiny 2040 (8MB)
            (0x1B4F, 0x0025),  # SparkFun Thing Plus RP2040
            (0x1B4F, 0x0026),  # SparkFun Pro Micro RP2040
            (0x1B4F, 0x0039),  # SparkFun Pro Micro RP2350
            (0x1FFB, 0x2043),  # Pololu 3pi+ 2040 Robot
            (0x1FFB, 0x2044),  # Pololu Zumo 2040 Robot
            (0x2341, 0x025E),  # Arduino Nano RP2040 Connect
            (0x239A, 0x80F2),  # Adafruit Feather RP2040
            (0x239A, 0x80F8),  # Adafruit QT Py RP2040
            (0x239A, 0x80FE),  # Adafruit ItsyBitsy RP2040
            (0x2E8A, 0x0005),  # Raspberry Pi Pico, Raspberry Pi Pico 2
            (0x2E8A, 0x000C),  # Raspberry Pi Pico, Raspberry Pi Pico 2
            (0x2E8A, 0x1002),  # Pimoroni Pico LiPo (4MB)
            (0x2E8A, 0x1003),  # Pimoroni Pico LiPo (16MB)
        ),
        "description": QCoreApplication.translate(
            "MicroPythonDevice", "RP2040/RP2350 based"
        ),
        "icon": "rp2Device",
        "port_description": "",
        "module": ".RP2Devices",
    },
    "stlink": {
        "ids": ((0x0483, 0x374B),),  # STM32 STLink,
        "description": "STM32 STLink",
        "icon": "micropython48",
        "port_description": "STM32 STLink",
        "module": ".STLinkDevices",
    },
    "teensy": {
        "ids": ((0xF055, 0x9802),),  # Pyboard in CDC+MSC mode
        "description": "Teensy",
        "icon": "micropython48",
        "port_description": "Teensy",
        "module": ".TeensyDevices",
    },
}

IgnoredBoards = (
    (0x1A7E, 0x1001),  # Meltex UT150-A temperature sensor
    (0x8086, 0x9C3D),
    (0x8086, None),
)

FirmwareGithubUrls = {  # noqa: U200
    "micropython": "https://github.com/micropython/micropython/releases/latest",
    "circuitpython": "https://github.com/adafruit/circuitpython/releases/latest",
    "pimoroni_pico": "https://github.com/pimoroni/pimoroni-pico/releases/latest",
    "microbit_v1": "https://github.com/bbcmicrobit/micropython/releases/latest",
    "microbit_v2": (
        "https://github.com/microbit-foundation/micropython-microbit-v2/releases/latest"
    ),
}


def getSupportedDevices():
    """
    Function to get a list of supported MicroPython devices.

    @return set of tuples with the board type and description
    @rtype set of tuples of (str, str)
    """
    boards = []
    for board in SupportedBoards:
        boards.append((board, SupportedBoards[board]["description"]))
    return boards


def getFoundDevices():
    """
    Function to check the serial ports for supported MicroPython devices.

    @return tuple containing a list of tuples with the board type, the port
        description, a description, the serial port it is connected at, the
        VID and PID for known device types, a list of tuples with VID, PID
        and description for unknown devices and a list of tuples with VID,
        PID, description and port name for ports with missing VID or PID
    @rtype tuple of (list of tuples of (str, str, str, str, int, int),
        list of tuples of (int, int, str),
        list of tuples of (int, int, str, str)
    """
    foundDevices = []
    unknownDevices = []
    unknownPorts = []

    manualDevices = {}
    for deviceDict in Preferences.getMicroPython("ManualDevices"):
        manualDevices[(deviceDict["vid"], deviceDict["pid"])] = deviceDict

    availablePorts = QSerialPortInfo.availablePorts()
    for port in availablePorts:
        if port.hasVendorIdentifier() and port.hasProductIdentifier():
            supported = False
            vid = port.vendorIdentifier()
            pid = port.productIdentifier()

            if OSUtilities.isMacPlatform() and port.portName().startswith("tty."):
                # don't use the tty. variant on macOS; use the cu. one instead
                continue

            for board in SupportedBoards:
                if (vid, pid) in SupportedBoards[board]["ids"] or (
                    vid,
                    None,
                ) in SupportedBoards[board]["ids"]:
                    if board in ("bbc_microbit", "calliope") and (
                        port.description().strip()
                        != SupportedBoards[board]["port_description"]
                    ):
                        # both boards have the same VID and PID
                        # try to differentiate based on port description
                        continue
                    elif board in ("generic", "pyboard", "teensy") and (
                        not port.description().startswith(
                            SupportedBoards[board]["port_description"]
                        )
                    ):
                        # These boards have the same VID and PID.
                        # Try to differentiate based on port description
                        continue
                    foundDevices.append(
                        (
                            board,
                            port.description(),
                            SupportedBoards[board]["description"],
                            port.portName(),
                            vid,
                            pid,
                            port.serialNumber(),
                        )
                    )
                    supported = True
            if not supported and (vid, pid) in manualDevices:
                # check the locally added ones next
                board = manualDevices[(vid, pid)]["type"]
                foundDevices.append(
                    (
                        board,
                        port.description(),
                        SupportedBoards[board]["description"],
                        port.portName(),
                        vid,
                        pid,
                        port.serialNumber(),
                    )
                )
                supported = True
            if not supported:
                if vid and pid:
                    if (vid, pid) not in IgnoredBoards and (
                        vid,
                        None,
                    ) not in IgnoredBoards:
                        unknownDevices.append((vid, pid, port.description()))
                        logging.getLogger(__name__).debug(
                            "Unknown device: (0x%04x:0x%04x %s)",
                            vid,
                            pid,
                            port.description(),
                        )
                else:
                    # either VID or PID or both not detected
                    desc = port.description()
                    if not desc:
                        desc = QCoreApplication.translate(
                            "MicroPythonDevice", "Unknown Device"
                        )
                    unknownPorts.append((vid, pid, desc, port.portName()))

        elif bool(port.portName()) and Preferences.getMicroPython(
            "EnableManualDeviceSelection"
        ):
            # no VID and/or PID available (e.g. in Linux container of ChromeOS)
            desc = port.description()
            if not desc:
                desc = QCoreApplication.translate("MicroPythonDevice", "Unknown Device")
            unknownPorts.append((0, 0, desc, port.portName()))

    return foundDevices, unknownDevices, unknownPorts


def getDeviceIcon(boardName, iconFormat=True):
    """
    Function to get the icon for the given board.

    @param boardName name of the board
    @type str
    @param iconFormat flag indicating to get an icon or a pixmap
    @type bool
    @return icon for the board (iconFormat == True) or
        a pixmap (iconFormat == False)
    @rtype QIcon or QPixmap
    """
    iconName = (
        SupportedBoards[boardName]["icon"]
        if boardName in SupportedBoards
        else
        # return a generic MicroPython icon
        "micropython48"
    )

    if iconFormat:
        return EricPixmapCache.getIcon(iconName)
    else:
        return EricPixmapCache.getPixmap(iconName)


def getDevice(deviceType, microPythonWidget, vid, pid, boardName="", serialNumber=""):
    """
    Public method to instantiate a specific MicroPython device interface.

    @param deviceType type of the device interface
    @type str
    @param microPythonWidget reference to the main MicroPython widget
    @type MicroPythonWidget
    @param vid vendor ID (only used for deviceType 'generic')
    @type int
    @param pid product ID (only used for deviceType 'generic')
    @type int
    @param boardName name of the board (defaults to "")
    @type str (optional)
    @param serialNumber serial number of the board (defaults to "")
    @type str (optional)
    @return instantiated device interface
    @rtype BaseDevice
    """
    with contextlib.suppress(KeyError):
        mod = importlib.import_module(
            SupportedBoards[deviceType]["module"], __package__
        )
        if mod:
            return mod.createDevice(
                microPythonWidget, deviceType, vid, pid, boardName, serialNumber
            )

    # nothing specific requested or specific one failed or is not supported yet
    return BaseDevice(microPythonWidget, deviceType)
