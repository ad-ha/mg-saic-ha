[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ad-ha/mg-saic-ha?include_prereleases)
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ad-ha/mg-saic-ha/latest/total)

[![HACS Action](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml)


# MG/SAIC CUSTOM INTEGRATION

**Important Notes:** 
- **Using this integration causes the MG/SAIC mobile app to shut down, as per API requirements, since only one device can be connected at a time. Logging into the mobile app causes this integration to disconnect and fail to set up.**
- This Integration has only been tested on a MG Marvel R model. Please provide feedback on sensors and information for other vehicles.

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

You may add additional vehciles by following the same steps as above.


## SENSORS AVAILABLE

The MG/SAIC Custom Integration provides the following sensors and binary sensors:

### Sensors

- Brand
- Model
- Model Year
- Mileage
- Fuel Level
- Fuel Range
- EV SOC
- Electric Range
- HVAC Status
- Battery Voltage
- Interior Temperature
- Front Left Tyre Pressure
- Front Right Tyre Pressure
- Rear Left Tyre Pressure
- Rear Right Tyre Pressure


### Binary Sensors

#### DOORS ####
- Driver Door
- Passenger Door
- Rear Left Door
- Rear Right Door
- Bonnet Status
- Boot Status

#### WINDOWS ####
- Driver Window
- Passenger Window
- Rear Left Window
- Rear Right Window
- Sun Roof Status

#### OTHERS ####
- **Lock Status**


## Version History
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


## TO-DO

- Implement initial services for Locks action, HVAC control and anciliary services.
- Implement charging detection and corresponding sensors.
- Check API details for energy usage and stats, adding additional sensors.
- Check implementation against other EV/PHEV models.
- Add possibility to display metric or imperial data, including tyres' pressure.


## Contributing

Contributions are welcome! If you have any suggestions or find any issues, please open an [issue](https://github.com/ad-ha/mg-saic-ha/issues) or a [pull request](https://github.com/ad-ha/mg-saic-ha/pulls).

## Credits

This integration was made possible thanks to the [saic-ismart-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) repository and its developers/contributors.

## License

This project is licensed under the MIT License. See the LICENSE file for details.



## Disclaimer
THIS PROJECT IS NOT IN ANY WAY ASSOCIATED WITH OR RELATED TO THE SAIC MOTOR OR ANY OF ITS SUBSIDIARIES. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.
