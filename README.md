# Tibber Sonos Integration

Built with Python 3.10

config.json

Time in hours (utc) for when to trigger.

```
{
    "QUIET_AFTER": 20,
    "QUIET_BEFORE": 5,
    "MINUTES_WAIT_UNTIL_REPEAT": 30,
    "LAST_TRIGGER": "2022-09-05 14:46 +0000"
}
```

.env

```
TIBBER_TOKEN=<token>
TIBBER_HOME_ID=<home_id>
HOURLEY_TRIGGER_RATE=<when_to_trigger>
SONOS_REFRESH_TOKEN=<token for sonos>
SONOS_CREDENTIALS=<base 64 encoded client id>
SONOS_GROUP_ID=<speaker group to send play command to>
SONOS_HOUSEHOLD_ID=<sonos household id>
```
