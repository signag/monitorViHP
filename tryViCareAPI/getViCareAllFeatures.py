from PyViCare.PyViCare import PyViCare
from functools import wraps
import json

client_id = ""
email = ""
password = ""
file = "./tests/features.json"
fileEnabled = "./tests/features_enabled.json"
fileCSV = "./tests/features_enabled.csv"
csvSep = ";"
decimalSeparator = ","

vicare = PyViCare()
vicare.initWithCredentials(email, password, client_id, "token.save")

device = vicare.devices[1]
allFeatures = device.service.fetch_all_features()
fJson = json.dumps(
    allFeatures,
    indent=4,
)
with open(file, mode="w", encoding="utf-8") as f:
    f.write(fJson)
print(f"Features have been written to {file}")

enabledFeatures = {}
efData = []
properties = []
properties.append("value")
afData = allFeatures["data"]
for feat in afData:
    if "isEnabled" in feat:
        if feat["isEnabled"] == True:
            efData.append(feat)
            if "properties" in feat:
                props = feat["properties"]
                for key, value in props.items():
                    if "value" in value and "type" in value:
                        type = value["type"]
                        if type == "string" \
                        or type == "number" \
                        or type == "boolean":
                            if not key in properties:
                                properties.append(key)

enabledFeatures["data"] = efData
fJson = json.dumps(
    enabledFeatures,
    indent=4,
)
with open(fileEnabled, mode="w", encoding="utf-8") as f:
    f.write(fJson)
print(f"Enabled features have been written to {fileEnabled}")


title = "Feature"
for prp in properties:
    title = title + csvSep + prp

with open(fileCSV, mode="w", encoding="utf-8") as f:
    f.write(title)
    for feat in efData:
        line = feat["feature"]
        props = feat["properties"]
        for prp in properties:
            if prp in props:
                type = props[prp]["type"]
                if type == "string" \
                or type == "number" \
                or type == "boolean":
                    val = props[prp]["value"]
                    strVal = str(val)
                    if isinstance(val, float):
                        strValF = strVal.replace(".", decimalSeparator)
                    else:
                        strValF = strVal
                    line = line + csvSep + strValF
                else:
                    line = line + csvSep
            else:
                line = line + csvSep
        line = line + "\n"
        f.write(line)
print(f"A list of features has been written to {fileCSV}")
