import re
from datetime import datetime, timedelta


# RECURRENCE

# GET RECURRENCE INFO

dateRegex = r"\^(\d{1,2}/\d{1,2})"
recurrenceRegex = r"@(\d+)"


def getTodoSegmentRecurrencePeriod(todoSegment):
    periodInDays = "noPeriod"
    # Regular expression for the number after '@'
    match_period = re.search(recurrenceRegex, todoSegment)
    if match_period:
        periodInDays = match_period.group(1)
        if periodInDays.isdigit():
            periodInDays = int(periodInDays)

    return periodInDays


def getTodoRecurrencePeriod(todoPath):
    return getTodoSegmentRecurrencePeriod(todoPath[-1])


def getTodoSegmentNextOccurrence(todoSegment):
    nextOccurrence = "noNextOccurrence"
    # Regular expression for the date in 'dd/mm' format
    match_date = re.search(dateRegex, todoSegment)
    if match_date:
        date_str = match_date.group(1)
        date = datetime.strptime(date_str, "%d/%m")
        nextOccurrence = (date - datetime(date.year, 1, 1)).days + 1
    return nextOccurrence


def getTodoNextOccurrence(todoPath):
    return getTodoSegmentNextOccurrence(todoPath[-1])


def getTodoSegmentDaysToNextOccurrence(todoSegment):
    periodInDays = getTodoSegmentRecurrencePeriod(todoSegment)
    nextOccurrence = getTodoSegmentNextOccurrence(todoSegment)
    if nextOccurrence == "noNextOccurrence":
        if periodInDays == "noPeriod":
            return "notRecurring"
        return "noNextOccurrence"

    currentDaysInYear = (datetime.now() - datetime(datetime.now().year, 1, 1)).days

    daysUntilNextOccurrence = nextOccurrence - currentDaysInYear
    if type(nextOccurrence) is int and daysUntilNextOccurrence <= 0:
        print(
            todoSegment,
            "next occurrence: ",
            nextOccurrence,
            "periodInDays: ",
            periodInDays,
            "daysUntilNextOccurrence: ",
            daysUntilNextOccurrence,
        )
    return daysUntilNextOccurrence


def getTodoDaysToNextOccurrence(todoPath):
    return getTodoSegmentDaysToNextOccurrence(todoPath[-1])


# MODIFY RECURRENCE INFO


def updateTodoSegmentNextOccurrence(todoSegment):
    recurrencePeriod = getTodoSegmentRecurrencePeriod(todoSegment)
    nextOccurenceDate = ""
    if recurrencePeriod != "noPeriod":
        nextOccurenceDate = datetime.now() + timedelta(days=recurrencePeriod)
        nextOccurenceDate = "^" + nextOccurenceDate.strftime("%d/%m")

    if re.search(dateRegex, todoSegment):
        updated_task = re.sub(dateRegex, nextOccurenceDate, todoSegment)
    else:
        updated_task = f"{todoSegment} {nextOccurenceDate}".rstrip(" ")

    return updated_task


def updateTodoNextOccurrence(todoPath):
    todoPath[-1] = updateTodoSegmentNextOccurrence(todoPath[-1])
    return todoPath
