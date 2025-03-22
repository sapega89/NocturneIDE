def has_ntp():
    try:
        import ntptime
        return True
    except ImportError:
        return False

def set_ntp_time(server, tz_offset, timeout):
    import ntptime
    import machine

    ntptime.host = server
    ntptime.timeout = timeout
    ntptime.settime()

    rtc = machine.RTC()
    t = list(rtc.datetime())
    t[4] += tz_offset
    rtc.datetime(t)

def connect_wifi():
    import esp32
    import network
    from time import sleep

    try:
        nvs = esp32.NVS("wifi_creds")
        buf = bytearray(1024)
        size = nvs.get_blob("ssid", buf)
        ssid = buf[:size].decode()
        size = nvs.get_blob("password", buf)
        password = buf[:size].decode()
        size = nvs.get_blob("hostname", buf)
        hostname = buf[:size].decode()
        size = nvs.get_blob("country", buf)
        country = buf[:size].decode()

        print("Connecting WiFi to '{0}'...".format(ssid))

        if country:
            try:
                network.country(country)
            except AttributeError:
                pass

        if hostname:
            try:
                network.hostname(hostname)
            except AttributeError:
                pass

        wifi = network.WLAN(network.STA_IF)
        wifi.active(False)
        wifi.active(True)
        wifi.connect(ssid, password)
        max_wait = 140
        while max_wait and wifi.status() != network.STAT_GOT_IP:
            max_wait -= 1
            sleep(0.1)
        if wifi.isconnected():
            print("WiFi connected:", wifi.ifconfig()[0])
            if has_ntp():
                set_ntp_time("pool.ntp.org", 0, 10)
                print("Time snchronized to network time (UTC).")
        else:
            print("WiFi connection failed. Status:", wifi.status())
    except:
        print("WiFi secrets are kept in NVM. Please store them there!")

connect_wifi()
