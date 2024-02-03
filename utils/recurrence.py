import re
from datetime import datetime


#### RECURRENCE


## GET RECURRENCE INFO
def getSegmentRecurrenceInfo(todoSegment):
    # Initialize values as None
    periodInDays = None
    lastOccurrence = None

    # Regular expression for the number after '@'
    match_period = re.search(r"@(\d+)", todoSegment)
    if match_period:
        periodInDays = match_period.group(1)
        if periodInDays.isdigit():
            periodInDays = int(periodInDays)
        else:
            return "noPeriod"
    else:
        return "noPeriod"

    currentDaysInYear = (datetime.now() - datetime(datetime.now().year, 1, 1)).days + 1
    # Regular expression for the date in 'dd/mm' format
    match_date = re.search(r"\^(\d{1,2}/\d{1,2})", todoSegment)
    if match_date:
        date_str = match_date.group(1)
        date = datetime.strptime(date_str, "%d/%m")
        lastOccurrence = (date - datetime(date.year, 1, 1)).days + 1
    else:
        return "noLastOccurence"

    daysUntilNextOccurrence = (lastOccurrence + periodInDays) - currentDaysInYear

    return daysUntilNextOccurrence


def getTodoRecurrenceInfo(todoPath):
    return getSegmentRecurrenceInfo(todoPath[-1])


## MODIFY RECURRENCE INFO


def updateTodoSegmentLastOccurrence(todoSegment):
    # Get current date in 'dd/mm' format
    current_date = datetime.now().strftime("%d/%m")

    # Regular expression to check if the date specifier exists
    if re.search(r"\^\d{1,2}/\d{1,2}", todoSegment):
        # If exists, update it
        updated_task = re.sub(r"\^\d{1,2}/\d{1,2}", f"^{current_date}", todoSegment)
    else:
        # If not, add it
        updated_task = f"{todoSegment} ^{current_date}"

    return updated_task


def updateTodoLastOccurence(todoPath):
    todoPath[-1] = updateTodoSegmentLastOccurrence(todoPath[-1])
    return todoPath
