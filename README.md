[![hacs_badge](https://img.shields.io/badge/HACS-Default-green.svg)](https://github.com/hacs/default)
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ad-ha/mg-saic-ha?include_prereleases)
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ad-ha/mg-saic-ha/latest/total)

[![HACS Action](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml)

![image](https://brands.home-assistant.io/brands/_/mg_saic/logo.png)

# MG/SAIC CUSTOM INTEGRATION

<a href="https://buymeacoffee.com/varetas3d" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

**Important Notes:** 
- **Using this integration causes the MG/SAIC mobile app to shut down if the same account is used, as per API requirements.**
- **To avoid issues, make sure to setup a Secondary Account on iSmart App.**

## INSTALLATION

### HACS (Home Assistant Community Store)

1. Ensure that HACS is installed.
2. Go to HACS
3. Search for "MG SAIC" and download the repository.
4. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the [MG SAIC Custom Integration GitHub repository](#).
2. Unzip the release and copy the `mg_saic` directory to `custom_components` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## CONFIGURATION

[<img src="https://github.com/user-attachments/assets/36459daa-a780-448a-82a5-19ee07ccd3f6">](https://my.home-assistant.io/redirect/config_flow_start?domain=mg_saic)


1. Go to Configuration -> Integrations.
2. Click on the "+ Add Integration" button.
3. Search for "MG SAIC" and follow the instructions to set up the integration.
4. Select your type of account (email or phone), enter the details and select your region (EU, China, Australia, Rest of World)
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
- Instant Power
- Speed
- Last Update TIme
- Next Update Time
- Front Left Heated Seat Level
- Front Right Heated Seat Level
- Last Powered Off
- Last Powered On
- Last Vehicle Activity

#### Tyre Pressure
- Front Left Tyre Pressure
- Front Right Tyre Pressure
- Rear Left Tyre Pressure
- Rear Right Tyre Pressure

#### Charging Data
- Charging Status
- Charging Voltage
- Charging Current
- Charging Current Limit
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
- Last Key Seen
- Last Update Time

### ACTIONS
- Lock Vehicle
- Unlock Vehicle
- Start Climate
- Start AC
- Stop AC
- Set Target SOC
- Set Charging Current Limit
- Open Tailgate
- Tigger Find My Car Alarm
- Start Charging (sometimes this service fails)
- Stop Charging
- Defrost Rear Window
- Defrost Windshield
- Control Heated Seats
- Control Battery Heating
- Update Vehicle Data

### DEVICE TRACKER
- Latitude
- Longitude
- Elevation (Altitude)
- HDOP
- Satellites
- Heading
- Raw Heading


### SWITCHES
- Front Defrost
- Rear Window Defrost
- Heated Seats
- Charging Start/Stop
- Battery Heating
- Sunroof
- Charging Port
- Individual Heated Seats

### BUTTONS
- Tigger Alarm
- Update Vehicle Data

### LOCK
- Lock entity for lock/unlock doors
- Boot/Tailgate lock entity

### CLIMATE
- AC Control Climate entity
  * Temperature
  * Fan Speed
  * Fan only mode

### SLIDERS
- Target SOC

### SELECT
- Charging Current Limit
- Heated Seats Level

**Note: Actions (Services) can be accessed and activated from the Actions menu under Developer Tools.**
![image](https://github.com/user-attachments/assets/14be0d41-ae65-4738-8bc0-5b0f743c290f)


## Contributing

Contributions are welcome! If you have any suggestions or find any issues, please open an [issue](https://github.com/ad-ha/mg-saic-ha/issues) or a [pull request](https://github.com/ad-ha/mg-saic-ha/pulls).

## Credits

This integration was made possible thanks to the [saic-ismart-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) repository and its developers/contributors.

## License

This project is licensed under the MIT License. See the LICENSE file for details.



## Disclaimer
THIS PROJECT IS NOT IN ANY WAY ASSOCIATED WITH OR RELATED TO THE SAIC MOTOR OR ANY OF ITS SUBSIDIARIES. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.
