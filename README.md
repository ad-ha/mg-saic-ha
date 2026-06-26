[![GitHub license](https://img.shields.io/github/license/ad-ha/mg-saic-ha)](https://github.com/ad-ha/mg-saic-ha/blob/main/LICENSE)
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ad-ha/mg-saic-ha?include_prereleases)
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/ad-ha/mg-saic-ha/latest/total)
[![GitHub stars](https://img.shields.io/github/stars/ad-ha/mg-saic-ha?style=flat)](https://github.com/ad-ha/mg-saic-ha/stargazers)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-green.svg)](https://github.com/hacs/default)
[![HACS Action](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/validate.yaml)
[![Hassfest](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ad-ha/mg-saic-ha/actions/workflows/hassfest.yaml)
[![Integration Usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.mg_saic.total)](https://analytics.home-assistant.io/)

![Logo](brand/icon.png)


</br></br>
# MG/SAIC CUSTOM INTEGRATION

<a href="https://buymeacoffee.com/Townsmcp" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

**Important Notes:** 
- **Using this integration causes the MG/SAIC mobile app to shut down if the same account is used, as per API requirements.**
- **To avoid issues, make sure to setup a Secondary Account on iSmart App.**

**Requirements:**
- Home Assistant 2024.06 or later.
- Confirmed compatible with Python 3.14, the runtime used by current Home Assistant core releases (2026.3+). No action needed on your part — this is handled automatically by Home Assistant on supported installation methods.

## INSTALLATION

### HACS (Home Assistant Community Store)

1. Ensure that HACS is installed.
2. Go to HACS
3. Search for "MG SAIC" and download the repository.
4. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the [MG SAIC Custom Integration GitHub repository](https://github.com/ad-ha/mg-saic-ha/releases).
2. Unzip the release and copy the `mg_saic` directory to `custom_components` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## CONFIGURATION

To add the integration to your local Home Assistant, click here:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ad-ha&repository=mg-saic-ha&category=integration)

Install the integration, restart Home Assistant and then add the integration, either:

[<img src="https://github.com/user-attachments/assets/36459daa-a780-448a-82a5-19ee07ccd3f6">](https://my.home-assistant.io/redirect/config_flow_start?domain=mg_saic)

Or manually by:

1. Go to Configuration -> Integrations.
2. Click on the "+ Add Integration" button.
3. Search for "MG SAIC" and follow the instructions to set up the integration.
4. Select your type of account (email or phone), enter the details and select your region (EU, China, Australia, Turkey, Rest of World)
5. Once connected to the API, a list of available VINs associated with your account will be shown. Select the vehicle that you want to integrate and finish the process.



You may add additional vehicles by following the same steps as above.
 
### Multiple Vehicles
 
If you have more than one MG/SAIC vehicle, you can add each one as a separate integration entry. Vehicles on the **same SAIC account** are fully supported — the integration uses a single shared API session per account, so adding a second vehicle does not interfere with the first.
 
If your vehicles are on different SAIC accounts, add each account separately in the same way.


## SENSORS AVAILABLE
 
The MG/SAIC Custom Integration provides the following sensors, binary sensors, and controls. Not all entities are available on every vehicle — availability depends on vehicle type (BEV, PHEV, HEV, ICE) and optional equipment.
 
### SENSORS
 
#### General
- Brand
- Model
- Model Year
- Mileage
- Interior Temperature
- Exterior Temperature
- Battery Voltage (12V)
- Speed
- Power Mode
- Last Key Seen *(raw key fob identifier; shown as Unknown when key is not present)*
- Last Powered On
- Last Powered Off
- Last Vehicle Activity
- Last Update Time
- Next Update Time
#### Tyre Pressure
- Front Left Tyre Pressure
- Front Right Tyre Pressure
- Rear Left Tyre Pressure
- Rear Right Tyre Pressure
#### Electric / Hybrid
- EV State of Charge (SOC)
- Electric Range
- Instant Power *(kW draw/regen while driving; negative = traction, positive = regen/charge)*
- Fuel Level *(PHEV/HEV/ICE only)*
- Fuel Range *(PHEV/HEV/ICE only)*
#### Climate
- HVAC Status
- Front Left Heated Seat Level *(if equipped)*
- Front Right Heated Seat Level *(if equipped)*
- Steering Wheel Heat *(if equipped)*
#### Charging Data *(BEV/PHEV)*
- Charging Status *(Unplugged / Charging (AC) / Charging (DC) / V2X Discharging / …)*
- Charging Voltage
- Charging Current
- Charging Current Limit
- Charging Power
- Estimated Range After Charging
- Charging Target SOC *(shown only on models where the iSmart app supports it)*
- Charging Duration
- Remaining Charging Time
- Added Electric Range
- Power Usage Since Last Charge
- Mileage Since Last Charge
- Total Battery Capacity *(kWh; corrected for models where the API reports an inaccurate value)*
- Last Charge Ending Power *(kWh; corrected for models where the API reports an inaccurate value)*
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
- Sunroof Status *(if equipped)*
#### Other
- Lock Status
- Charging Gun Status
### EVENTS
 
- **Command Error** — fired when a remote command (lock, AC, charge, etc.) fails or is rejected by the vehicle. Use this in automations to get notified when a command does not go through.
### DEVICE TRACKER
- Latitude
- Longitude
- Elevation (Altitude)
- HDOP
- Satellites
- Heading
- Raw Heading
### SWITCHES
- Charging Start/Stop
- Battery Heating *(if equipped)*
- Front Defrost
- Rear Window Defrost
- Heated Seats *(if equipped)*
- Sunroof *(if equipped)*
- Charging Port Lock
### BUTTONS
- Trigger Find My Car Alarm
- Update Vehicle Data
### LOCK
- Lock entity for door lock/unlock
- Boot/Tailgate lock entity
### CLIMATE
- AC Control Climate entity
  * Temperature
  * Fan Speed
  * HVAC mode (Cool / Fan Only / Off)
### SLIDERS
- Target SOC *(shown only on models where the iSmart app supports it)*
### SELECT
- Charging Current Limit
- Heated Seats Level *(if equipped)*
**Note: Actions (Services) can be accessed and activated from the Actions menu under Developer Tools.**
![image](https://github.com/user-attachments/assets/14be0d41-ae65-4738-8bc0-5b0f743c290f)
 
 
## Climate Control
 
The MG SAIC integration exposes a climate entity for remote control of the vehicle's air conditioning. Because SAIC limits remote commands to **3 per cycle between starting the car with a key**, the integration is designed to use commands as efficiently as possible.
 
### How commands are used
 
The SAIC API counts each instruction sent to the car as one command. To avoid wasting your allowance, only explicit HVAC mode changes send a command. Adjusting fan speed or temperature on their own does not.
 
**Uses a command:**
- Turning the AC on (HVAC mode set to `Cool` or `Fan Only`)
- Turning the AC off (HVAC mode set to `Off`)
- Switching between `Cool` and `Fan Only`
**Does NOT use a command:**
- Changing fan speed (`Low`, `Medium`, `High`)
- Changing target temperature
### Recommended usage
 
Set your preferred temperature and fan speed **first**, then turn the AC on. The command sent to the car will include whatever fan speed and temperature you have already set in HA. A complete remote pre-conditioning session uses exactly **2 commands** — one to turn on, one to turn off — leaving one spare for a lock or unlock action.
 
If you want to change temperature or fan speed while the AC is already running, update the values in HA first, then turn the AC off and back on. This applies your new settings using 2 commands.
 
### Fan speeds
 
| HA setting | Behaviour |
|---|---|
| Low | Gentle airflow |
| Medium | Default when turning on |
| High | Maximum normal fan speed |
 
> **Note:** Fan speed values used internally vary by vehicle model. The integration automatically selects the correct values for your car based on its series. The Front Defrost command uses a separate API speed value and is never accidentally triggered by fan speed changes.
 
### HVAC modes
 
| Mode | Behaviour |
|---|---|
| `Cool` | Runs the compressor with your chosen temperature and fan speed |
| `Fan Only` | Runs the fan without the compressor (blowing only) |
| `Off` | Stops all climate activity |
 
 
## Event-Driven Updates
 
The integration polls the SAIC alarm message queue once per minute per account and automatically triggers an immediate data refresh when it detects:
 
- **Engine start** — data refreshes as soon as the car is driven away
- **Vehicle shutdown** — data refreshes after the car is turned off
- **Charging plug-in** — data refreshes when charging begins
This means you can set a long polling interval (e.g. 30 minutes or more) for idle/parked state and still get near-real-time updates when the car is active.
 
> **Multiple vehicles on one account:** The integration uses a single API session and a single message poll loop per SAIC account, regardless of how many vehicles are registered under it. This prevents session conflicts and duplicate API calls.
 
 
## Vehicle Profiles
 
The integration includes built-in profiles for specific MG/SAIC models that correct known inaccuracies in the API data:
 
| Series | Model | Notes |
|---|---|---|
| `EH32` | MG4 Electric | Temperature range and fan speed values confirmed |
| `MIS3E` | MGS6 EV (Long Range / Dual Motor) | Battery capacity 74.3 kWh; inverted temperature index |
| `AS33P` | MG HS PHEV (Super Hybrid 2025/2026) | Battery capacity 24.7 kWh; Target SOC not supported by iSmart; electric range via estimated field |
 
Models not listed above use safe default values and should work normally. If you notice incorrect sensor readings for your model, please open an issue with your vehicle's debug logs.


## 💡 Troubleshooting & FAQ

* **"Invalid Credentials" or Connection Timeouts:** Ensure you are choosing the correct region (EU, China, Australia, Israel, Turkey, Rest of World) matching your mobile app setup.
* **Entities showing as 'Unavailable':** The integration respects API rate limits to prevent account lockouts. If an entity is temporarily unavailable, wait for the next scheduled update or use the `button.update_vehicle_data` entity to force a refresh.
* **My App keeps logging me out:** As noted above, ensure your Home Assistant integration uses a **Secondary Account**, not your primary mobile application credentials.
* **Target SOC entity is missing:** Some vehicle models (e.g. MG HS PHEV) do not support remote Target SOC setting via the iSmart API. The entity is intentionally not created for these models.
* **Electric Range shows an unexpected value:** For some PHEV models the live electric range field is not populated by the API. The integration falls back to the estimated-range-after-full-charge figure from the charging management data.
* **Two cars on the same account:** Fully supported. Both vehicles share a single API session so neither interferes with the other.
* **Instant Power sensor shows a stale value after HA restart:** Home Assistant restores entity states from its database on startup. The value will update to `0 kW` on the first successful poll (usually within 30 seconds) if the car is not driving.

## How to enable logging

* Add the following lines to `configuration.yaml` (or your sub `logger.yaml` file if you have broken down `configuraiton.yaml` into smaller files)
  ```
  logger:
  default: warning
  
  logs:
    custom_components.mg_saic: debug
  ```
* Restart Home Assistant
* Go to System -> Logs
* Search for `mg_saic`
* Click the 3 vertical dots
* Choose `Show full logs`

## Contributing

Contributions are welcome! If you have any suggestions or find any issues, please open an [issue](https://github.com/ad-ha/mg-saic-ha/issues) or a [pull request](https://github.com/ad-ha/mg-saic-ha/pulls).

## Credits

This integration was made possible thanks to the [saic-ismart-client-ng](https://github.com/SAIC-iSmart-API/saic-python-client-ng) repository and its developers/contributors.

## License

This project is licensed under the MIT License. See the LICENSE file for details.



## Disclaimer
THIS PROJECT IS NOT IN ANY WAY ASSOCIATED WITH OR RELATED TO THE SAIC MOTOR OR ANY OF ITS SUBSIDIARIES. The information here and online is for educational and resource purposes only and therefore the developers do not endorse or condone any inappropriate use of it, and take no legal responsibility for the functionality or security of your devices.
