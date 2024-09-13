import requests
import json
from datetime import datetime

# API endpoint
url = "https://api.ticktick.com/api/v2/habits"

# Headers
headers = {
    "cookie": "cookie: t=154BB8FE914467838857B098038B43ADE8D4CFA313919A5258BA01F2FD72D4174C2A88FC19EAB910E616597C001200739D669527A4028751DCE594F7B15330C90E02762C06FF5B514BFFD847418A24060BCD97B425F8548635B3618E533D013082BEE463B1431075BC4DD36207DCA5A80BCD97B425F85486E947B995C87843B0C2851F2CBA770F39841478DC8FC39A65FA8D5F4EBDB4BD7CC0C3DF9840B21D81; _csrf_token=Q_Dju_sOzCh8NkqXsrG3N488vTAgnHMsdZ9jujyYpg-1725609570; oai=34EA9AAC90BF370BC55434AFDE8962B179F4528958F3E69482F493E737EBB3014BF88D2F137EBC5FF9F8EFE12EC76D4CFCB7DF6DDAB5723EA043F02B57F1D40E2AC536DBCB019EDB56C93C04D2DA22BAA800BBDA56CE8AC417E0313C075F2BA4D3056E5F14F482704582A4C3495C72EDC945FD92BCBDCC7AE72A62B62D375827234F632BE7281B9E2BC9DE612A818BFC;"
}


def get_long_term_habits_due_today():
    # Make the API request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        habits = json.loads(response.text)
        today = datetime.now().date()

        long_term_habits_due_today = []

        for habit in habits:
            # Check if the habit is due today
            if (
                "dueDate" in habit
                and datetime.fromisoformat(habit["dueDate"].split("T")[0]).date()
                == today
            ):
                # Check if the habit includes "long term" in its name
                if "long term" in habit["name"].lower():
                    long_term_habits_due_today.append(habit["name"])

        return long_term_habits_due_today
    else:
        print(f"Failed to fetch habits. Status code: {response.status_code}")
        return []


# Main execution
if __name__ == "__main__":
    long_term_habits = get_long_term_habits_due_today()

    if long_term_habits:
        print("Long-term habits due today:")
        for habit in long_term_habits:
            print(f"- {habit}")
    else:
        print("No long-term habits due today.")
