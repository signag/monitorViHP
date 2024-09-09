#!/usr/bin/python3
"""
Module monitorViHP

This module periodically reads data from an OpenEMS Energy Management System
and stores data in an InfluxDB and/or CSV files.

For openEMS, see: https://github.com/OpenEMS/openems
"""

import time
import datetime
import math
import os
import os.path
import json
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareUtils import (
    PyViCareBrowserOAuthTimeoutReachedError,
    PyViCareCommandError,
    PyViCareInternalServerError,
    PyViCareRateLimitError,
)

# Set up logging
import logging
from logging.config import dictConfig
import logging_plus

logger = logging_plus.getLogger("main")

testRun = False
servRun = False


# Configuration defaults
cfgFile = ""
cfg = {
    "measurementInterval": 120,
    "vicareClient_id": None,
    "vicareEmail": None,
    "vicarePassword": None,
    "vicareInstallation": None,
    "vicareDevice": None,
    "InfluxOutput": False,
    "InfluxURL": None,
    "InfluxOrg": None,
    "InfluxToken": None,
    "InfluxBucket": None,
    "csvOutput": False,
    "csvFile": "",
    "vicareData": [],
}

# Constants
CFGFILENAME = "monitorViHP.json"


def getCl():
    """Get command line parameters

    Raises:
        ValueError: Invalid command line parameter
    """

    import argparse
    import os.path

    global logger
    global testRun
    global servRun
    global cfgFile

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
    This program periodically reads data from Viessmann ViCare controlling a heating system
    and stores these as measurements in an InfluxDB database.

    If not otherwises specified on the command line, a configuration file
       monitorViHP.json
    will be searched sequentially under ./tests/data, ./config, $HOME/.config or /etc.

    This configuration file specifies credentials for ViCare access,
    the connection to the InfluxDB and datapoint definitions.
    """,
    )
    parser.add_argument(
        "-t", "--test", action="store_true", help="Test run - single cycle - no wait"
    )
    parser.add_argument(
        "-s", "--service", action="store_true", help="Run as service - special logging"
    )
    parser.add_argument(
        "-l", "--log", action="store_true", help="Shallow (module) logging"
    )
    parser.add_argument("-L", "--Log", action="store_true", help="Deep logging")
    parser.add_argument("-F", "--Full", action="store_true", help="Full logging")
    parser.add_argument("-p", "--logfile", help="path to log file")
    parser.add_argument(
        "-f", "--file", help="Logging configuration from specified JSON dictionary file"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose - log INFO level"
    )
    parser.add_argument("-c", "--config", help="Path to config file to be used")

    args = parser.parse_args()

    # Disable logging
    logger = logging_plus.getLogger("main")
    logger.addHandler(logging.NullHandler())
    rLogger = logging_plus.getLogger()
    rLogger.addHandler(logging.NullHandler())

    # Set handler and formatter to be used
    handler = logging.StreamHandler()
    if args.logfile:
        handler = logging.FileHandler(args.logfile)
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    formatter2 = logging.Formatter(
        "%(asctime)s %(name)-33s %(levelname)-8s %(message)s"
    )
    handler.setFormatter(formatter)

    if args.log:
        # Shallow logging
        handler.setFormatter(formatter2)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    if args.Log:
        # Deep logging
        handler.setFormatter(formatter2)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    if args.Full:
        # Full logging
        handler.setFormatter(formatter2)
        rLogger.addHandler(handler)
        rLogger.setLevel(logging.DEBUG)
        # Activate logging of function entry and exit
        logging_plus.registerAutoLogEntryExit()

    if args.file:
        # Logging configuration from file
        logDictFile = args.file
        if not os.path.exists(logDictFile):
            raise ValueError(
                "Logging dictionary file from command line does not exist: "
                + logDictFile
            )

        # Load dictionary
        with open(logDictFile, "r") as f:
            logDict = json.load(f)

        # Set config file for logging
        dictConfig(logDict)
        logger = logging.getLogger()
        # Activate logging of function entry and exit
        # logging_plus.registerAutoLogEntryExit()

    # Explicitly log entry
    if args.Log or args.Full:
        logger.logEntry("getCL")
    if args.log:
        logger.debug("Shallow logging (main only)")
    if args.Log:
        logger.debug("Deep logging")
    if args.file:
        logger.debug("Logging dictionary from %s", logDictFile)

    if args.verbose or args.service:
        if not args.log and not args.Log and not args.Full:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    if args.test:
        testRun = True

    if args.service:
        servRun = True

    if testRun:
        logger.debug("Test run mode activated")
    else:
        logger.debug("Test run mode deactivated")

    if servRun:
        logger.debug("Service run mode activated")
    else:
        logger.debug("Service run mode deactivated")

    if args.config:
        cfgFile = args.config
        logger.debug("Config file: %s", cfgFile)
    else:
        logger.debug("No Config file specified on command line")

    if args.Log or args.Full:
        logger.logExit("getCL")


def getConfig():
    """Get the configuration form the configuration file

    At first the configuration file is searched in a sequence of paths:
    ./tests/data -> ./config/ -> ~/.config
    Whenever a file CFGFILENAME is used, this is taken.

    Configuration entries found in the configuration file overwrite
    the global configuration cfg

    Raises:
        ValueError: Invalid or missing configuration parameters
    """
    global cfgFile
    global cfg
    global logger

    # Check config file from command line
    if cfgFile != "":
        if not os.path.exists(cfgFile):
            raise ValueError(
                "Configuration file from command line does not exist: ", cfgFile
            )
        logger.info("Using cfgFile from command line: %s", cfgFile)

    if cfgFile == "":
        # Check for config file in ./tests/data directory
        curDir = os.path.dirname(os.path.realpath(__file__))
        curDir = os.path.dirname(curDir)
        cfgFile = curDir + "/tests/data/" + CFGFILENAME
        if not os.path.exists(cfgFile):
            # Check for config file in /etc directory
            logger.info("Config file not found: %s", cfgFile)
            cfgFile = ""

    if cfgFile == "":
        # Check for config file in ./config directory
        curDir = os.path.dirname(os.path.realpath(__file__))
        curDir = os.path.dirname(curDir)
        cfgFile = curDir + "/config/" + CFGFILENAME
        if not os.path.exists(cfgFile):
            # Check for config file in ./config directory
            logger.info("Config file not found: %s", cfgFile)
            cfgFile = ""

    if cfgFile == "":
        # Check for config file in $HOME/.config directory
        try:
            homeDir = os.environ["HOME"]
            cfgFile = homeDir + "/.config/" + CFGFILENAME
            if not os.path.exists(cfgFile):
                logger.info("Config file not found: %s", cfgFile)
                # Check for config file in etc directory
                cfgFile = "/etc/" + CFGFILENAME
                if not os.path.exists(cfgFile):
                    logger.info("Config file not found: %s", cfgFile)
                    cfgFile = ""
        except KeyError:
            logger.info("Environment variable HOME not set.")
            cfgFile = ""

    if cfgFile == "":
        # No cfg available
        logger.info("No config file available. Using default configuration")
    else:
        logger.info("Using cfgFile: %s", cfgFile)
        with open(cfgFile, "r") as f:
            conf = json.load(f)
            if "measurementInterval" in conf:
                cfg["measurementInterval"] = conf["measurementInterval"]
            if "vicareClient_id" in conf:
                cfg["vicareClient_id"] = conf["vicareClient_id"]
            if "vicareEmail" in conf:
                cfg["vicareEmail"] = conf["vicareEmail"]
            if "vicarePassword" in conf:
                cfg["vicarePassword"] = conf["vicarePassword"]
            if "vicareInstallation" in conf:
                cfg["vicareInstallation"] = conf["vicareInstallation"]
            if "vicareDevice" in conf:
                cfg["vicareDevice"] = conf["vicareDevice"]
            if "InfluxOutput" in conf:
                cfg["InfluxOutput"] = conf["InfluxOutput"]
            if "InfluxURL" in conf:
                cfg["InfluxURL"] = conf["InfluxURL"]
            if "InfluxOrg" in conf:
                cfg["InfluxOrg"] = conf["InfluxOrg"]
            if "InfluxToken" in conf:
                cfg["InfluxToken"] = conf["InfluxToken"]
            if "InfluxBucket" in conf:
                cfg["InfluxBucket"] = conf["InfluxBucket"]
            if "csvOutput" in conf:
                cfg["csvOutput"] = conf["csvOutput"]
            if "csvDir" in conf:
                cfg["csvDir"] = conf["csvDir"]
            if cfg["csvDir"] == "":
                cfg["csvOutput"] = False
            if "vicareData" in conf:
                cfg["vicareData"] = conf["vicareData"]

    # Check Vicare credentials
    if not cfg["vicareClient_id"]:
        raise ValueError("vicareClient_id not specified")
    if not cfg["vicareEmail"]:
        raise ValueError("vicareEmail not specified")
    if not cfg["vicarePassword"]:
        raise ValueError("vicarePassword not specified")
    if not cfg["vicareInstallation"]:
        raise ValueError("vicareInstallation not specified")
    if not cfg["vicareDevice"]:
        raise ValueError("vicareDevice not specified")

    logger.info("Configuration:")
    logger.info("    measurementInterval:%s", cfg["measurementInterval"])
    logger.info("    vicareClient_id:%s", cfg["vicareClient_id"])
    logger.info("    vicareEmail:%s", cfg["vicareEmail"])
    logger.info("    vicarePassword:%s", cfg["vicarePassword"])
    logger.info("    vicareInstallation:%s", cfg["vicareInstallation"])
    logger.info("    vicareDevice:%s", cfg["vicareDevice"])
    logger.info("    InfluxOutput:%s", cfg["InfluxOutput"])
    logger.info("    InfluxURL:%s", cfg["InfluxURL"])
    logger.info("    InfluxOrg:%s", cfg["InfluxOrg"])
    logger.info("    InfluxToken:%s", cfg["InfluxToken"])
    logger.info("    InfluxBucket:%s", cfg["InfluxBucket"])
    logger.info("    csvOutput:%s", cfg["csvOutput"])
    logger.info("    csvDir:%s", cfg["csvDir"])
    logger.info("    vicareData:%s", len(cfg["vicareData"]))


def waitForNextCycle(waitUntilMidnight: bool = False):
    """Wait for next measurement cycle.

    This function assures that measurements are done at specific times depending on the specified interval
    In case that measurementInterval is an integer multiple of 60, the waiting time is calculated in a way,
    that one measurement is done every full hour.

    Args:
        waitUntilMidnight (bool, optional): Defaults to False.
            When True, the next cycle will not be started before midnight.
            Typically, this is used in cases with limited number of service calls
            where the daily quota has been exceeded.
    """
    global cfg

    if waitUntilMidnight:
        tNow = datetime.datetime.now()
        waitTimeSec = (
            24 * 60 * 60
            - (
                3600 * tNow.hour
                + 60 * tNow.minute
                + tNow.second
                + tNow.microsecond / 1000000
            )
            + 5 * 60
        )
        time.sleep(waitTimeSec)

    elif (
        (cfg["measurementInterval"] % 60 == 0)
        or (cfg["measurementInterval"] % 120 == 0)
        or (cfg["measurementInterval"] % 240 == 0)
        or (cfg["measurementInterval"] % 300 == 0)
        or (cfg["measurementInterval"] % 360 == 0)
        or (cfg["measurementInterval"] % 600 == 0)
        or (cfg["measurementInterval"] % 720 == 0)
        or (cfg["measurementInterval"] % 900 == 0)
        or (cfg["measurementInterval"] % 1200 == 0)
        or (cfg["measurementInterval"] % 1800 == 0)
    ):
        tNow = datetime.datetime.now()
        seconds = 60 * tNow.minute
        period = math.floor(seconds / cfg["measurementInterval"])
        waitTimeSec = (period + 1) * cfg["measurementInterval"] - (
            60 * tNow.minute + tNow.second + tNow.microsecond / 1000000
        )
        logger.debug(
            "At %s waiting for %s sec.",
            datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"),
            waitTimeSec,
        )
        time.sleep(waitTimeSec)
    elif (
        (cfg["measurementInterval"] % 2 == 0)
        or (cfg["measurementInterval"] % 4 == 0)
        or (cfg["measurementInterval"] % 5 == 0)
        or (cfg["measurementInterval"] % 6 == 0)
        or (cfg["measurementInterval"] % 10 == 0)
        or (cfg["measurementInterval"] % 12 == 0)
        or (cfg["measurementInterval"] % 15 == 0)
        or (cfg["measurementInterval"] % 20 == 0)
        or (cfg["measurementInterval"] % 30 == 0)
    ):
        tNow = datetime.datetime.now()
        seconds = 60 * tNow.minute + tNow.second
        period = math.floor(seconds / cfg["measurementInterval"])
        waitTimeSec = (period + 1) * cfg["measurementInterval"] - seconds
        logger.debug(
            "At %s waiting for %s sec.",
            datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"),
            waitTimeSec,
        )
        time.sleep(waitTimeSec)
    else:
        waitTimeSec = cfg["measurementInterval"]
        logger.debug(
            "At %s waiting for %s sec.",
            datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S,"),
            waitTimeSec,
        )
        time.sleep(waitTimeSec)

def getPyViCareSession() -> PyViCare:
    """The function initializes a session for subsequent service calls

    Returns:
        PyViCare: Session with authorization
    """

    vicare = PyViCare()
    vicare.initWithCredentials(
        cfg["vicareEmail"], cfg["vicarePassword"], cfg["vicareClient_id"], "token.save"
    )
    return vicare

def getTagOrField(features: dict, tfCfg: dict, measurement: str, type: str) -> dict:
    """Create a dictionary of tags or fields from a given configuration

    Args:
        features (dict): ViCare features dictionary
        tfCfg (dict): Configuration for tags or fields
        measurement (str): measurement
        type (str): "tags"|"fields"
        
    Raises:
        ValueError: in case of missing or infalid data in tag or field configuration
    Returns:
        dict: tags or fields dictionary
    """
    res = {}
    for tf in tfCfg:
        if "name" in tf:
            nameCfg = tf["name"]
        else:
            raise ValueError(f"name missing in vicareData / {measurement} / {type}")
        if "value" in tf:
            valCfg = tf["value"]
        else:
            raise ValueError(f"Tagname missing in vicareData / {measurement} / {type}")

        if "source" in valCfg:
            sourceCfg = valCfg["source"]
        else:
            raise ValueError(f"Source missing in vicareData / {measurement} / {type}")

        if "feature" in valCfg:
            featureCfg = valCfg["feature"]
        else:
            raise ValueError(f"feature missing in vicareData / {measurement} / {type}")

        if sourceCfg == "value":
            value = featureCfg
            if type == "tags":
                value = str(value)
        elif sourceCfg == "cfg":
            value = cfg[featureCfg]
        elif sourceCfg == "vicare":
            if "formula" in valCfg:
                formulaCfg = valCfg["formula"]
            else:
                raise ValueError(f"formula missing in vicareData / {measurement} / {type} / {nameCfg}")
            if type == "tags":
                typeCfg = "str"
            else:
                if "type" in valCfg:
                    typeCfg = valCfg["type"]
                else:
                    raise ValueError(
                        f"type missing in vicareData / {measurement} / {type} / {nameCfg}"
                    )
            if featureCfg in features:
                properties = features[featureCfg]
                try:
                    value = eval(formulaCfg)
                except Exception as e:
                    raise ValueError(
                        f"formula invalid for vicareData / {measurement} / {type} / {nameCfg}: {str(e)}"
                    )
                if typeCfg == "int":
                    value = int(value)
                elif typeCfg == "float":
                    value = float(value)
                elif typeCfg == "str":
                    value = str(value)
                else:
                    raise ValueError(
                        f"type {typeCfg} invalid for vicareData / {measurement} / {type} / {nameCfg}: {str(e)}"
                    )

            else:
                raise ValueError(
                    f"feature {measurement} / {type} {featureCfg} not found in ViCare features"
                )
        else:
            raise ValueError(
                f"Invalid source ({sourceCfg}) in vicareData / {measurement} / {type}"
            )
        res[nameCfg] = value
    return res

def storeViCaraData(influxWriteAPI, features: dict, mCfg: dict):
    """Store data from an PyViCare query as measurements in Influx

    Args:
        influxWriteAPI: Influx write_api object
        features (dict): ViCare features as dictionary (key: feature, value: properties)
        mCfg (dict): Configuration for Influx measurement
    """
    csvFile = cfg["csvDir"] + mCfg["csvFile"]
    sep = ";"

    point = {}
    point["measurement"] = mCfg["measurement"]
    point["time"] = mTS
    point["tags"] = {}
    point["fields"] = {}

    if "tags" in mCfg:
        tags = mCfg["tags"]
        point["tags"] = getTagOrField(features, tags, mCfg["measurement"], "tags")

    if "fields" in mCfg:
        fields = mCfg["fields"]
        point["fields"] = getTagOrField(features, fields, mCfg["measurement"], "fields")

    if len(point["fields"]) > 0:
        if cfg["InfluxOutput"] == True:
            influxWriteAPI.write(cfg["InfluxBucket"], cfg["InfluxOrg"], point)
            logger.debug(
                "ViCare data written to Influx DB for measurement %s",
                mCfg["measurement"]
            )
        if cfg["csvOutput"] == True:
            title = "_measureemnt" + sep + "_time"
            if len(point["tags"]) > 0:
                for key, value in point["tags"].items():
                    title = title + sep + key
            for key, value in point["fields"].items():
                title = title + sep + key
            title = title + "\n"
            data = point["measurement"] + sep + point["time"]
            if len(point["tags"]) > 0:
                for key, value in point["tags"].items():
                    data = data + sep + value
            for key, value in point["fields"].items():
                data = data + sep + value
            data = data + "\n"
            writeCsv(csvFile, title, data)
            logger.debug(
                "EMS data written to csv file for measurement %s", mCfg["measurement"]
            )


def writeCsv(fp, title, data):
    """
    Write data to CSV file
    """
    f = None
    newFile = True
    if os.path.exists(fp):
        newFile = False
    if newFile:
        os.makedirs(cfg["csvDir"], exist_ok=True)
        f = open(fp, "w")
    else:
        f = open(fp, "a")
    logger.debug("File opened: %s", fp)

    if newFile:
        f.write(title)
    f.write(data)
    f.close()

def dictFromFeatureList(features: list) -> dict:
    """Create a dictionary from ViCare feature list
    
    Use "feature" as dictionary key and "properties" as value

    Args:
        features (list): Feature list from ViCare

    Raises:
        error: _description_

    Returns:
        dict: Features as dictionary
    """
    featDict = {}
    if features:
        if "data" in features:
            data = features["data"]
            for ft in data:
                if "feature" in ft:
                    feature = ft["feature"]
                    if "properties" in ft:
                        props = ft["properties"]
                        featDict[feature] = props

    return featDict

# ============================================================================================
# Start __main__
# ============================================================================================
#
# Get Command line options
getCl()

logger.info("=============================================================")
logger.info("monitorViHP V1.4 started")
logger.info("=============================================================")

# Get configuration
getConfig()

fb = None
influxClient = None
influxWriteAPI = None
stop = False

try:
    # Instantiate InfluxDB access
    if cfg["InfluxOutput"]:
        influxClient = influxdb_client.InfluxDBClient(
            url=cfg["InfluxURL"], token=cfg["InfluxToken"], org=cfg["InfluxOrg"]
        )
        influxWriteAPI = influxClient.write_api(write_options=SYNCHRONOUS)
        logger.debug("Influx interface instantiated")

except Exception as error:
    logger.critical("Unexpected Exception (%s): %s", error.__class__, error.__cause__)
    logger.critical("Unexpected Exception: %s", error.message)
    logger.critical("Could not get InfluxDB access")
    stop = True
    influxClient = None
    influxWriteAPI = None

noWait = False
waitUntilMidnight = False
serverErrorWait = 2 * cfg["measurementInterval"] if cfg["measurementInterval"] > 300 else 300

while not stop:
    try:
        # Wait unless noWait is set in case of an exception.
        # Skip waiting for test run
        if not noWait and not testRun:
            waitForNextCycle(waitUntilMidnight)
        noWait = False
        waitUntilMidnight = False

        logger.info("monitorViHP - cycle started")
        UTC_datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        UTC_timestampRounded = round(UTC_datetime.timestamp())
        UTC_datetimeRounded = datetime.datetime.fromtimestamp(
            UTC_timestampRounded, tz=datetime.timezone.utc
        )
        mTS = UTC_datetimeRounded.strftime("%Y-%m-%dT%H:%M:%S.%f000Z")

        # Get session
        session = getPyViCareSession()

        # Get all Features
        d = int(cfg["vicareDevice"])
        device = session.devices[d]
        features = device.service.fetch_all_features()

        featureDict = dictFromFeatureList(features)

        if "vicareData" in cfg:
            measurements = cfg["vicareData"]
            for measurement in measurements:
                storeViCaraData(influxWriteAPI, featureDict, measurement)

        del session

        serverErrorWait = 2 * cfg["measurementInterval"] if cfg["measurementInterval"] > 300 else 300

        logger.info("monitorViHP - cycle completed")

        if testRun:
            # Stop in case of test run
            stop = True

    except PyViCareRateLimitError as error:
        stop = False
        waitUntilMidnight = True
        serverErrorWait = 2 * cfg["measurementInterval"] if cfg["measurementInterval"] > 300 else 300
        logger.error("Rate limit reached: %s. Waiting untilmidnight", error)

    except PyViCareInternalServerError as error:
        logger.error(
            "PyViCareInternalServerError error %s. Waiting %s sec",
            error,
            serverErrorWait,
        )
        time.sleep(serverErrorWait)
        if serverErrorWait < 3600 * 4:
            serverErrorWait = serverErrorWait * 2

    except PyViCareBrowserOAuthTimeoutReachedError as error:
        logger.error(
            "PyViCareBrowserOAuthTimeoutReachedError error %s. Waiting %s sec",
            error,
            serverErrorWait,
        )
        time.sleep(serverErrorWait)
        if serverErrorWait < 3600 * 4:
            serverErrorWait = serverErrorWait * 2

    except PyViCareCommandError as error:
        logger.error(
            "PyViCareCommandError error %s. Waiting %s sec", error, serverErrorWait
        )
        time.sleep(serverErrorWait)
        if serverErrorWait < 3600 * 4:
            serverErrorWait = serverErrorWait * 2

    except Exception as error:
        stop = True
        logger.critical("Unexpected Exception: %s", error)
        if influxClient:
            del influxClient
            influxClient = None
        if influxWriteAPI:
            del influxWriteAPI
            influxWriteAPI = None
        raise error

    except KeyboardInterrupt:
        stop = True
        logger.debug("KeyboardInterrupt")
        if influxClient:
            del influxClient
            influxClient = None
        if influxWriteAPI:
            del influxWriteAPI
            influxWriteAPI = None
if influxClient:
    del influxClient
if influxWriteAPI:
    del influxWriteAPI
logger.info("=============================================================")
logger.info("monitorViHP terminated")
logger.info("=============================================================")
