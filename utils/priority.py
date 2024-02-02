import re
from datetime import datetime
from utils.utils import *


tasksToAssignPriority = getConfig()["tasksToAssignPriority"]


#### RECURRENCE


## GET RECURRENCE INFO
def getSegmentRecurrenceInfo(todoSegment):
    # Initialize values as None
    periodInDays = None
    lastOccurrence = None

    # Regular expression for the number after '@'
    match_period = re.search(r"@(\d+)", todoSegment)
    if match_period:
        periodInDays = int(match_period.group(1))
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


#### PRIORITISATION


## GET PRIORITISATION INFO
def getPriorityOfTodoSegment(todoSegment):
    match = re.search(
        r" #(\d+|[a-zA-Z])", todoSegment
    )  # Extended pattern to include letters
    if match:
        priority = match.group(1)
        return int(priority) if priority.isdigit() else priority
    return False


def getPriorityOfTodo(todo_path):
    return getPriorityOfTodoSegment(todo_path[-1])


## MODIFY PRIORITISATION INFO
def removePriorityFromTodoSegment(todoSegment):
    return re.sub(r"\s*#(\d+|[a-zA-Z])", "", todoSegment)


def removePriorityFromTodo(todoPath):
    todoPath[-1] = removePriorityFromTodoSegment(todoPath[-1])
    return todoPath


def replacePriorityOfTodoSegment(todoSegment, newPriority):
    newPriorityStr = str(newPriority)  # Ensure newPriority is treated as a string
    if getPriorityOfTodoSegment(todoSegment) is not False:
        todoSegment = re.sub(r"\s*#(\d+|[a-zA-Z])", f" #{newPriorityStr}", todoSegment)
    else:
        todoSegment += f" #{newPriorityStr}"
    return todoSegment.strip()


def replacePriorityOfTodo(todoPath, newPriority):
    todoPath[-1] = replacePriorityOfTodoSegment(todoPath[-1], newPriority)
    return todoPath


#### COMPLETION


## GET COMPLETION INFO
def isTodoSegmentDone(todoSegment):
    return "- [x] " in todoSegment


def isTodoDone(todoPath):
    return isTodoSegmentDone(todoPath[-1])


## MODIFY COMPLETION INFO
def markTodoSegmentAsDone(todoSegment):
    todoSegment = todoSegment.replace("- [ ] ", "- [x] ")
    todoSegment = todoSegment.replace("- [/] ", "- [x] ")
    return todoSegment


def markTodoAsDone(todoPath):
    todoPath[-1] = markTodoSegmentAsDone(todoPath[-1])
    return todoPath


def markTodoSegmentAsUnDone(todoSegment):
    todoSegment = todoSegment.replace("- [x] ", "- [ ] ")
    todoSegment = todoSegment.replace("- [/] ", "- [ ] ")
    return todoSegment


def markTodoAsUnDone(todoPath):
    todoPath[-1] = markTodoSegmentAsUnDone(todoPath[-1])
    return todoPath


#### PRIORITISATION INTERFACE


def askForPriority(todo_path, todo_file, remaining):
    while True:
        priority_input = input(
            f"\n\n\nPrioritise (0 - {tasksToAssignPriority} OR 'n' if not in top {tasksToAssignPriority} or 3-4 to swap priorities 3 and 4 or d to 'delete'):\nFile: {todo_file}\nRemaining: {remaining}\n{' '.join(todo_path)}: "
        )
        if (
            priority_input.isdigit()
            and 1 <= int(priority_input) <= tasksToAssignPriority
        ):
            priority = int(priority_input)
            return priority
        elif priority_input.lower() == "n":
            return priority_input.lower()
        elif "-" in priority_input:
            priority = priority_input.split("-")
            return priority
        elif priority_input.lower() == "d":
            return "d"
        else:
            print("invalid input")


#### PRIORTISATION TEXT MANPULATION


def removeTopTodosFromText(text):
    pattern = r"^\+{5}\n(.|\n)*?\+{5}$"
    text = re.sub(pattern, "", text, flags=re.MULTILINE)
    return text


def getTopNTodosAsText(todoPaths, n):
    textOutput = []
    textOutput.append(f"Top {n} todos:")
    allTodos = [
        (getPriorityOfTodo(path), path)
        for path in todoPaths
        if getPriorityOfTodo(path) and getPriorityOfTodo(path) != "n"
    ]
    if len(allTodos) == 0:
        return "\n".join(textOutput)
    sortedTodos = sorted(allTodos, key=lambda x: x[0])
    n = min(n + 1, len(sortedTodos))
    for i in range(n):
        priority, path = sortedTodos[i]
        todoName = (
            path[-1].replace("- [x] ", "").replace("- [/] ", "").replace("- [ ] ", "")
        )
        todoName = " ".join(
            [
                segment
                for segment in todoName.split()
                if "@" not in segment and "^" not in segment and "#" not in segment
            ]
        )
        textOutput.append(f"{priority}) {todoName}")

    textOutput = "\n".join(textOutput)
    return textOutput


def printTopNTodos(todoPaths, n):
    print(f"\n\n\n\n\n\n\n\n\n\n")
    print(getTopNTodosAsText(todoPaths, n))


#### PRIORITISATION DETERMINATION
def shouldTodoBePrioritised(todoPaths, i, mustNotBeAlreadyPrioritised):
    path = todoPaths[i]
    isLastTodoInList = len(todoPaths) - 1 == i
    if isLastTodoInList:
        hasNoChildren = True
    else:
        hasNoChildren = len(todoPaths[i + 1]) <= len(todoPaths[i])
    isNotHashTag = not (len(path) == 1 and path[0].startswith("#"))
    hasCheckBox = "- [ ] " in path[-1] or "- [/] " in path[-1]
    todoPriority = getPriorityOfTodo(path)
    shouldBePrioritised = hasNoChildren and isNotHashTag and hasCheckBox
    if mustNotBeAlreadyPrioritised:
        shouldBePrioritised = shouldBePrioritised and not todoPriority
    return shouldBePrioritised, hasNoChildren


#### ERROR CHECKING
def generateTodoListHash(todoPaths):
    indentHash = 0
    base = 257  # A prime number used as the base for the polynomial hash
    mod = 248900  # Modulus for keeping the hash values manageable
    for todo in todoPaths:
        indentation = len(todo)
        indentHash = (indentHash * base + indentation) % mod
    pathCount = len(todoPaths)
    indentSum = sum(len(todo) for todo in todoPaths)
    return (indentHash, indentSum, pathCount)


#### ABSTRACT PRIORITY MODIFICATION
def substitePriority(prioritySubstitutions, todoPaths):
    for i, task in enumerate(todoPaths):
        taskPriority = getPriorityOfTodo(task)
        if taskPriority in prioritySubstitutions:
            todoPaths[i] = replacePriorityOfTodo(
                task, prioritySubstitutions[taskPriority]
            )
    return todoPaths


def swapPriorities(todoPaths, priority1, priority2):
    if priority2 == "n" or priority2 > tasksToAssignPriority:
        todoPaths = substitePriority({priority1: "n"}, todoPaths)
    else:
        todoPaths = substitePriority({priority1: 1000000}, todoPaths)
        todoPaths = substitePriority({priority2: 5000000}, todoPaths)
        todoPaths = substitePriority({1000000: priority2}, todoPaths)
        todoPaths = substitePriority({5000000: priority1}, todoPaths)
    return todoPaths
