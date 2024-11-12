[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ad-ha/mg-saic-ha?include_prereleases)
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ad-ha/mg-saic-ha/latest/total)

[![HACS Action](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml)

![image](https://brands.home-assistant.io/brands/_/mg_saic/logo.png)

# MG/SAIC CUSTOM INTEGRATION

<a href="https://buymeacoffee.com/varetas3d" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

**Important Notes:** 
- **Using this integration causes the MG/SAIC mobile app to shut down, as per API requirements, since only one device can be connected at a time. Logging into the mobile app causes this integration to disconnect and fail to set up.**
- Please provide feedback on sensors and information for other vehicles.

## INSTALLATION

### HACS (Home Assistant Community Store)

1. Ensure that HACS is installed.
2. Go to HACS
3. On the top right menu select "Custom repositories"

  ![image](https://github.com/user-attachments/assets/c89651bc-76c2-4c62-b7e2-f9dd11592f84)

4. On the "Repository" field put the URL https://github.com/ad-ha/mg-saic-ha. On the "Category" select "Integration" and click "ADD"

  ![image](https://github.com/user-attachments/assets/7b6ed323-58f3-489f-9d32-c0d41fd5afeb)

6. Search for "MG SAIC" and download the repository.
7. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the [MG SAIC Custom Integration GitHub repository](#).
2. Unzip the release and copy the `mg_saic` directory to `custom_components` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## CONFIGURATION

[<img src="https://github.com/user-attachments/assets/36459daa-a780-448a-82a5-19ee07ccd3f6">](https://my.home-assistant.io/redirect/config_flow_start?domain=mg_saic)


1. Go to Configuration -> Integrations.
2. Click on the "+ Add Integration" button.
3. Search for "MG SAIC" and follow the instructions to set up the integration.
4. Select your type of account (email or phone), enter the details and select your region (EU, Asia, China)
5. Once connected to the API, a list of available VINs associated with your account will be shown. Select the vehicle that you want to integrate and finish the process.

You may add additional vehicles by following the same steps as above.


## SENSORS AVAILABLE

The MG/SAIC Custom Integration provides the following sensors and binary sensors:

### SENSORS

#### General
- Brand
- Model
- Model Year
- Mileage
- Fuel Level
- Fuel Range
- EV SOC
- Electric Range
- Battery Voltage
- HVAC Status
- Interior Temperature
- Exterior Temperature

#### Tyre Pressure
- Front Left Tyre Pressure
- Front Right Tyre Pressure
- Rear Left Tyre Pressure
- Rear Right Tyre Pressure

#### Charging Data
- Charging Status
- Charging Voltage
- Charging Current
- Charging Power
- Estimated Range After Charging
- Charging Target SOC
- Charging Duration
- Remaining Charging Time
- Added Electric Range
- Power Usage Since Last Charge
- Mileage Since Last Charge


### BINARY SENSORS

#### Doors
- Driver Door
- Passenger Door
- Rear Left Door
- Rear Right Door
- Bonnet Status
- Boot Status

#### Windows
- Driver Window
- Passenger Window
- Rear Left Window
- Rear Right Window
- Sun Roof Status

#### Others
- Lock Status
- Charging Gun Status

### ACTIONS
- Lock Vehicle
- Unlock Vehicle
- Start AC
- Stop AC
- Set Target SOC
- Open Tailgate
- Tigger Find My Car Alarm
- Start Charging (sometimes this service fails)
- Stop Charging
- Defrost Rear Window
- Defrost Windshield
- Control Heated Seats
- Control Battery Heating
- Update Vehicle Data
 
### SWITCHES
- AC On/Off
- Heated Seats
- Charging Start/Stop
- Battery Heating

### BUTTONS
- Open Tailgate
- Start Front Defrost
- Start Rear Window Heat
- Tigger Alarm
- Update Vehicle Data

### LOCK
- Lock entity for lock/unlock doors

### CLIMATE
- AC Control Climate entity
  * Temperature
  * Fan Speed

### SLIDERS
- Target SOC

**Note: Actions (Services) can be accessed and activated from the Actions menu under Developer Tools.**
![image](https://github.com/user-attachments/assets/14be0d41-ae65-4738-8bc0-5b0f743c290f)


## Version History
```
0.4.6
- Fix generic responses being parsed and not caught on exceptions
```

```
0.4.5
- Revise code for setup of Fuel Level and Fuel Range sensors on ICE vehicles.
- Add new "Update Vehicle Data" service, for manual updates.
- Add new "Update Vehicle Data" button
- Refactor Generic Response handling and retrying, to trigger on manual updates
- Improve exceptions' handling on Generic Responses
- Revise translations and typos.
```

```
0.4.4
- Refactor setup to avoid generic responses from blocking integration startup
- Revise Generic Response verification method
- Revise Charging Gun State sensor mechanics for BEV and PHEV only.
- Additional Debug Logging for Generic Responses
```

```
0.4.3
- Revise Generic Response verification method to discard responses with SOC over 100%
```

```
0.4.2
- Revise Vehicle Type mechanics. Avoid overriding user selection from configuration process
- Revise SOC sensor data retrieval. Now main data will be obtained from Charging Data and fallback on Basis Status.
- Revise sensors available for BEV, PHEV and HEV.
- Refactor data updates on initial setup and update intervals
- Refactor data calculations for Charging Current and Charging Voltage sensors
- Add Charging Power (kW) sensor
- Adjust climate entity issues. Actionable mode COOL/OFF only, correcting the raised error from HA.
- New Actions and Switch entities:
  * Battery Heating
- Revise translation files for Config Flow, since some labels were missing.
- Adjust charging status messages from API.
- Bump saic-ismart-client-ng to 0.5.2
```

```
0.4.1
- Add new platforms to the integration
- New Switch entities:
  * AC On/Off
  * Heated Seats
  * Charging Start/Stop
- New Button entities
  * Open Tailgate
  * Start Front Defrost
  * Start Rear Window Heat
  * Tigger Alarm
- New Lock entity
  * Lock entity for lock/unlock doors
- New Climate entity
  * AC Control Climate entity
    - Temperature
    - Fan Speed
- New Slider entity
  * Target SOC
- Revise API methods to identify some vehicle info and show sensors/actions accordingly. 
  (limited to some areas only, as API is not fully reliable on data provided)
```

```
0.3.0
- Refactor usage of DataCoordinator to address issues with Update Intervals. Hopefully closes #10 
- Refactor code to address issues with `No entity id specified`
- Refactor State of Charge sensor to try to retrieve data from ChargingData if StatusData is not available. Hope it closes #8 
- Add new **Set Target SOC** service.
- Revise Debug logs generation to avoid duplicated entries
```
 
```
0.2.1
- Revised vehicle type identification mechanics and conditions - closes SOC not showing in HA #6
- Added new step to config_flow to allow users to select the correct vehicle type if the integration fails to do so based on API data - closes SOC not showing in HA #6
- Added configuration options to the integration to manually change the update intervals.
- Revised translations
```

```
0.2.0
- Revised mechanics for connection with API and data retrieval
- Services testing and adjusting to API requirements
- Renamed and revised sensor data and info
- Revise units for sensors and adapting all sensors to SensorDeviceClass from Home Assistant
- Revise Unique ID generation for all sensors
- Revise Login method to avoid blocking calls during startup
- Improve detection and discard of "Generic Responses" during API setup and updates
- Improve vehicle type detection on integration setup.
```
 
```
0.1.0
- Refactor code to work with data coordinator
- Revised mechanics for connection with API and data retrieval
- Update saic-python-client-ng requirements to version 0.2.3
- Added new sensors for charging data
- Renamed and revised sensor data and info
- Revise config_flow to allow login with phone and email
- Initial implementation of services (some services still not available, but are implemented as a proof of concept). _Feedback on this will be helpful_
- Change update interval to 5 minutes once charging is detected
- Refactor API responses and values as needed. Charging sensors only display data if Charging is Active, otherwise 0 will be displayed
- Fuel Level, Fuel Range, EV State of Charge and Electric Range are vehicle dependent. Add logic to determine the vehicle type and show sensors accordingly.
```

```
0.0.2
- Revised mechanics for connection with API
- Added new sensors (Brand, Model and MY)
- Rename sensors based on Brand and Model
- Rename sensors to have them grouped by type (windows, doors, tyres...)
- Revise config_flow (_login with phone still not working and unavailable_)
- Initial trialing for charging details 
```

```
0.0.1
- Initial release
```

## Contributing

Contributions are welcome! If you have any suggestions or find any issues, please open an [issue](https://github.com/ad-ha/mg-saic-ha/issues) or a [pull request](https://github.com/ad-ha/mg-saic-ha/pulls).

## Credits

This integration was made possible thanks to the [saic-ismart-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) repository and its developers/contributors.

## License

This project is licensed under the MIT License. See the LICENSE file for details.



## Disclaimer
THIS PROJECT IS NOT IN ANY WAY ASSOCIATED WITH OR RELATED TO THE SAIC MOTOR OR ANY OF ITS SUBSIDIARIES. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.
