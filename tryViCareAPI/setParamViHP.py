# ==================================================
# This program can be used to set a single parameter
# ===================================================
from PyViCare.PyViCare import PyViCare

client_id = ""
email = ""
password = ""

# ==== Parameter to be modified ======
circuit = 1
feature = f"heating.circuits.{circuit}.temperature.levels"
property = "max"
command = "setMax"
params = {"temperature": 50.0}
# ====================================

vicare = PyViCare()
vicare.initWithCredentials(email, password, client_id, "token.save")
device = vicare.devices[1]

# Get Value before change
valInit = device.service.getProperty(feature)["properties"][property]["value"]

# Change value
ok = True
try:
    res = device.service.setProperty(feature, command, params,)
except Exception as e:
    ok = False

# Get Value after change
valFinal = device.service.getProperty(feature)["properties"][property]["value"]

# Print result
print("")
print(f"Feature: {feature}")
print(f"Property: {property}")
print(f"Initial value: {valInit}")
if ok:
    print(f"Result: {res}")
else:
    print(f"Exception: {e}")
print(f"Final value: {valFinal}")
