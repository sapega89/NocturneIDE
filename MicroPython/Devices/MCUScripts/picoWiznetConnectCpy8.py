def connect_lan():
    import os
    from adafruit_wiznet5k import adafruit_wiznet5k

    global nic

    if os.getenv("WIZNET_IFCONFIG_0") is None:
        print("The network configuration is kept in 'settings.toml'")
        print("with the keys 'WIZNET_IFCONFIG_0' to 'WIZNET_IFCONFIG_3'.")
        print("Please add them there.")
        return None

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

    nic.mac_address = adafruit_wiznet5k._DEFAULT_MAC
    if os.getenv("WIZNET_IFCONFIG_0") == 'dhcp':
        nic.set_dhcp(hostname=os.getenv("WIZNET_HOSTNAME"))
    else:
        nic.ifconfig = (
            nic.unpretty_ip(os.getenv("WIZNET_IFCONFIG_0")),
            nic.unpretty_ip(os.getenv("WIZNET_IFCONFIG_1")),
            nic.unpretty_ip(os.getenv("WIZNET_IFCONFIG_2")),
            tuple(int(a) for a in os.getenv("WIZNET_IFCONFIG_3").split('.')),
        )

    return nic
