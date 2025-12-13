import urllib.request
import json
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/qr/entry") as response:
       data = json.loads(response.read().decode())
       print(data['url'])
except Exception as e:
    print(e)
