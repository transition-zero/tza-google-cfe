# TZ-Analysis-PyPSA: India
This folder contains the csv files used to create a PyPSA model for India.

PyPSA-India is an hourly-resolution power sector model. It can be used for:

- Dynamic dispatch modelling of power systems.
- Market pricing and intervention analysis.
- Power system capacity expansion planning.

## Overview
The PyPSA-India model is comprised of 5 nodes and 6 inter grid-zone links. Here, each node represents a regional power grid in the India National Grid, while each link represents the aggregated transmissions capacity between grid zones.

The model is setup and calibrated to run a 2023 dispatch year. Policy targets have also been setup to allow the model to run a 2030 NDC-compliant year.

## Model configuration

### Geographical scope
The 5 grid zones are as follows:

Grid zone       | Code
---             | ---                  
India East      | INDEA     
India North-East| INDNE   
India North     | INDNO   
India South     | INDSO   
India West      | INDWE                          

### Temporal resolution
PyPSA-India runs at an hourly resolution (i.e., 8760 timesteps). Other temporal resolutions are currently not supported.

### Data sources

- **Thermal and hydro plant capacities**: Pulled in from our internal TransitionZero Data Warehouse, which is in turn taken from [CEA](https://cea.nic.in) and matched with plants from Global Energy Monitor. Pipeline plants for 2030 are entered using information available from the CEA and [ICED](https://iced.niti.gov.in/).
- **Renewable plant capacities**: Manually downloaded from [ICED](https://iced.niti.gov.in/).
- **Solar capacity factors**: Chu and Hawkes (2020). State level averages are created using GEM location data.
- **Wind capacity factors**: Chu and Hawkes (2020). State level averages are created using GEM location data.
- **Hydro capacity factors**: [ICED](https://iced.niti.gov.in/) - historical 2023 factors used for 2023 calibration
- **Biomass/bagasse capacity factors**: [ICED](https://iced.niti.gov.in/) - historical 2023 factors used for 2023 calibration. Note bagasse plants are assumed captive and therefore have near-zero marginal cost.
- **Technology costs**: CEA & DEA Indian Technology Catalogue, available [here](https://cea.nic.in/wp-content/uploads/irp/2022/02/First_Indian_Technology_Catalogue_Generation_and_Storage_of_Electricity-2.pdf) and [here](https://mnre.gov.in/en/document/indian-technology-catalogue-generation-and-storage-of-electricity-by-cea/). IEA World Energy Outlook was used to supplement any gaps in information.
- **Coal plant variable costs**: [IEA Projected Costs of Generating Electricity (2020)](https://www.iea.org/reports/projected-costs-of-generating-electricity-2020) has been used for ultracritical coal plants, adjusted for inflation according to the India CPI. Prices for other coal boiler types have been derived using the ratios in their efficiencies.
- **Coal prices (alternate)**: Coal India [price notification 2023](https://www.cercind.gov.in/coal_price_index_base.html).
- **Nuclear plant variable costs**: [IEA Projected Costs of Generating Electricity (2020)](https://www.iea.org/reports/projected-costs-of-generating-electricity-2020) has been used, adjusted for inflation according to the India CPI.
- **Gas prices**: India has a limited supply of domestic gas, and also imports LNG. LNG Asia spot price has been assumed.
- **Biomass prices**: Determined through looking at state-level tariffs, e.g. [CERC RE Tariff Order for FY 2022-23](https://cercind.gov.in/2022/orders/14-SM-2022.pdf).
- **Ramping rates/min up and down times**: CEA & DEA Indian Technology Catalogue, available [here](https://cea.nic.in/wp-content/uploads/irp/2022/02/First_Indian_Technology_Catalogue_Generation_and_Storage_of_Electricity-2.pdf).
- **2030 demand**: Total demand in 2030 is taken from [Report on Optimal Generation Mix 2030](https://cea.nic.in/wp-content/uploads/notification/2023/05/Optimal_mix_report__2029_30_Version_2.0__For_Uploading.pdf) from the CEA. Demand curves have been scaled up linearly, with the demand shape remaining the same.
- **2030 transmission build**: Taken from [Rolling Plan: Interstate transmission system 2028-29](https://www.ctuil.in/uploads/annual_rolling_plan/171636414536Final%20Report_Print%20Verison.pdf) from CTUIL.

### Policy targets
In addition, there is a `power_sector_targets.csv` file to define NDC targets such as emissions and minimum capacity targets for 2030. This file also defines renewables potentials, upper limits of buildouts due to technological limitations or state targets.
