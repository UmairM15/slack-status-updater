import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import yaml

from dotenv import load_dotenv
load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_USER_TOKEN")
if not SLACK_TOKEN:
    raise RuntimeError("Missing SLACK_USER_TOKEN environment variable.")
API = "https://slack.com/api"

HEADERS = {
    "Authorization": f"Bearer {SLACK_TOKEN}",
    "Content-Type": "application/json; charset=utf-8",
}

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_config(path="status.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def slack_get_profile():
    r = requests.get(f"{API}/users.profile.get", headers=HEADERS, timeout=15)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack profile get failed: {data}")
    return data["profile"]


def slack_set_status(text, emoji, expiration):
    payload = {
        "profile": {
            "status_text": text,
            "status_emoji": emoji,
            "status_expiration": expiration,
        }
    }

    r = requests.post(
        f"{API}/users.profile.set",
        headers=HEADERS,
        json=payload,
        timeout=15,
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack profile set failed: {data}")


def slack_clear_status():
    slack_set_status("", "", 0)


def spec_matches(profile, spec):
    current_text = profile.get("status_text", "")
    current_emoji = profile.get("status_emoji", "")

    if "text" in spec and current_text != spec["text"]:
        return False
    if "emoji" in spec and current_emoji != spec["emoji"]:
        return False
    return True


def is_protected(profile, config):
    return any(spec_matches(profile, s) for s in config.get("protected_statuses", []))


def is_managed(profile, config):
    managed = config["managed_statuses"].values()
    return any(spec_matches(profile, s) for s in managed)


def parse_time(value):
    hour, minute = map(int, value.split(":"))
    return hour, minute


def find_desired_status(config, now):
    today = DAY_NAMES[now.weekday()]

    for rule in config["schedule"]:
        if today not in rule["days"]:
            continue

        start_hour, start_minute = parse_time(rule["start"])
        end_hour, end_minute = parse_time(rule["end"])

        start = now.replace(
            hour=start_hour,
            minute=start_minute,
            second=0,
            microsecond=0,
        )
        end = now.replace(
            hour=end_hour,
            minute=end_minute,
            second=0,
            microsecond=0,
        )

        if start <= now < end:
            status_key = rule["status"]
            status = config["managed_statuses"][status_key]
            return status, int(end.timestamp())

    return None, None


def main():
    config = load_config()
    tz = ZoneInfo(config["timezone"])
    now = datetime.now(tz)

    profile = slack_get_profile()

    # Never override protected statuses like Off shift/Event/In a meeting.
    if is_protected(profile, config):
        print("Protected status active; doing nothing.")
        return

    desired, expiration = find_desired_status(config, now)

    current_text = profile.get("status_text", "")
    current_emoji = profile.get("status_emoji", "")

    # If user manually set some random status, don't overwrite it.
    current_blank = not current_text and not current_emoji
    current_managed = is_managed(profile, config)

    if not current_blank and not current_managed:
        print("Manual unknown status active; doing nothing.")
        return

    if desired is None:
        if current_managed:
            print("Outside schedule; clearing managed status.")
            slack_clear_status()
        else:
            print("Outside schedule; nothing to do.")
        return

    if current_text == desired["text"] and current_emoji == desired["emoji"]:
        print("Already correct; nothing to do.")
        return

    print(f"Setting status: {desired['emoji']} {desired['text']}")
    slack_set_status(desired["text"], desired["emoji"], expiration)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)