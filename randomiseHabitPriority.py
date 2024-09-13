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
    start_date = datetime.strptime(str(habit['targetStartDate']), '%Y%m%d').date()
    
    if start_date > today:
        return False
    
    repeat_rule = habit['repeatRule']
    if 'FREQ=DAILY' in repeat_rule:
        interval = int(repeat_rule.split('INTERVAL=')[1]) if 'INTERVAL=' in repeat_rule else 1
        days_since_start = (today - start_date).days
        return days_since_start % interval == 0
    elif 'FREQ=WEEKLY' in repeat_rule:
        if 'TT_TIMES=' in repeat_rule:
            times_per_week = int(repeat_rule.split('TT_TIMES=')[1])
            days_since_start = (today - start_date).days
            return days_since_start % (7 // times_per_week) == 0
    
    return False

def get_long_term_habits_due_today():
    # For testing purposes, we'll use a mock response
    # In a real scenario, you would use: response = requests.get(url, headers=headers)
    mock_response = '''
    [{"id":"66dac49bdce64115dd651668","name":"2x 30 pushups straight + face-on-floor","iconRes":"habit_daily_check_in","color":"#97E38B","sortOrder":-1099511627776,"status":0,"encouragement":"","totalCheckIns":6,"createdTime":"2024-09-06T09:00:11.000+0000","modifiedTime":"2024-09-12T18:07:09.000+0000","archivedTime":null,"type":"Boolean","goal":1.0,"step":0.0,"unit":"Count","etag":"ppkhc2lq","repeatRule":"RRULE:FREQ=WEEKLY;TT_TIMES=4","reminders":["06:00"],"recordEnable":false,"sectionId":"664b1be095e0d66e17a4ea4d","targetDays":0,"targetStartDate":20240906,"completedCycles":0,"exDates":[],"style":1},{"id":"66dacd25dce64115dd6517dd","name":"5 min typing practice","iconRes":"habit_daily_check_in","color":"#97E38B","sortOrder":-2199023255552,"status":0,"encouragement":"","totalCheckIns":4,"createdTime":"2024-09-06T09:36:37.000+0000","modifiedTime":"2024-09-06T09:36:37.000+0000","archivedTime":null,"type":"Boolean","goal":1.0,"step":0.0,"unit":"Count","etag":"ykn8578a","repeatRule":"RRULE:FREQ=DAILY;INTERVAL=2","reminders":["06:00"],"recordEnable":false,"sectionId":"664b1be095e0d66e17a4ea4d","targetDays":0,"targetStartDate":20240906,"completedCycles":0,"exDates":[],"style":1},{"id":"66dacd5fdce64115dd651851","name":"Backup output of `bitwarden` to keepass","iconRes":"habit_daily_check_in","color":"#97E38B","sortOrder":-3298534883328,"status":0,"encouragement":"","totalCheckIns":1,"createdTime":"2024-09-06T09:37:35.000+0000","modifiedTime":"2024-09-06T09:37:35.000+0000","archivedTime":null,"type":"Boolean","goal":1.0,"step":0.0,"unit":"Count","etag":"ltw8pjpe","repeatRule":"RRULE:FREQ=DAILY;INTERVAL=30","reminders":["06:00"],"recordEnable":false,"sectionId":"664b1be095e0d66e17a4ea4d","targetDays":0,"targetStartDate":20240906,"completedCycles":0,"exDates":[],"style":1}]
    '''
    
    habits = json.loads(mock_response)
    long_term_habits_due_today = []

    for habit in habits:
        if is_habit_due_today(habit) and "long term" in habit["name"].lower():
            long_term_habits_due_today.append(habit["name"])

    return long_term_habits_due_today

# Main execution
if __name__ == "__main__":
    long_term_habits = get_long_term_habits_due_today()

    if long_term_habits:
        print("Long-term habits due today:")
        for habit in long_term_habits:
            print(f"- {habit}")
    else:
        print("No long-term habits due today.")
