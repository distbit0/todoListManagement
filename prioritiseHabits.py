import requests
from datetime import datetime, timedelta
import json
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
checkins_url = "https://api.ticktick.com/api/v2/habitCheckins/query"

headers = {
    "cookie": os.environ.get("tiktikCookie"),
    "User-Agent": "curl/7.64.1",
    "Accept": "*/*",
    "Content-Type": "application/json",
}


def get_habits_due_today(list_of_habits, checkins):
    """
    Returns a list of habits due today based on the provided habits and checkins.

    :param list_of_habits: List of habit dictionaries.
    :param checkins: Dictionary mapping habit IDs to lists of checkin dictionaries.
    :return: List of habit dictionaries that are due today.
    """

    # Helper function to parse the RRULE string
    def parse_repeat_rule(rrule_str):
        """
        Parses an RRULE string into a dictionary.

        :param rrule_str: RRULE string (e.g., "RRULE:FREQ=DAILY;INTERVAL=20")
        :return: Dictionary of RRULE components.
        """
        rrule = {}
        if rrule_str.startswith("RRULE:"):
            rrule_str = rrule_str[len("RRULE:") :]
        parts = rrule_str.split(";")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                rrule[key] = value
        return rrule

    # Helper function to convert BYDAY to Python's weekday numbers
    def byday_to_weekdays(byday_str):
        """
        Converts BYDAY values to Python weekday numbers.

        :param byday_str: String of BYDAY values (e.g., "SU,MO,TU,WE,TH,FR,SA")
        :return: List of integers representing weekdays (0=Monday, 6=Sunday)
        """
        day_mapping = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
        days = byday_str.split(",")
        weekdays = [day_mapping[day] for day in days if day in day_mapping]
        return weekdays

    # Helper function to parse dates
    def parse_date(date_input):
        """
        Parses a date from various formats to a datetime.date object.

        :param date_input: Integer in YYYYMMDD or string in ISO format.
        :return: datetime.date object.
        """
        if isinstance(date_input, int):
            return datetime.strptime(str(date_input), "%Y%m%d").date()
        elif isinstance(date_input, str):
            # Attempt to parse ISO format
            try:
                return datetime.strptime(date_input, "%Y-%m-%dT%H:%M:%S.%f%z").date()
            except ValueError:
                try:
                    return datetime.strptime(date_input, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(f"Unrecognized date format: {date_input}")
        else:
            raise TypeError(f"Unsupported date input type: {type(date_input)}")

    # Get today's date in local tz
    today = datetime.now().astimezone().date()

    due_today = []

    for habit in list_of_habits:
        # Skip archived habits
        if habit.get("archivedTime"):
            continue

        repeat_rule = habit.get("repeatRule", "")
        if not repeat_rule:
            continue  # Skip if no repeat rule

        rrule = parse_repeat_rule(repeat_rule)
        freq = rrule.get("FREQ", "").upper()

        if freq == "WEEKLY":
            byday = rrule.get("BYDAY", "")
            if not byday:
                continue  # Skip if no BYDAY specified
            weekdays = byday_to_weekdays(byday)
            if today.weekday() in weekdays:
                due_today.append(habit)
        elif freq == "DAILY":
            interval = int(rrule.get("INTERVAL", "1"))
            habit_id = habit.get("id")
            habit_checkins = checkins.get(habit_id, [])

            # Find the latest checkin date
            latest_checkin_date = None
            for checkin in habit_checkins:
                checkin_stamp = checkin.get("checkinStamp")
                if checkin_stamp:
                    try:
                        checkin_date = parse_date(checkin_stamp)
                        if (latest_checkin_date is None) or (
                            checkin_date > latest_checkin_date
                        ):
                            latest_checkin_date = checkin_date
                    except (ValueError, TypeError):
                        continue  # Skip invalid checkin dates

            if latest_checkin_date:
                days_since_last_checkin = (today - latest_checkin_date).days
                if days_since_last_checkin >= interval:
                    due_today.append(habit)
            else:
                # No checkins, check targetStartDate
                target_start = habit.get("targetStartDate")
                if target_start:
                    try:
                        target_start_date = parse_date(target_start)
                        if target_start_date <= today:
                            due_today.append(habit)
                    except (ValueError, TypeError):
                        continue  # Skip if targetStartDate is invalid
                else:
                    # If no targetStartDate, assume due
                    due_today.append(habit)
        else:
            # Handle other frequencies if necessary
            continue

    return due_today


def update_habit_text(habits):
    updatedHabits = [habit for habit in habits if "^" in habit["name"]]
    habits = [habit for habit in habits if not "^" in habit["name"]]
    for priority, habit in enumerate(habits):
        priority += 1
        old_name = habit["name"]
        new_name = f"{priority}. {remove_existing_prefix(old_name)}"
        print(f"Updated: {old_name} -> {new_name}")
        habit_update = habit.copy()  # Create a copy of the original habit
        habit_update["name"] = new_name  # Update the name
        updatedHabits.append(habit_update)

    payload = {"add": [], "update": updatedHabits, "delete": []}

    try:
        response = requests.post(update_url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while updating the habit: {e}")
    
    return updatedHabits


def update_habit_sort_order(habits):
    updatedHabits = []
    for habit in habits:
        habit_update = habit.copy()  
        # Check for priority in the habit name
        priority_match = re.match(r"^(\d+)\.\s", habit["name"])
        if priority_match:
            priority = int(priority_match.group(1))
        elif "^" in habit["name"]:
            priority = 0
        else:
            priority = len(updatedHabits) + 1  # Default priority
        
        habit_update["sortOrder"] = priority * 1000000000
        updatedHabits.append(habit_update)

    payload = {"add": [], "update": updatedHabits, "delete": []}

    try:
        response = requests.post(update_url, headers=headers, json=payload)
        response.raise_for_status()
        print("Successfully updated habit sort order")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while updating the habits: {e}")

    return updatedHabits

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


def weighted_shuffle(habits, bias):
    # Assign weights and add some randomness
    weighted_habits = [
        (habit, random.random() + (bias if "!" in habit.get("name", "") else 0))
        for habit in habits
    ]

    # Sort based on weights (descending order)
    weighted_habits.sort(key=lambda x: x[1], reverse=True)

    # Return only the habits, without the weights
    return [habit for habit, _ in weighted_habits]


def main():
    if has_run_today():
        print("Script has already run today. Exiting.")
        return

    try:
        # Fetch all habits
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_habits = response.json()

        # Save all habits to JSON file
        save_habits_json(all_habits)

        # Extract habit IDs from all_habits
        habit_ids = [habit["id"] for habit in all_habits]

        # Prepare JSON data for the checkins request
        json_data = {"habitIds": habit_ids}

        # Make the POST request with the JSON data
        checkins_response = requests.post(checkins_url, headers=headers, json=json_data)
        checkins_response.raise_for_status()
        checkins_data = checkins_response.json()
        checkins = checkins_data.get("checkins", {})

        # Get habits due today
        due_habits_today = get_habits_due_today(all_habits, checkins)

        if due_habits_today:
            print(f"Found {len(due_habits_today)} long-term habits due today.")

            due_habits_today = weighted_shuffle(due_habits_today, 0.3)
            due_habits_today = update_habit_text(due_habits_today)
            update_habit_sort_order(due_habits_today)

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
