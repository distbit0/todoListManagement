import re
from datetime import datetime
from utils.general import *


tasksToAssignPriority = getConfig()["tasksToAssignPriority"]


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
        isInProgress = "[/] " in path[-1] or "[-] " in path[-1]
        inProgressText = "[[WIP]]" if isInProgress else ""
        todoName = (
            path[-1]
            .replace("- [x] ", "")
            .replace("- [/] ", "")
            .replace("- [ ] ", "")
            .replace("- [-] ", "")
        )
        todoName = " ".join(
            [
                segment
                for segment in todoName.split()
                if "@" not in segment and "^" not in segment and "#" not in segment
            ]
        )
        textOutput.append(f"{priority}) {inProgressText} {todoName}")

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


#### ABSTRACT PRIORITY MODIFICATION
def substitutePriority(prioritySubstitutions, todoPaths):
    for i, task in enumerate(todoPaths):
        taskPriority = getPriorityOfTodo(task)
        if taskPriority in prioritySubstitutions:
            todoPaths[i] = replacePriorityOfTodo(
                task, prioritySubstitutions[taskPriority]
            )
    return todoPaths


def swapPriorities(todoPaths, priority1, priority2):
    # if priority2 == "n" or priority2 > tasksToAssignPriority: (commented this out so that we can recover these prioritisations even if they are for now not in top n
    if priority2 == "n":
        todoPaths = substitutePriority({priority1: "n"}, todoPaths)
    else:
        todoPaths = substitutePriority({priority1: 1000000}, todoPaths)
        todoPaths = substitutePriority({priority2: 5000000}, todoPaths)
        todoPaths = substitutePriority({1000000: priority2}, todoPaths)
        todoPaths = substitutePriority({5000000: priority1}, todoPaths)
    return todoPaths
