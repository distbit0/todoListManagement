import requests
import json
from datetime import datetime, timedelta
import random
import re
from dotenv import load_dotenv
import os
import pathlib

load_dotenv()

LAST_RUN_FILE = pathlib.Path(__file__).parent / ".last_run"
HABITS_JSON_FILE = pathlib.Path("/home/pimania/miscSyncs/habits/habits.json")

url = "https://api.ticktick.com/api/v2/habits"
update_url = "https://api.ticktick.com/api/v2/habits/batch"
headers = {
    "cookie": os.environ.get("tiktikCookie"),
    "User-Agent": "curl/7.64.1",
    "Accept": "*/*",
    "Content-Type": "application/json",
}


def is_habit_due_today(habit):
    today = datetime.now().date()
    repeat_rule = habit.get("repeatRule", "")

    if not repeat_rule.startswith("RRULE:FREQ=WEEKLY;BYDAY="):
        return False

    days_of_week = repeat_rule.split("BYDAY=")[1].split(",")
    today_abbr = today.strftime("%a").upper()[
        :2
    ]  # Get first two letters of day name (e.g., 'MO' for Monday)

    return today_abbr in days_of_week


def get_long_term_habits_due_today():
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        habits = response.json()
        long_term_habits_due_today = []

        for habit in habits:
            is_due = is_habit_due_today(habit)
            is_long_term = "long term" in habit["name"].lower()
            if is_due and is_long_term:
                long_term_habits_due_today.append(habit)

        return long_term_habits_due_today
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
    return []


def update_habit_name(habit, new_name):
    habit_update = habit.copy()  # Create a copy of the original habit
    habit_update["name"] = new_name  # Update the name

    payload = {"add": [], "update": [habit_update], "delete": []}

    try:
        response = requests.post(update_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Successfully updated habit: {new_name}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while updating the habit: {e}")


def remove_existing_prefix(name):
    return re.sub(r"^\d+\.\s*", "", name)


def has_run_today():
    if not LAST_RUN_FILE.exists():
        return False
    currentDate = datetime.now().date()
    last_run = datetime.fromtimestamp(LAST_RUN_FILE.stat().st_mtime)
    return currentDate == last_run.date()


def update_last_run():
    LAST_RUN_FILE.touch()


def save_habits_json(habits):
    HABITS_JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HABITS_JSON_FILE, "w") as f:
        json.dump(habits, f, indent=2)
    print(f"Habits JSON saved to {HABITS_JSON_FILE}")


def main():
    if has_run_today():
        print("Script has already run today. Exiting.")
        return

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_habits = response.json()

        # Save all habits to JSON file
        save_habits_json(all_habits)

        long_term_habits = [
            habit
            for habit in all_habits
            if is_habit_due_today(habit) and "long term" in habit["name"].lower()
        ]

        if long_term_habits:
            print(f"Found {len(long_term_habits)} long-term habits due today.")
            random.shuffle(long_term_habits)

            for i, habit in enumerate(long_term_habits, 1):
                old_name = habit["name"]
                new_name = f"{i}. {remove_existing_prefix(old_name)}"
                update_habit_name(habit, new_name)
                print(f"Updated: {old_name} -> {new_name}")

            update_last_run()
            print("Script execution completed and last run time updated.")
        else:
            print("No long-term habits due today.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")


if __name__ == "__main__":
    main()
