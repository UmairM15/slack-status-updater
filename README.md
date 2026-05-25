# Slack Status Auto Updater

A small Python automation project that updates your Slack status based on a weekly schedule defined in `status.yaml`.

The script can run locally, through Windows Task Scheduler, or online using GitHub Actions so your laptop does not need to stay on.

## What It Does

- Reads your current Slack profile status.
- Checks the current day and time using the timezone in `status.yaml`.
- Finds the first matching schedule rule.
- Sets your Slack status text, emoji, and expiration time.
- Avoids overwriting protected statuses such as `Off shift`, `Event`, or `In a meeting`.
- Avoids overwriting random manually set statuses that are not managed by the script.
- Clears managed statuses when the schedule no longer applies.

## Project Structure

```text
slackscript/
├─ slack_status.py
├─ status.yaml
├─ requirements.txt
├─ .gitignore
└─ .github/
   └─ workflows/
      └─ slack-status.yml
```

## Requirements

- Python 3.9+
- A Slack app with a User OAuth Token
- GitHub Actions if running online

Python packages:

```txt
requests
pyyaml
python-dotenv
tzdata
```

Install locally with:

```bash
python -m pip install -r requirements.txt
```

## Slack App Setup

Create a Slack app from scratch:

1. Go to Slack API → Your Apps.
2. Click **Create New App**.
3. Choose **From scratch**.
4. Name it something clear, such as `Personal Slack Status Scheduler`.
5. Select your Slack workspace.
6. Go to **OAuth & Permissions**.
7. Under **User Token Scopes**, add:
   - `users.profile:read`
   - `users.profile:write`
8. Install or reinstall the app to your workspace.
9. Copy the **User OAuth Token**.

The token usually starts with:

```text
xoxp-
```

Do not use a bot token starting with `xoxb-`.

## Environment Variable

The script expects this environment variable:

```text
SLACK_USER_TOKEN
```

### Local `.env` Option

Create a `.env` file in the project folder:

```env
SLACK_USER_TOKEN=xoxp-your-token-here
```

Make sure `.env` is listed in `.gitignore` so it is never pushed to GitHub:

```gitignore
.env
```

## GitHub Actions Secret

If running this online with GitHub Actions:

1. Open your GitHub repository.
2. Go to **Settings**.
3. Go to **Secrets and variables → Actions**.
4. Click **New repository secret**.
5. Add:

```text
Name: SLACK_USER_TOKEN
Value: xoxp-your-token-here
```

The workflow reads the token using:

```yaml
env:
  SLACK_USER_TOKEN: ${{ secrets.SLACK_USER_TOKEN }}
```

## Configuration

All status rules are controlled in `status.yaml`.

Example:

```yaml
timezone: America/New_York

protected_statuses:
  - text: Off shift
    emoji: ":zzz:"
  - text: Event
    emoji: ":circus_tent:"
  - text: In a meeting

managed_statuses:
  office:
    text: In office
    emoji: ":office:"
  wfh:
    text: WFH
    emoji: ":house_with_garden:"
  lunch:
    text: Lunch Break
    emoji: ":cookie:"

schedule:
  - status: lunch
    days: [mon, tue, wed, thu, fri]
    start: "12:00"
    end: "13:00"

  - status: office
    days: [mon, wed, fri]
    start: "09:00"
    end: "17:00"

  - status: wfh
    days: [tue, thu]
    start: "09:00"
    end: "17:00"
```

## How Schedule Matching Works

The script checks the schedule from top to bottom.

The first rule that matches the current day and time is used.

That means if two rules overlap, the one listed first wins.

Example:

```yaml
schedule:
  - status: lunch
    days: [mon, tue, wed, thu, fri]
    start: "13:00"
    end: "14:00"

  - status: office
    days: [mon, tue, wed, thu, fri]
    start: "09:00"
    end: "17:00"
```

In this example, lunch takes priority from 1 PM to 2 PM because it appears before the office rule.

## Blank Status Text

If you want an emoji but no status text, use an empty string:

```yaml
managed_statuses:
  office:
    text: ""
    emoji: ":office:"
```

Do not leave it blank like this:

```yaml
text:
```

A blank YAML value becomes `null`, which can cause matching issues.

## Running Locally

From the project folder:

```bash
python slack_status.py
```

Possible outputs:

```text
Setting status: :office: In office
Already correct; nothing to do.
Outside schedule; nothing to do.
Outside schedule; clearing managed status.
Protected status active; doing nothing.
Manual unknown status active; doing nothing.
```

## Running with GitHub Actions

Create this file:

```text
.github/workflows/slack-status.yml
```

Example workflow:

```yaml
name: Update Slack Status

on:
  schedule:
    - cron: "2,7,12,17,22,27,32,37,42,47,52,57 * * * *"
  workflow_dispatch:

jobs:
  update-status:
    runs-on: ubuntu-latest

    env:
      SLACK_USER_TOKEN: ${{ secrets.SLACK_USER_TOKEN }}

    steps:
      - name: Check out repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Slack status script
        run: python slack_status.py
```

After pushing this file to GitHub:

1. Go to the **Actions** tab.
2. Select **Update Slack Status**.
3. Click **Run workflow** to test it manually.
4. Check the logs for the script output.

## Notes About GitHub Actions Timing

The workflow runs on GitHub's servers, so your laptop does not need to be on.

The cron schedule runs based on UTC, but the Python script uses the timezone from `status.yaml`, so your status rules still follow your configured local timezone.

GitHub scheduled workflows can occasionally be delayed. Running every 5 minutes helps keep the status reasonably accurate.

## Troubleshooting

### `Missing SLACK_USER_TOKEN environment variable`

Your environment variable or GitHub Actions secret is missing.

Check that the secret is named exactly:

```text
SLACK_USER_TOKEN
```

### `No time zone found with key America/New_York`

Install `tzdata`:

```bash
python -m pip install tzdata
```

Also make sure `tzdata` is in `requirements.txt`.

### `No such file or directory: status.yaml`

The script cannot find the config file.

Check that:

- The file is named `status.yaml`
- It is committed to GitHub
- `slack_status.py` uses `load_config(path="status.yaml")`

### `Slack profile set failed`

Common causes:

- Wrong token type
- Missing Slack scopes
- App not installed/reinstalled after adding scopes
- Workspace app approval restrictions

Use a User OAuth Token starting with `xoxp-`, not a bot token.

### Status does not change

Check:

- GitHub Actions run succeeded.
- The `Run Slack status script` step shows the expected output.
- Your current Slack status is not a protected status.
- Your current Slack status is not a random manual status.
- The current time matches a rule in `status.yaml`.
