# hacs-idm-hpweb
HACS integration for IDM heat pumps by using just the WEB interface

> [!IMPORTANT]
> This integration is not affiliated with iDM Energiesysteme GmbH and is provided as-is and without warranty.

# IDM heat pump web integration

[![License][license-shield]](LICENSE)

_Component to integrate with [IDM heat pumps][https://www.idm-energie.at/]._

> [!NOTE]
> Your heat pump needs to have the Navigator 2.0 control unit.
> Other versions of the control unit may not work correctly.

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show other info from the heat pump.

## What is IDM heat pump web integration

1. This integration uses the local HTTP Web server, which comes now with all iDM heat pumps with Navigator 2.0.
2. It do not use the iDM Web service nor is dependent on any iDM regsitration or internet or cloud service. All data is still collected local in your network
3. To make this integration work, your iDM heat pump has a static IP address or you configured your network router in a way it always assigns the same ip address. You use the IP address as the host name for the integration
4. This integration needs the PIN code from you iDM heat pump to open the HTTP connection. If no PIN code is assigned, to local HTTP server is disabled, activate a PIN on the iDM heatpump display
5. This integration do not provide all entities iDM heat pump can provide, not gives up to now any control. However the provided entities enriches other integration.
6. This integration is actually a compantion designed to work together with the popular Kodebach iDM Integration see https://github.com/kodebach/hacs-idm-heatpump
7. This integration will even run, if ModbusTCP protocol is not yet activated by your iDM service team. However I recommend to do so, to be able to run this integration together with the Kodebach integration


## What is the difference to already existing integrations for iDM heat pumps

1. This integration uses standard HTTP get and push commands to retries the data and provide it to Home Assistant via Entries.
2. This integration tries to discover the entities themself and just add the entities, provided by your heatpump.
3. Since the standard iDM Web server expects a 10 seconds update cycle, this is the default for this integration. I allow to lower this to 2 seconds. I tried it without a glich with 5 seconds update cycle. Or course you could slow down the update cycle to relax Home Assistant entity handling. But the iDM interface and this integration has no issue with higher update rates.
4. This is a contract to ModbusTCP based integrations. ModbusTCP can of course have faster update rates, however the way Home Assistant implements it and the way iDM has integrated it, allows a update rate by best 30 seconds. If you have a higher update rate, the iDM GUI and control can go static and the heatpump freezes. Recommended update rate is 1 min lowest. This might be quite slow for some Home Assistant controled temperature handling. This integration gives you the needed higher update rate for such conditions.
5. iDM designed ModbusTCP as the interface for the heat pump. Therefore use the Kodebach integration as the main integration. However iDM lacks a few very important sensors on the ModbusTCP implementation. They are not willing to add them, even requesting them. This integration bridges the flaw, and adds: flowrate, hotgas temperature, compressor high and low pressure values and many more.
6. As already mentioned, this integration is designed and implemented to run in parallel with a standard Modbus based integration for the heat pump like the one from Kodebach. By disabling sensors not needed in this integration, you could greatly relax Home Assistant data handling and still allow to have the few sensors of your interests, e.g. flowrate or hotgas temperature or flow temp and return temp on a high update rate. 

