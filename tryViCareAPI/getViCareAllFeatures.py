import sys
import logging
from PyViCare.PyViCare import PyViCare
from functools import wraps
from typing import Callable
from PyViCare import Feature
from PyViCare.PyViCareUtils import PyViCareNotSupportedFeatureError
import json
#from myUtils import HandleNotSupported

client_id = ""
email = ""
password = ""

vicare = PyViCare()
vicare.initWithCredentials(email, password, client_id, "token.save")

device = vicare.devices[1]
print(json.dumps(device.service.fetch_all_features()))

