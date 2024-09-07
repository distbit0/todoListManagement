import re
from datetime import datetime
from utils.general import *
import utils.completion as completion


tasksToDisplayInCLI = getConfig()["tasksToDisplayInCLI"]
tasksToDisplayInMD = getConfig()["tasksToDisplayInMd"]


# PRIORITISATION


# GET PRIORITISATION INFO
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


# MODIFY PRIORITISATION INFO
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


# PRIORITISATION INTERFACE


def askForPriority(todo_path, todo_file, remaining):
    while True:
        priority_input = input(
            f"""\n\n
"5" > assign task priority 5 (1 to {tasksToDisplayInCLI})
"3-4" > swap priorities 3 and 4
"n" or "3-n" > assign priority lower than top {tasksToDisplayInCLI}
"d" or "3-d" > mark todo as done
________________________________
"[title of new note]" > create note from todo
"edit" > edit todo title
"back" > go back to last todo
File: {todo_file}
Remaining: {remaining}
{' > '.join([getTodoSegmentName(segment) for segment in todo_path])}: """
        )
        if priority_input.isdigit() and 1 <= int(priority_input) <= tasksToDisplayInCLI:
            priority = int(priority_input)
            return priority
        elif "-" in priority_input:
            priority = priority_input.split("-")
            return priority
        elif priority_input.lower() in ["edit", "back", "d", "n"]:
            return priority_input.lower()
        elif (
            priority_input
            and priority_input.lower()[0] == "["
            and priority_input.lower()[-1] == "]"
        ):
            return priority_input
        else:
            print("invalid input")


# PRIORTISATION TEXT MANPULATION


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
        if type(getPriorityOfTodo(path)) is int
    ]
    if len(allTodos) == 0:
        return "\n".join(textOutput)
    sortedTodos = sorted(allTodos, key=lambda x: x[0])
    n = min(n, len(sortedTodos))
    for i in range(n):
        priority, path = sortedTodos[i]
        isInProgress = "[/] " in path[-1] or "[-] " in path[-1]
        inProgressText = "[[WIP]]" if isInProgress else ""
        todoName = getTodoSegmentName(path[-1], includeDep=True)
        textOutput.append(f"{priority}) {inProgressText} {todoName}")

    textOutput = "\n".join(textOutput)
    return textOutput


def printTopNTodos(todoPaths):
    tasksToDisplayInCLI = getConfig()["tasksToDisplayInCLI"]
    print(f"\n\n\n\n\n\n\n\n\n\n")
    print(getTopNTodosAsText(todoPaths, tasksToDisplayInCLI))


# PRIORITISATION DETERMINATION
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


# ABSTRACT PRIORITY MODIFICATION
def substitutePriority(prioritySubstitutions, todoPaths):
    for i, task in enumerate(todoPaths):
        taskPriority = getPriorityOfTodo(task)
        if taskPriority in prioritySubstitutions and type(taskPriority) is int:
            if prioritySubstitutions[taskPriority] == "d":
                todoPaths[i] = completion.markTodoAsDone(task)
                prioritySubstitutions[taskPriority] = "n"
            todoPaths[i] = replacePriorityOfTodo(
                task, prioritySubstitutions[taskPriority]
            )
    return todoPaths


def swapPriorities(todoPaths, priority1, priority2):
    priority1 = int(priority1) if priority1.isdigit() else priority1
    priority2 = int(priority2) if priority2.isdigit() else priority2
    if priority2 in ["n", "d"] or priority2 > tasksToDisplayInCLI:
        todoPaths = substitutePriority({priority1: "n"}, todoPaths)
    else:
        todoPaths = substitutePriority({priority1: 1000000}, todoPaths)
        todoPaths = substitutePriority({priority2: 5000000}, todoPaths)
        todoPaths = substitutePriority({1000000: priority2}, todoPaths)
        todoPaths = substitutePriority({5000000: priority1}, todoPaths)
    return todoPaths


# MISC
def getNoOfTodosToPrioritise(todoPaths):
    return len(
        [
            path
            for i, path in enumerate(todoPaths)
            if shouldTodoBePrioritised(todoPaths, i, True)[0]
        ]
    )
