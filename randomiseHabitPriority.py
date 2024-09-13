import requests
import json
from datetime import datetime, timedelta

url = "https://api.ticktick.com/api/v2/habits"
headers = {
    "cookie": "t=154BB8FE914467838857B098038B43ADE8D4CFA313919A5258BA01F2FD72D4174C2A88FC19EAB910E616597C001200739D669527A4028751DCE594F7B15330C90E02762C06FF5B514BFFD847418A24060BCD97B425F8548635B3618E533D013082BEE463B1431075BC4DD36207DCA5A80BCD97B425F85486E947B995C87843B0C2851F2CBA770F39841478DC8FC39A65FA8D5F4EBDB4BD7CC0C3DF9840B21D81; _csrf_token=Q_Dju_sOzCh8NkqXsrG3N488vTAgnHMsdZ9jujyYpg-1725609570; oai=34EA9AAC90BF370BC55434AFDE8962B179F4528958F3E69482F493E737EBB3014BF88D2F137EBC5FF9F8EFE12EC76D4CFCB7DF6DDAB5723EA043F02B57F1D40E2AC536DBCB019EDB56C93C04D2DA22BAA800BBDA56CE8AC417E0313C075F2BA4D3056E5F14F482704582A4C3495C72EDC945FD92BCBDCC7AE72A62B62D375827234F632BE7281B9E2BC9DE612A818BFC; ",
    "User-Agent": "curl/7.64.1",
    "Accept": "*/*",
}


def is_habit_due_today(habit):
    today = datetime.now().date()
    repeat_rule = habit.get("repeatRule", "")

    if not repeat_rule.startswith("RRULE:FREQ=WEEKLY;BYDAY="):
        return False

    days_of_week = repeat_rule.split("BYDAY=")[1].split(",")
    today_abbr = today.strftime("%a").upper()[:2]  # Get first two letters of day name (e.g., 'MO' for Monday)

    return today_abbr in days_of_week


def get_long_term_habits_due_today():
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        print("Response status code:", response.status_code)
        habits = response.json()
        long_term_habits_due_today = []

        for habit in habits:
            is_due = is_habit_due_today(habit)
            is_long_term = "long term" in habit["name"].lower()
            print(f"Habit: {habit['name']}, Due today: {is_due}, Long term: {is_long_term}")
            if is_due and is_long_term:
                long_term_habits_due_today.append(habit["name"])

        return long_term_habits_due_today
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print("Response content:", response.text)
    return []


# Main execution
if __name__ == "__main__":
    long_term_habits = get_long_term_habits_due_today()

    if long_term_habits:
        print("Long-term habits due today:")
        for habit in long_term_habits:
            print(f"- {habit}")
    else:
        print("No long-term habits due today or an error occurred.")
