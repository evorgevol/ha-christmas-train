# Christmas Train for Home Assistant

This custom integration creates a **Christmas Train** device controlled through
an existing Home Assistant remote, such as a Sofabaton hub. It does not replace
the Sofabaton integration.

## Important: assumed state

The train does not report its state. The movement sensor and the Light and
Steam synchronization selectors show the **last assumed state**, not a
confirmed measurement. A successful remote action does not prove that the
train received or acted on it. The physical remote, missed signals, a train
power cycle, direct `remote.send_command` calls, or an interruption can make
the displayed state wrong. Do not rely on it for safety.

States start unknown and are restored across Home Assistant restarts. Observe
the train and use the **Sync assumed movement**, **Sync assumed light**, and
**Sync assumed steam** selectors to correct them; selecting a value never
sends a command. If the Light or Steam state is unknown, its toggle button
keeps it unknown until you synchronize it. Noise cycles through its three modes
but is not tracked.

Commands are serialized. While a command is being sent, the affected assumed
state is set to unknown; if the send reports an error, the state stays unknown
and the error is surfaced. A previously queued command can delay Stop, so
keep a physical way to stop or disconnect the train.

## Installation

1. Copy the `custom_components/christmas_train` folder into your Home
   Assistant configuration directory's `custom_components` folder, preserving
   other custom integrations.
2. Restart Home Assistant. Under **Settings > Devices & services > Add
   integration**, search for **Christmas Train**.
3. Select `remote.x2_hub_remote` and enter Sofabaton device ID `2`, or supply
   the equivalent values for your setup.
4. Open the Christmas Train device. Check the actual train and use the three
   sync selectors to record its current state.

The integration targets Home Assistant 2025.4 or newer. It is installed
manually, not through HACS.

## Commands

| Button | Sofabaton command | Repeats |
| --- | ---: | ---: |
| Forward | 1 | 3 |
| Stop | 2 | 3 |
| Reverse | 3 | 3 |
| Toggle steam | 4 | 1 |
| Forward fast | 5 | 3 |
| Toggle light | 6 | 1 |
| Cycle noise | 7 | 1 |

Each action uses `delay_secs: 1` and `hold_secs: 0`. First test each command
with the train in a safe, accessible position. In particular, verify whether
one repeat reliably triggers the toggle commands once: how a receiver handles
repeats is hardware-dependent. To change a repeat count, edit the corresponding
entry in `custom_components/christmas_train/const.py`, restart Home Assistant,
and test again. Do not assume repeated toggle signals are harmless.

## Dashboard

An entities card is a simple starting point. Entity IDs are assigned by Home
Assistant and can differ, especially if names already exist; check the device
page and replace these example IDs as necessary.

```yaml
type: entities
title: Christmas Train
entities:
  - entity: sensor.christmas_train
    name: Assumed movement
  - button.christmas_train_forward
  - button.christmas_train_forward_fast
  - button.christmas_train_reverse
  - button.christmas_train_stop
  - button.christmas_train_toggle_light
  - select.christmas_train_sync_assumed_light
  - button.christmas_train_toggle_steam
  - select.christmas_train_sync_assumed_steam
  - button.christmas_train_cycle_noise
  - select.christmas_train_sync_assumed_movement
```

For automations, use the standard button action, replacing the entity ID if
necessary:

```yaml
action: button.press
target:
  entity_id: button.christmas_train_forward
```

To manually correct an assumption without moving the train:

```yaml
action: select.select_option
target:
  entity_id: select.christmas_train_sync_assumed_movement
data:
  option: stopped
```

The movement options are `unknown`, `stopped`, `forward`, `forward_fast`, and
`reverse`. The Light and Steam options are `unknown`, `on`, and `off`.

## Development

The integration has no third-party runtime dependencies. Run its tests with
`python -m unittest discover -s tests -v`. The isolated tests exercise the
integration against test doubles; a real Home Assistant installation and the
actual train are still needed to verify integration compatibility and radio
behavior.
