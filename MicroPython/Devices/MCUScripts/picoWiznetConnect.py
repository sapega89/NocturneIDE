try:
    import wiznet_config

    def connect_lan():
        import network
        import time
        from machine import Pin, SPI

        try:
            ifconfig = wiznet_config.ifconfig
            hostname = wiznet_config.hostname
        except AttributeError:
            print("The network configuration in 'wiznet_config.py' is invalid.")
            return None

        if hostname:
            try:
                network.hostname(hostname)
            except AttributeError:
                pass

        spi = SPI(0, 2_000_000, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        nic = network.WIZNET5K(spi, Pin(17), Pin(20))

        nic.active(False)
        nic.active(True)
        nic.ifconfig(ifconfig)
        max_wait = 140
        while max_wait:
            if nic.isconnected():
                break
            max_wait -= 1
            time.sleep(0.1)

        if nic.isconnected():
            print("Connected to LAN:", nic.ifconfig())
        else:
            print("Connection to LAN failed.")

        return nic

except ImportError:
    print(
        "The network configuration is kept in 'wiznet_config.py'. Please add it there."
    )
    def connect_lan():
        return None
