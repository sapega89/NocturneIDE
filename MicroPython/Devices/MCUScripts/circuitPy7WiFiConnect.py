try:
    from secrets import secrets

    def connect_wifi():
        import wifi

        print("Connecting WiFi to '{0}' ...".format(secrets["ssid"]))

        if secrets["hostname"]:
            wifi.radio.hostname = secrets["hostname"]

        wifi.radio.start_station()
        try:
            wifi.radio.connect(
                secrets["ssid"],
                "" if secrets["password"] is None else secrets["password"]
            )
        except Exception as exc:
            print("WiFi connection failed:", str(exc))
        if wifi.radio.ipv4_address is None:
            print("WiFi connection failed")
        else:
            print("WiFi connected:", wifi.radio.ipv4_address)

    connect_wifi()
except ImportError:
    print("WiFi secrets are kept in 'secrets.py', please add them there!")
