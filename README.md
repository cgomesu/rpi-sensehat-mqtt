# rpi-sensehat-mqtt

## Introduction

The files here create a service on the _Raspberry Pi_ that works with the SenseHAT from the [astro-pi](https://astro-pi.org/) project and streams its data over MQTT.

This service works on all the Raspberry Pi flavors, as long as they support the SenseHAT.

## Official docs

- [RPi SenseHAT](https://www.raspberrypi.com/documentation/accessories/sense-hat.html)
- [SenseHAT Python Module](https://pythonhosted.org/sense-hat/)

## Folder structure

The files are here structured in this way:

- `rpi_sensehat_mqtt.py` python script to read the sensors and publish over MQTT
- `rpi_sensehat_mqtt.logrotate` configuration for [logrotate](https://manpages.debian.org/stretch/logrotate/logrotate.8.en.html) to rotate the log file of this script
- `rpi_sensehat_mqtt.env` file to define the environmental variables used while running the background service
- `rpi_sensehat_mqtt.service` file to run the background service
- `setconfiguration.sh` script to configure the system and properly propagate the files in the right folders

## How-to

The main python script `rpi_sensehat_mqtt.py` does the following operations when it runs:

- Reads sensor data
- Creates the MQTT message
- Publish it on the broker

The script logs its operations in the file `/var/log/rpi_broadcaster/rpi_sensehat_mqtt.log`.

The script requires a configuration through environmental variables defined in the `rpi_sensehat_mqtt.env` file.
The available configuration parameters are:

- `RPI_SENSEHAT_MQTT_LOGLEVEL="<desired loglevel>"` the desired log level to be used in the log, as defined by the [python library](https://docs.python.org/3/library/logging.html#levels)
- `RPI_SENSEHAT_MQTT_CYCLE=<desired timecycle>` the desired time cycle
- `RPI_SENSEHAT_MQTT_LOCATION="<desired location>"` to set the location in the message
- `RPI_SENSEHAT_MQTT_BROKER="protocol://address:port"` endpoint of the broker
- `RPI_SENSEHAT_MQTT_TOPIC_PREFIX="<desired prefix>"` to set the prefix for all the topics (default `sensehat`): `readings` is used for the readings and `commands` to process input commands
- `RPI_SENSEHAT_MQTT_MEASUREMENT="<desired measurement>"` measurement name
- `RPI_SENSEHAT_MQTT_WELCOME="<desired welcome message>"` welcome message at startup

## Install

1. Follow the official docs [to install the `sense-hat` package](https://www.raspberrypi.com/documentation/accessories/sense-hat.html#installation). (Make sure `I2C` was enabled afterwards; otherwise, run `sudo raspi-config` and manually turn it on.)

1. Test it by running one or more of the Python demos at `/usr/src/sense-hat/examples/python-sense-hat` (`Ctrl+c` to stop):

	```sh
	./usr/src/sense-hat/examples/python-sense-hat/rainbow.py
	```

1. (Optional.) [Callibrate the magnetometer](https://www.raspberrypi.com/documentation/accessories/sense-hat.html#calibration). (This will install many additional packages and will take some time to complete.)

1. On the target machine, clone this repository:

	```sh
	sudo apt install git
	git clone https://github.com/cgomesu/rpi-sensehat-mqtt.git
	```

1. Install the requisites:

	```sh
	sudo apt install python3 python3-pip
	pip3 install --upgrade pip
	pip3 install -r requirements.txt
	```

1. Make sure your `$USER` can find its Python modules by adding `~/.local/bin` to its `$PATH`.

1. Edit the environmental variables in `rpi_sensehat_mqtt.env` to match your configuration (see [How-To](#how-to)).

1. Run the following command:

	```sh
	cd rpi-sensehat-mqtt/
	sudo bash ./setconfiguration.sh
	```

1. After this has been successfully executed the new service is already running, and it can be managed using:

	```sh
	sudo systemctl <command> rpi_sensehat_mqtt.service
	```

[top](#)
