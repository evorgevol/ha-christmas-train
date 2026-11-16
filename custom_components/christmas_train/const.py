"""Constants for the Christmas Train integration."""

DOMAIN = "christmas_train"
CONF_REMOTE_ENTITY = "remote_entity"
CONF_REMOTE_DEVICE = "remote_device"

UNKNOWN = "unknown"
MOVEMENT_OPTIONS = (UNKNOWN, "stopped", "forward", "forward_fast", "reverse")
TOGGLE_OPTIONS = (UNKNOWN, "on", "off")
STATE_OPTIONS = {
    "movement": MOVEMENT_OPTIONS,
    "light": TOGGLE_OPTIONS,
    "steam": TOGGLE_OPTIONS,
}

# Command, affected state, resulting movement (None means toggle), repeats.
COMMANDS = {
    "forward": ("1", "movement", "forward", 3),
    "stop": ("2", "movement", "stopped", 3),
    "reverse": ("3", "movement", "reverse", 3),
    "steam": ("4", "steam", None, 1),
    "forward_fast": ("5", "movement", "forward_fast", 3),
    "light": ("6", "light", None, 1),
    "noise": ("7", None, None, 1),
}
