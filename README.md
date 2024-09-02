# monitorViHP

The program periodically reads monitoring data from a Viessmann Heating System and stores these as measurements in an InfluxDB V2 database.

Viessmann Products are usually delivered with the [ViCare App](https://www.viessmann.de/de/produkte/steuerung-und-konnektivitaet/vicare-app.html) for visualization and control.   
This App includes visualization of time series data for the overall energy balance.

For more detailed analysis and visualization of system parameters over time, **monitorViHP** can collect the required time series data.

The [Viessmann Developer Portal](https://developer.viessmann.com/start.html) allows access to a variety of [Datapoints](https://documentation.viessmann.com/static/iot/data-points) which can be recorded over time with **monitorViHP**.

**monitorViHP** uses a **generic** approach for mapping Viessmann to Influx datapoints.
This allows monitoring virtually all accessible Viessmann data just by configuration.

[PyViCare](https://github.com/somm15/PyViCare) is used for interfacing and requesting a list of all features in a single transaction.   
This list is then analyzed with respect to the datapoints of interest, for which the details can be configured.   
The procedure requires just one transaction per time point and thus allows for 2 minute intervals to get along with the limit of 1.450 free transactions per day.

## Requirements

In order to use the program, you need

- a **[Viessmann Climate Solution](https://www.viessmann-climatesolutions.com/en.html)** with ViCare access.      
(*monitorViHP* has been developed and tested with a [Vitocal 250-A](https://www.viessmann.de/de/produkte/waermepumpe/vitocal-250-a.html) heatpump)
- a computer on which [**Docker**](https://www.docker.com/) is running (Windows PC, Linux, e.g. Raspi, NAS, ...), which is available for 24/7 operation.    
(This project has been deployed on a Synology DS220+ Disk Station)
- An **Influx DB V2.x** (eventally running as Docker container)
- Optionally, a **Grafana** instance for visualization (eventally running as Docker container)

If you are not already running a Docker Engine, see [Install Docker Engine](https://docs.docker.com/engine/install/).    
On NAS systems, Docker is usually available as App in the NAS OS.   
[InfluxDB](https://docs.influxdata.com/influxdb/v2/) is a time series database. *monitorViHP* currently only supports the free **V2.x** version of InfluxDB!   
[Grafana](https://grafana.com/) is an open source analytics and vizualization platform.

## Getting started

The following description assumes running all applications as Docker containers.   
You may alternatively run monitorViHP in a virtual Python environment from the command line (see [below](#running-monitorViHP-as-python-program)).

| Step | Action                                                                                                                                       |
|------|----------------------------------------------------------------------------------------------------------------------------------------------|
| 1.   | Install and configure an InfluxDB V2 (https://docs.influxdata.com/influxdb/v2/install/)                                                |
| 2.   | In InfluxDB, [create a new bucket](https://docs.influxdata.com/influxdb/v2/admin/buckets/create-bucket/). The *monitorViHP* default configuration assumes "ViHP"          |
| 3.   | In InfluxDB, [create an API Token](https://docs.influxdata.com/influxdb/v2/admin/tokens/create-token/) with write access to the bucket |
| 4.   | Prepare a ```config``` folder on a suitable location of the machine where Docker is installed. |
| 5.   | Download [monitorViHP_tpl.json](https://github.com/signag/monitorViHP/blob/main/config/monitorViHP_tpl.json) and store it as ```monitorViHP.json``` in the ```config``` folder prepared in step 4 |
| 6.   | Adjust the configuration file (see [Configuration](#configuration))<br>Essential adjustments are:<br>- ViCare credentials<br>- URL for the Influx DB<br>- Influx Org, Bucket and Token for ViCare data |
| 7.   | Run  the latest [monitorViHP](https://hub.docker.com/r/signag/monitorvihp) Docker image in a **Docker** container.<br>The container's ```/app/config``` directory must be mapped to the directory created in step 4.<br>From the command line, this can be done with<br>```docker run --name monitorvihp --mount type=bind,src=<configDir>,dst=/app/config signag/monitorvihp:latest```<br>where ```<configDir>``` must be replaced by the full path of the directory created in step 4.|
| 8.   | Check the container log for correct operation or any errors (you may need to wait for the next period which will be indicated in the log)|
| 9.   | In the Influx *Data Explorer*, check that data are being written to the ViHP bucket. |

## Gaining Access to ViCare Developer Portal

(See [PyViCare Prerequisites](https://github.com/somm15/PyViCare#prerequisites))

1. Login to the [Viessmann Developer Portal](https://app.developer.viessmann.com/) with your existing ViCare app username/password.
2. On the developer dashboard click add in the clients section.
3. Create a new client using following data:
   - Name: PyViCare
   - Google reCAPTCHA: Disabled
   - Redirect URIs: vicare://oauth-callback/everest
4. Copy the ```Client ID``` to use in the configuration, below

## Configuration

Configuration for **monitorViHP** needs to be provided in a specific configuration file.

**NOTE:** See [Running monitorViHP as Python Program](#running-monitorvihp-as-python-program) how you can test that a configuration file is valid.

By default, a configuration file "monitorViHP.json" is searched in the given sequence under ```$ROOT/config```, ```$HOME/.config``` or under ```/etc```. <br>Here, ```$ROOT``` is the project root directory and ```$HOME``` is the home directory of the user running the program.

For testing in a development environment, primarily the location ```$ROOT/tests/data``` is searched for a configuration file.

Alternatively, the path to the configuration file can be specified on the command line.

The **Docker** image expects a configuration file "monitorViHP.json" under ```/app/config``` which needs to be mapped to a directory in a container-external file system.

### Structure of JSON Configuration File

The following is an example of a configuration file:
A template can be found under
```$ROOT/config``` in the installation folder.

```json
{
    "measurementInterval": 120,
    "vicareClient_id": "",
    "vicareEmail": "",
    "vicarePassword": "",
    "vicareInstallation": "",
    "vicareDevice": "",
    "InfluxOutput": true,
    "InfluxURL": "",
    "InfluxOrg": "",
    "InfluxToken": "",
    "InfluxBucket": "ViHP",
    "csvOutput": false,
    "csvDir": "",
    "vicareData": [
        {
            "measurement": "heatpump",
            "csvFile": "heatpump.csv",
            "tags": [
                {
                    "name": "installation_id",
                    "value": {
                        "source": "cfg",
                        "feature": "vicareInstallation"
                    }
                },
                {
                    "name": "device_id",
                    "value": {
                        "source": "cfg",
                        "feature": "vicareDevice"
                    }
                }
            ],
            "fields": [
                {
                    "name": "outside_temperature",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.sensors.temperature.outside",
                        "formula": "properties['value']['value']",
                        "type": "float"
                    }
                },
                {
                    "name": "boiler_common_supply_temperature",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.boiler.sensors.temperature.commonSupply",
                        "formula": "properties['value']['value']",
                        "type": "float"
                    }
                }
            ]
        }
    ]
}
```

### Parameters

| Parameter               | Description                                                                           |
|-------------------------|---------------------------------------------------------------------------------------|
| measurementInterval     | Measurement interval in seconds. (Default: 120)                                       |
| vicareClient_id         | Client ID, gained in step 4 of [Gaining Access to ViCare Developer Portal](#gaining-access-to-vicare-developer-portal), above |
| vicareEmail             | E-mail address used for ViCare access                                                 |
| vicarePassword          | Password used for ViCare access                                                       |
| vicareInstallation      | ID of the installation.<br>See [Retrieving Installation Info](#retrieving-installation-info) how to get it.<br>The installation ID will only be used to tag data points, probably to be able to distinguish these from other installations |
| vicareDevice            | The device number. Typically "1". Used in a similar way asvicareInstallation |
| InfluxOutput            | Specifies whether data shall be stored in InfluxDB (Default: false)                   |
| InfluxURL               | URL for access to Influx DB                                                           |
| InfluxOrg               | Organization Name specified during InfluxDB installation                              |
| InfluxToken             | Influx API Token (see [Getting started](#getting-started))                            |
| InfluxBucket            | Bucket to be used for storage of ViCare data                                             |
| csvOutput               | Specifies whether ViCare data shall be written to a csv file (Default: false)            |
| csvDir                  | Path to the directory where csv files shall be located                                |
| **vicareData**          | List of configuration sets for Influx measurements to be created.<br>For explanation of the different elements, see [Getting Tag and Field Values from ViCare Features](#getting-tag-and-field-values-from-vicare-features), below.<br>For an example, see [monitorViHP_tpl.json](./config/monitorViHP_tpl.json).<br>See also [How to find Configurations for Data Points Of Interest](#finding-configurations-for-data-points-of-interest).|
|- measurement            | Influx **Measurement** to be used for data points of this configuration<br>The measurement name can be chosen freely but must be unique               |
|- csvFile                | Name of the csv file to which CSV data shall be written, if activated                 |
|- **tags**               | List of configurations for Influx tags to be used for data points of this measurement |
|- **fields**             | List of configurations for Influx fields to be used for data points of this measurement<br>Both configurations have the same structure: |
|-- name                  | Name for the tag or field.<br>The name can be chosen freely but must be unique. |
|-- **value**             | Rule for determining the value for the tag or field  |
|--- source               | Source where to get the value from.<br>May be<br>- "value" if the value is a constant value (only to be used for tags)<br>- "cfg" when referring to this configuration<br>- "vicare" if referring to a specific ViCare feature       |
|--- feature              | 'Feature' key depending on source:<br>- constant value<br>- key within this configuration<br>- ViCare feature key|
|--- formula              | Only for ```"source"="vicare"```: Python expression how to get the value from the ```properties``` of the ViCare feature.<br>See [monitorViHP_tpl.json](./config/monitorViHP_tpl.json) for examples |
|--- type                 | Type with which the value shall be stored in Influx.<br>- "int"<br>- "float"<br>- "str"

### Getting Tag and Field Values from ViCare Features

The JSON structure of ViCare features (see [How to get a List with ViCare Features](#how-to-get-a-list-with-vicare-features)) looks essentially like this:

```json
{
    "data": [
        {
            "feature": "heating.sensors.temperature.outside",
            "gatewayId": "xxxxxxxxxxxxxxxx",
            "deviceId": "0",
            "timestamp": "2024-07-01T13:28:03.057Z",
            "isEnabled": true,
            "isReady": true,
            "apiVersion": 1,
            "uri": "https://api.viessmann.com/iot/v1/features/installations/yyyyyyy/gateways/xxxxxxxxxxxxxxxx/devices/0/features/heating.sensors.temperature.outside",
            "properties": {
                "value": {
                    "type": "number",
                    "value": 20.7,
                    "unit": "celsius"
                },
                "status": {
                    "type": "string",
                    "value": "connected"
                }
            },
            "commands": {}
        },
        {
            "feature": "heating.boiler.sensors.temperature.commonSupply",
            "gatewayId": "xxxxxxxxxxxxxxxx",
            "deviceId": "0",
            "timestamp": "2024-07-01T13:26:41.522Z",
            "isEnabled": true,
            "isReady": true,
            "apiVersion": 1,
            "uri": "https://api.viessmann.com/iot/v1/features/installations/yyyyyyy/gateways/xxxxxxxxxxxxxxxx/devices/0/features/heating.boiler.sensors.temperature.commonSupply",
            "properties": {
                "value": {
                    "type": "number",
                    "value": 41.8,
                    "unit": "celsius"
                },
                "status": {
                    "type": "string",
                    "value": "connected"
                }
            },
            "commands": {}
        },
        {
            "feature": "heating.circuits.0",
            "gatewayId": "xxxxxxxxxxxxxxxx",
            "deviceId": "0",
            "timestamp": "2024-06-30T23:30:34.067Z",
            "isEnabled": true,
            "isReady": true,
            "apiVersion": 1,
            "uri": "https://api.viessmann.com/iot/v1/features/installations/yyyyyyy/gateways/xxxxxxxxxxxxxxxx/devices/0/features/heating.circuits.0",
            "properties": {
                "active": {
                    "type": "boolean",
                    "value": true
                },
                "name": {
                    "type": "string",
                    "value": "Heizkoerper"
                },
                "type": {
                    "type": "string",
                    "value": "heatingCircuit"
                }
            },
            "commands": {
                "setName": {
                    "uri": "https://api.viessmann.com/iot/v1/features/installations/yyyyyyy/gateways/xxxxxxxxxxxxxxxx/devices/0/features/heating.circuits.0/commands/setName",
                    "name": "setName",
                    "isExecutable": true,
                    "params": {
                        "name": {
                            "type": "string",
                            "required": true,
                            "constraints": {
                                "minLength": 1,
                                "maxLength": 20
                            }
                        }
                    }
                }
            }
        },
        {
            "feature": "heating.circuits.0.circulation.pump",
            "gatewayId": "xxxxxxxxxxxxxxxx",
            "deviceId": "0",
            "timestamp": "2024-07-01T11:55:22.471Z",
            "isEnabled": true,
            "isReady": true,
            "apiVersion": 1,
            "uri": "https://api.viessmann.com/iot/v1/features/installations/yyyyyyy/gateways/xxxxxxxxxxxxxxxx/devices/0/features/heating.circuits.0.circulation.pump",
            "properties": {
                "status": {
                    "type": "string",
                    "value": "off"
                }
            },
            "commands": {}
        },
    ]
}

```

From this list, **monitorViHP** retrieves information for Influx datapoints.

How this is done needs to be specified in the element ```vicareData``` of the [Configuration](#configuration).

### Example: Outside temperature

The ```fields``` specification for the outside temperature is

```
                {
                    "name": "outside_temperature",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.sensors.temperature.outside",
                        "formula": "properties['value']['value']",
                        "type": "float"
                    }
                },
```

### Example: Heating Circuit

```
        {
            "measurement": "circuit",
            "csvFile": "circuit.csv",
            "tags": [
                {
                    "name": "installation_id",
                    "value": {
                        "source": "cfg",
                        "feature": "vicareInstallation"
                    }
                },
                {
                    "name": "device_id",
                    "value": {
                        "source": "cfg",
                        "feature": "vicareDevice"
                    }
                },
                {
                    "name": "circuit_id",
                    "value": {
                        "source": "value",
                        "feature": "0"
                    }
                },
                {
                    "name": "circuit_name",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.circuits.0",
                        "formula": "properties['name']['value']"
                    }
                }
            ],
            "fields": [
                {
                    "name": "active",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.circuits.0",
                        "formula": "1 if properties['active']['value'] == True else 0",
                        "type": "int"
                    }
                },
                {
                    "name": "circulation_pump_active",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.circuits.0.circulation.pump",
                        "formula": "0 if properties['status']['value'] == 'off' else 1",
                        "type": "int"
                    }
                },
                {
                    "name": "temperature_supply",
                    "value": {
                        "source": "vicare",
                        "feature": "heating.circuits.0.sensors.temperature.supply",
                        "formula": "properties['value']['value']",
                        "type": "float"
                    }
                }
            ]
        },

```

Here, "installation_id", "device_id" and "circuit_id" are used as tags for Influx datapoints related to a specific heating circuit.   
The tag "circuit_id" is a constant here, because **monitorViHP** does not support loops in the configuration.

As additional informative tag, the "circuit_name" is used which is obtained from the feature ```"heating.circuits.0"```.

The active-status is obtained from the same feature but from property ```"active"```.    
Here, the boolean values of Vicare are translated to 0 or 1 for Influx.

## Running monitorViHP as Python Program

This option should be used when experimenting and testing with configurations for new data points before a configuration is exposed to the Docker container.

The program has especially a -t option for testing, which forces a cycle to start immediately without waiting for the configured interval.

In order to run monitorViHP (or other Python programs of this package) as Python program, proceed as follows:    
(Python 3.10 or later and Git must have been installed)

| Step | Action                                                                         |
|------|--------------------------------------------------------------------------------|
| 1.   | In the command shell of your system navigate to a suitable parent ($PARENT) folder |
| 2.   | Clone the monitorViHP repository<br>```git clone https://github.com/signag/monitorViHP``` |
| 3.   | Create and activate virtual Python environment<br>```cd monitorViHP```<br>```python -m venv .venv```<br><br>```.venv\Scripts\activate``` (Windows)<br>```source .venv/bin/activate``` (Linux)  |
| 4.   | Install necessary programs:<br>```pip install -r requirements.txt``` |
| 5.   | Start program:<br>```python monitorViHP/monitorViHP.py -h```<br>This should show the usage description (see [Usage](#usage)) |
| 6.   | Now, you can create a ```$PARENT/monitorViHP/tests/data``` folder, stage the configuration file and run a test with<br>```python monitorViHP/monitorViHP.py -t -v``` |

## Usage

(Not required when running the **Docker** image)

```shell
usage: monitorViHP.py [-h] [-t] [-s] [-l] [-L] [-F] [-p LOGFILE] [-f FILE] [-v] [-c CONFIG]
    This program periodically reads data from Viessmann ViCare controlling a heating system
    and stores these as measurements in an InfluxDB database.

    If not otherwises specified on the command line, a configuration file
       monitorViHP.json
    will be searched sequentially under ./tests/data, ./config, $HOME/.config or /etc.

    This configuration file specifies credentials for ViCare access,
    the connection to the InfluxDB and datapoint definitions.

  -h, --help            show this help message and exit
  -t, --test            Test run - single cycle - no wait
  -s, --service         Run as service - special logging
  -l, --log             Shallow (module) logging
  -L, --Log             Deep logging
  -F, --Full            Full logging
  -p LOGFILE, --logfile LOGFILE
                        path to log file
  -f FILE, --file FILE  Logging configuration from specified JSON dictionary file
  -v, --verbose         Verbose - log INFO level
  -c CONFIG, --config CONFIG
                        Path to config file to be used
```

## Retrieving Installation Info

This package includes a small [getViCareInstallation.py](./tryViCareApi/getViCareInstallation.py) Python program which can be used to get information on your installation from ViCare.

Before usage, copy this file to ```$PARENT/tests```.
(```$PARENT/tests``` is ignored by git)

1. Edit ```$PARENT/tests/getViCareInstallation.py``` and set 'client_id', 'email' and 'password' for your ViCare access (See [Gaining Access to ViCare Developer Portal](#gaining-access-to-vicare-developer-portal))
2. Change to the ```$PARENT/monitorViHP``` directory and activate the virtual environment, if not already done:<br>```.venv\Scripts\activate``` (Windows)<br>```source .venv/bin/activate``` (Linux)
3. Run the program:<br>```python tests/getViCareInstallation.py```<br>The program will print out general information on your installation, among others: the **Installation ID**

## How to get a List with ViCare Features

This package includes a small [getViCareAllFeatures.py](./tryViCareApi/getViCareAllFeatures.py) Python program which can be used to generate a list of features available for a device.

Before usage, copy this file to ```$PARENTDIR/tests```.
(```$PARENTDIR/tests``` is ignored by git)

1. Set 'client_id', 'email' and 'password' for your ViCare access (See [Gaining Access to ViCare Developer Portal](#gaining-access-to-vicare-developer-portal))
2. Change to the ```$PARENT/monitorViHP``` directory and activate the virtual environment, if not already done:<br>```.venv\Scripts\activate``` (Windows)<br>```source .venv/bin/activate``` (Linux)
3. Run the program:<br>```python tests/getViCareAllFeatures.py```<br>The program will generate a ```$PARENTDIR/tests/features.json``` file with all available ViCare features.
