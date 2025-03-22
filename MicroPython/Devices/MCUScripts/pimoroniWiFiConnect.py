try:
    import secrets

    def connect_wifi():
        import picowireless as pw
        from time import sleep

        print("Connecting WiFi to '{0}' ...".format(secrets.WIFI_SSID))
        pw.init()
        if bool(secrets.WIFI_KEY):
            pw.wifi_set_passphrase(secrets.WIFI_SSID, secrets.WIFI_KEY)
        else:
            pw.wifi_set_network(secrets.WIFI_SSID)

        max_wait = 140
        while max_wait:
            if pw.get_connection_status() == 3:
                break
            max_wait -= 1
            sleep(0.1)
        if pw.get_connection_status() == 3:
            pw.set_led(0, 64, 0)
            print("WiFi connected:", '.'.join(str(i) for i in pw.get_ip_address()))
        else:
            pw.set_led(64, 0, 0)
            print("WiFi connection failed")

    connect_wifi()
except ImportError:
    print("WiFi secrets are kept in 'secrets.py', please add them there!")
