# Ternopil Grid Schedule (Home Assistant)

![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)
![Version](https://img.shields.io/github/v/release/yshved-stack/ternopil-grid-schedule)
![License](https://img.shields.io/github/license/yshved-stack/ternopil-grid-schedule)
![hassfest](https://img.shields.io/github/actions/workflow/status/yshved-stack/ternopil-grid-schedule/hassfest.yml?branch=main)
![HACS](https://img.shields.io/github/actions/workflow/status/yshved-stack/ternopil-grid-schedule/hacs.yml?branch=main)
![Tests](https://img.shields.io/github/actions/workflow/status/yshved-stack/ternopil-grid-schedule/tests.yml?branch=main)

Planned outage schedule + ultra-fast power detection via TCP keep-alive ping to a smart plug (2–3s reaction).

## Features
- Outage group selection (1.1..6.7) via UI (select entity)
- TCP ping power detection:
  - `binary_sensor.ternopil_grid_power`
- Schedule entities:
  - `binary_sensor.ternopil_grid_planned_outage`
  - `sensor.ternopil_grid_next_change`
  - `sensor.ternopil_grid_countdown`
  - `sensor.ternopil_grid_off_today` (attribute `blocks`)
  - `sensor.ternopil_grid_off_tomorrow` (attribute `blocks`)

## Install (HACS)
1. HACS → Integrations → Custom repositories
2. Add this repo as **Integration**
3. Install, restart Home Assistant
4. Settings → Devices & services → Add Integration → **Ternopil Grid Schedule**

## Telegram example
Use `binary_sensor.ternopil_grid_power` state changes to send messages.
