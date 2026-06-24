import serial.tools.list_ports

def auto_detect():
    results = {"touch_plus": None, "monarch": None}
    try:
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            desc = (p.description + " " + p.device).lower()
            if "bluetooth" in desc and "humanware" in desc:
                results["touch_plus"] = p.device
            elif "humanware" in desc or "monarch" in desc:
                results["monarch"] = p.device
        if not results["touch_plus"] and not results["monarch"]:
            for p in ports:
                try:
                    s = serial.Serial(p.device, timeout=1, write_timeout=1)
                    s.write(b'\r')
                    resp = s.read(100)
                    s.close()
                    if resp:
                        if b'braillenote' in resp.lower() or b'touch' in resp.lower():
                            results["touch_plus"] = p.device
                        elif b'monarch' in resp.lower() or b'manarc' in resp.lower():
                            results["monarch"] = p.device
                except Exception:
                    pass
    except Exception:
        pass
    return results
