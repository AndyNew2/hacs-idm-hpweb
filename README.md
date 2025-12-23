# hacs-idm-hpweb
HACS integration for IDM heat pumps by using just the WEB interface

> [!IMPORTANT]
> **This integration is not affiliated with iDM Energiesysteme GmbH and is provided as-is and without warranty.**

# IDM heat pump web integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

_Component to integrate with [IDM heat pumps][https://www.idm-energie.at/]._

> [!NOTE]
> Your heat pump needs to have the **Navigator 2.0** control unit.
> Other versions of the control unit will not work at all. A try is not recommended.

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show other info from the heat pump.

## Introduction - what is this home assistant integration about

### What is IDM heat pump web integration

1. This integration uses the **local HTTP Web** server, which comes now with all iDM heat pumps with **Navigator 2.0**.
2. It do not use the iDM Web service nor is dependent on any iDM regsitration or **internet or cloud service**. All data is still collected **local in your network**.
3. To make this integration work, your iDM heat pump need to have a **static IP** address or you configured your network router in a way it always assigns the same **ip address**. Use the **IP address as the host** name for the integration.
4. This integration needs the **PIN code** from you iDM heat pump to open the HTTP connection. If no PIN code is assigned, the local HTTP on the heat pump is disabled. Activate a PIN on the iDM heatpump display.
5. This integration do not provide all entities iDM heat pump can provide, nor gives you any control. However, the provided entities enriches other integrations.
6. This integration is **actually a compantion**, designed to **work together** with the popular **Kodebach iDM Integration** see https://github.com/kodebach/hacs-idm-heatpump . However, it still can run standalone, but you will lack a lot of further information.
7. This integration will run without enabling ModbusTCP protocol by your iDM service team. However, I recommend to do so, to be able to run this integration together with the Kodebach integration.
8. See this Wiki for a picture, what you could see using this integration: https://github.com/AndyNew2/hacs-idm-hpweb/wiki.


### What is the difference to already existing integrations for iDM heat pumps, and why may I want to use it

1. This integration uses standard **HTTP get and push commands** to retries the data and provide it to Home Assistant via Entries.
2. This integration tries to discover the entities themself and just add the entities, provided by your heatpump.
3. Since the standard iDM Web server expects a **10 seconds update cycle**, this is the default for this integration. It can be **lowered to 2 seconds**. I tried it without a glich with 5 seconds update cycle. Of course, you could slow down the update cycle to relax Home Assistant entity handling. But the iDM interface and this integration has no issue with higher update rates.
4. This is very different to the ModbusTCP based integrations. ModbusTCP can of course have faster update rates, however the way Home Assistant implements it, and the way iDM has integrated it, allows a update rate by best 30 seconds. If you have a higher update rate, the iDM GUI and control can go static and the heatpump freezes. Recommended update rate is 1 min lowest. This might be quite slow for some Home Assistant controlled temperature handling. This integration gives you the needed higher update rate for such conditions. The heat pump itself is not stressed by the HTTP requests, but it is with ModbusTCP. (Maybe implementation specific and not a generic issue on ModbusTCP, however for the iDM heat pump this is true.)
5. iDM designed ModbusTCP as the interface for the heat pump. Therefore, use the **Kodebach integration as the main integration**. However, iDM lacks a few very important sensors on the ModbusTCP implementation. iDM till now, is not willing to add them. This integration bridges the flaw, and adds: **flowrate, hotgas temperature, compressor high and low pressure values** and many more.
6. As already mentioned, this integration is designed and implemented to run in parallel with a standard ModbusTCP based integration for the heat pump like the one from Kodebach. By disabling sensors not needed in this integration, you could greatly relax Home Assistant data handling and still allow to have the few sensors of your interests, e.g. flowrate or hotgas temperature or flow temp and return temp on a high update rate. 


## Installation


### Install HACS Repository

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AndyNew2&repository=hacs-idm-hpweb&category=integration)

1. Install [HACS](https://hacs.xyz/) and complete its setup.
2. Open HACS and select "Integrations".
3. Add `AndyNew2/hacs-idm-heatpump` with category "Integration" as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/).
4. Select "iDM Heatpump Web" from the list and click "Download".

### Set up integration

[![Add integration to Home Assistant!](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=idm_hpweb)

The integration now appears like any other Home Assistant integration.
To set it up, follow these steps:

1. In the HA UI go to "Settings" -> "Devices & Services", click "+ Add Integration" in the bottom right corner, and search for "iDM Heatpump Web".
2. Make sure the heat pump is configured correctly (see below), then fill out the necessary details in the setup form. See Configuration using Config Flow below for more details.

### Manual Installation

Just create on your HA installation a subdir in homeassistant/custom_components
1. A subdir called idm_hpweb
2. Copy all files from here to that directory including subfolders like translations (probably the only one)
3. Restart Home Assistant
4. Go to devices, search now for idm_hpweb or "iDM Heatpump Web" device and follow the config flow, see next section

### Configuration using the Config Flow
5. In the config flow you need to enter the IP Address of your heat pump (the same you use to access the local Web GUI). Enter the IP Address in the field "Host"
6. In the PIN field enter the PIN number to enter the Web Interface. Make sure you have assigned a PIN number, otherwise the Web Interface is disabled. By default this is "4444"
7. Timeout and Update rate could be left to defaults or change it to your wishes.

Done the integration should check the access and start after that automatically and start creating detected entities to your system

## Recommendations & Tipps and Tricks

1. Install both integrations and use the Kodebach integration on 1 minute update rate or even slower to relax both HA and the iDM heat pump controller. In this integration use the standard update rate of 10 seconds or around to have a faster update on signals, needing the higher update rate.
2. Disable all entities in this integration, you do not need faster update rate and(!) having the entity anyway in the Kodebach integration. Good examples are flow temperature and return temperature. By disabling them in this integration, you greatly safe resources on the Home Assistant world, mainly the recorder.
3. Disable all entities in the Kodebach integration, you plan to use from this integration, in case you need the higher update rate. That prevents having the same information recorded twice in Home Assistant.

***

[commits-shield]: https://img.shields.io/github/commit-activity/y/AndyNew2/hacs-idm-hpweb.svg?style=for-the-badge
[commits]: https://github.com/AndyNew2/hacs-idm-hpweb/commits/master
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/AndyNew2/hacs-idm-hpweb.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/AndyNew2/hacs-idm-hpweb.svg?style=for-the-badge
[releases]: https://github.com/AndyNew2/hacs-idm-hpweb/releases
