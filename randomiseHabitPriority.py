import requests
import json
from datetime import datetime, timedelta

# API endpoint
url = "https://api.ticktick.com/api/v2/habits"

# Headers
headers = {
    "cookie": "cookie: t=154BB8FE914467838857B098038B43ADE8D4CFA313919A5258BA01F2FD72D4174C2A88FC19EAB910E616597C001200739D669527A4028751DCE594F7B15330C90E02762C06FF5B514BFFD847418A24060BCD97B425F8548635B3618E533D013082BEE463B1431075BC4DD36207DCA5A80BCD97B425F85486E947B995C87843B0C2851F2CBA770F39841478DC8FC39A65FA8D5F4EBDB4BD7CC0C3DF9840B21D81; _csrf_token=Q_Dju_sOzCh8NkqXsrG3N488vTAgnHMsdZ9jujyYpg-1725609570; oai=34EA9AAC90BF370BC55434AFDE8962B179F4528958F3E69482F493E737EBB3014BF88D2F137EBC5FF9F8EFE12EC76D4CFCB7DF6DDAB5723EA043F02B57F1D40E2AC536DBCB019EDB56C93C04D2DA22BAA800BBDA56CE8AC417E0313C075F2BA4D3056E5F14F482704582A4C3495C72EDC945FD92BCBDCC7AE72A62B62D375827234F632BE7281B9E2BC9DE612A818BFC;"
}


def is_habit_due_today(habit):
    today = datetime.now().date()
    start_date = datetime.strptime(str(habit["targetStartDate"]), "%Y%m%d").date()

    if start_date > today:
        return False

    repeat_rule = habit["repeatRule"]
    if "FREQ=DAILY" in repeat_rule:
        interval = (
            int(repeat_rule.split("INTERVAL=")[1]) if "INTERVAL=" in repeat_rule else 1
        )
        days_since_start = (today - start_date).days
        return days_since_start % interval == 0
    elif "FREQ=WEEKLY" in repeat_rule:
        if "TT_TIMES=" in repeat_rule:
            times_per_week = int(repeat_rule.split("TT_TIMES=")[1])
            days_since_start = (today - start_date).days
            return days_since_start % (7 // times_per_week) == 0

    return False


def get_long_term_habits_due_today():
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        print("Response status code:", response.status_code)
        print("Response content:", response.text)
        
        habits = response.json()
        long_term_habits_due_today = []

        for habit in habits:
            if is_habit_due_today(habit) and "long term" in habit["name"].lower():
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
