from PyViCare.PyViCare import PyViCare
from functools import wraps
import json

client_id = ""
email = ""
password = ""
file = "./tests/features.json"

vicare = PyViCare()
vicare.initWithCredentials(email, password, client_id, "token.save")

device = vicare.devices[1]
fJson = json.dumps(
    device.service.fetch_all_features(),
    indent=4,
)
with open(file, mode="w", encoding="utf-8") as f:
    f.write(fJson)
print("Features have been written to %s", file)
