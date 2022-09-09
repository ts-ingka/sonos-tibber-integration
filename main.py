"""Main script. Will query Tibber API and get realtime consumption and price,
if you're averaging a burnrate of more than 10 sek attempt to play money
related song with Sonos."""
import os
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from python_graphql_client import GraphqlClient
import requests


logging.basicConfig(
    filename="./tibber-monitor.log", encoding="utf-8", level=logging.INFO
)

logging.info(
    "[%s] Loading environment variables and imports", datetime.now(timezone.utc)
)

load_dotenv()  # env variables

tibber_token = os.getenv("TIBBER_TOKEN")
tibber_home_id = os.getenv("TIBBER_HOME_ID")
sonos_refresh_token = os.getenv("SONOS_REFRESH_TOKEN")
sonos_credentials = os.getenv("SONOS_CREDENTIALS")
sonos_household_id = os.getenv("SONOS_HOUSEHOLD_ID")
sonos_group_id = os.getenv("SONOS_GROUP_ID")

consumption = []


def print_handle(data):
    logging.info(
        "[%s] Received data point %s",
        datetime.now(timezone.utc),
        data["data"]["liveMeasurement"]["timestamp"],
    )
    print(data)
    consumption.append(data)


def run():
    logging.info("[%s] Initiating client.", datetime.now(timezone.utc))
    client = GraphqlClient(
        endpoint="wss://api.tibber.com/v1-beta/gql/subscriptions"
    )
    query = f"""
        subscription {{
        liveMeasurement(homeId:"{tibber_home_id}") {{
            timestamp
            accumulatedCost
            power
        }}
    }}
    """
    asyncio.run(
        client.subscribe(
            query=query,
            headers={"Authorization": tibber_token},
            handle=print_handle,
            max_runs=2,
        )
    )

    consumption_1 = consumption[0]["data"]["liveMeasurement"]["accumulatedCost"]
    consumption_2 = consumption[-1]["data"]["liveMeasurement"][
        "accumulatedCost"
    ]

    hourly_trigger_rate = int(os.getenv("HOURLEY_TRIGGER_RATE"))
    trigger_burnrate = (
        hourly_trigger_rate / 360
    )  # (3600 seconds per hour, measurepoint every 10. i)
    current_burnrate = consumption_2 - consumption_1
    logging.info(
        "[%s] Consumption 1: %s Consumption 2: %s Diff: %s Trigger rate: %s",
        datetime.now(timezone.utc),
        consumption_1,
        consumption_2,
        consumption_2 - consumption_1,
        hourly_trigger_rate,
    )
    logging.info(
        "[%s] Current burnrate: %s SEK an hour",
        datetime.now(timezone.utc),
        current_burnrate * 360,
    )

    if not current_burnrate > trigger_burnrate:
        logging.info(
            "[%s] Burnrate not achieved. Exiting", datetime.now(timezone.utc)
        )
        return

    logging.info(
        "[%s] Currently burning more than %s SEK an hour",
        datetime.now(timezone.utc),
        hourly_trigger_rate,
    )

    logging.info("[%s] Loading configuration", datetime.now(timezone.utc))

    with open("./config.json", "r") as f:
        config = json.loads(f.read())

    now = datetime.now(timezone.utc)
    if now.hour > config["QUIET_AFTER"] or now.hour < config["QUIET_BEFORE"]:
        logging.info(
            "[%s] Trigger is in quiet hours... Not playing and exiting",
            datetime.now(timezone.utc),
        )
        return

    if config["LAST_TRIGGER"] is not None:
        last_trigger = datetime.strptime(
            config["LAST_TRIGGER"], "%Y-%m-%d %H:%M %z"
        )

        diff = now - last_trigger

        if diff.seconds < 1800:
            logging.info(
                "[%s] Was triggered within last 30 minutes. Exiting",
                datetime.now(timezone.utc),
            )
            return

    # proceding with trigger and updating config
    config["LAST_TRIGGER"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M %z"
    )

    with open("./config.json", "w") as f:
        f.writelines(json.dumps(config))

    r = requests.post(
        url=f"https://api.sonos.com/login/v3/oauth/access?grant_type=refresh_token&refresh_token={sonos_refresh_token}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": sonos_credentials,
        },
        timeout=10,
    )
    if r.status_code != 200:
        logging.exception(
            "Unable to generate access token with Sonos. %s ",
            r.status_code,
        )
        raise Exception("Unable to generate access token with Sonos")

    access_token = r.json()["access_token"]
    logging.info(
        "[%s] Created access token for sonos",
        datetime.now(timezone.utc),
    )

    # TODO: CHECK TIME AND OTHER REQUIREMENTS
    logging.info(
        "[%s] Loading playlist",
        datetime.now(timezone.utc),
    )

    r = requests.post(
        url=f"https://api.ws.sonos.com/control/api/v1/groups/{sonos_group_id}/playlists",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"action": "replace", "playlistId": 0},
        timeout=10,
    )

    logging.info(
        "[%s] Set status play",
        datetime.now(timezone.utc),
    )

    time.sleep(0.1)

    # set volume

    r = requests.post(
        url=f"https://api.ws.sonos.com/control/api/v1/groups/{sonos_group_id}/groupVolume?volume=33",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    r = requests.post(
        url=f"https://api.ws.sonos.com/control/api/v1/groups/{sonos_group_id}/playback/play",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    time.sleep(45)

    r = requests.post(
        url=f"https://api.ws.sonos.com/control/api/v1/groups/{sonos_group_id}/playback/pause",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )


if __name__ == "__main__":
    run()
