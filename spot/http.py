import json, time, urllib.request, urllib.error
UA = {"User-Agent": "Mozilla/5.0 (spot-radar)"}
def get_json(url, timeout=25, retries=2, pace=0.0):
    last = None
    for i in range(retries + 1):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
            data = json.loads(r.read().decode("utf-8", "ignore"))
            if pace: time.sleep(pace)
            return data
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    return None
def get_text(url, timeout=25):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
        return r.read().decode("utf-8", "ignore")
    except Exception:
        return None
