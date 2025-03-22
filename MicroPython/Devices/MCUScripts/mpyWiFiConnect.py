try:
    import secrets

    def connect_wifi():
        import network
        from time import sleep

        print("Connecting WiFi to '{0}' ...".format(secrets.WIFI_SSID))

        if secrets.WIFI_HOSTNAME:
            try:
                network.hostname(secrets.WIFI_HOSTNAME)
            except AttributeError:
                pass

        wifi = network.WLAN(network.STA_IF)
        wifi.active(False)
        wifi.active(True)
        wifi.connect(secrets.WIFI_SSID, secrets.WIFI_KEY if secrets.WIFI_KEY else None)
        max_wait = 140
        while max_wait:
            if wifi.status() < 0 or wifi.status() >= 3:
                break
            max_wait -= 1
            sleep(0.1)
        if wifi.isconnected():
            print("WiFi connected:", wifi.ifconfig())
        else:
            print("WiFi connection failed")

    connect_wifi()
except ImportError:
    print("WiFi secrets are kept in 'secrets.py', please add them there!")
