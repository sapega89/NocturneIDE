try:
    import wiznet_config

    def connect_lan():
        from adafruit_wiznet5k import adafruit_wiznet5k

        global nic

        try:
            ifconfig = wiznet_config.ifconfig
            hostname = wiznet_config.hostname
        except AttributeError:
            print("The network configuration in 'wiznet_config.py' is invalid.")
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
        if ifconfig == 'dhcp':
            nic.set_dhcp(hostname=hostname)
        else:
            nic.ifconfig = (
                nic.unpretty_ip(ifconfig[0]),
                nic.unpretty_ip(ifconfig[1]),
                nic.unpretty_ip(ifconfig[2]),
                tuple(int(a) for a in ifconfig[3].split('.')),
            )

        return nic

except ImportError:
    print(
        "The network configuration is kept in 'wiznet_config.py'. Please add it there."
    )
    def connect_lan():
        return None
