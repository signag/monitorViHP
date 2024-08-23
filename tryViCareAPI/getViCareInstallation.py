import sys
import logging
from PyViCare.PyViCare import PyViCare
from functools import wraps
from typing import Callable
from PyViCare import Feature
from PyViCare.PyViCareUtils import PyViCareNotSupportedFeatureError
import json
# from myUtils import HandleNotSupported

client_id = ""
email = ""
password = ""

vicare = PyViCare()
vicare.initWithCredentials(email, password, client_id, "token.save")
n = 0
print("Installations:")
for inst in vicare.installations:
    print(f"\tInstallation {n}")
    print(f"\tInstallation ID: {inst.id}")
    print(f"\tDescription: {inst.description}")
    print(f"\tAccessLevel: {inst.accessLevel}")
    print(f"\tInstallationType: {inst.installationType}")
    print(f"\tHeatingType: {inst.heatingType}")
    print(f"\tOwnedByMaintainer: {inst.ownedByMaintainer}")
    print(f"\tOwnershipType: {inst.ownershipType}")
    print(f"\tEndUserWlanCommissioned: {inst.endUserWlanCommissioned}")
    print(f"\tRegisteredAt: {inst.registeredAt}")
    print(f"\tUpdatedAt: {inst.updatedAt}")
    print(f"\tWithoutViCareUser: {inst.withoutViCareUser}")
    print(f"\tAddress:")
    print(f"\t\tCity: {inst.address.city}")
    print(f"\t\tZip: {inst.address.zip}")
    print(f"\t\tStreet: {inst.address.street}")
    print(f"\t\tHouseNumber: {inst.address.houseNumber}")
    print(f"\t\tCountry: {inst.address.country}")
    print(f"\t\tPhoneNumber: {inst.address.phoneNumber}")
    print(f"\t\tFaxNumber: {inst.address.faxNumber}")
    n += 1
print("")

print("Devices")
n = 0
for device in vicare.devices:
    print(f"\tDevice {n}")
    print(f"\tID: {device.device_id}")
    print(f"\t\tModel: {device.device_model}")
    print(f"\t\tStatus: {device.status}")
    n += 1
