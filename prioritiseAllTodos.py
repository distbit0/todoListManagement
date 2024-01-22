import utils.utils as utils
import sys
import utils.toDo as toDo


def getPriorityOfToDo(todoPath):
    try:
        potentialPriority = float(todoPath[-1].split("#")[-1].strip(" "))
    except:
        return False
    else:
        if 0 <= potentialPriority <= 99:
            return potentialPriority
        else:
            return False


def askForPriority(todoPath, todoFileName, remaining):
    priority = input(
        "\n\n\nPrioritise (0 - 99):\nFile: "
        + todoFileName
        + "\nRemaining: "
        + str(remaining)
        + "\n"
        + " ".join(todoPath)
        + ": "
    )
    try:
        priority = float(priority)
    except:
        print("Invalid input")
        return askForPriority(todoPath, todoFileName, remaining)
    else:
        todoPath = replacePriorityOfTodo(todoPath, priority)
        return todoPath


def replacePriorityOfTodo(todoPath, newPriority):
    if getPriorityOfToDo(todoPath):
        todoPath[-1] = "#".join(todoPath[-1].split("#")[:-1]) + " #" + str(newPriority)
    else:
        todoPath[-1] = todoPath[-1] + " #" + str(newPriority)
    todoPath[-1] = todoPath[-1].replace("  ", " ")
    return todoPath


def checkIfTodoShouldBePrioritised(todoPaths, i):
    path = todoPaths[i]
    isLastTodoInList = len(todoPaths) - 1 == i
    if isLastTodoInList:
        hasNoChildren = True
    else:
        hasNoChildren = len(todoPaths[i + 1]) <= len(todoPaths[i])
    isNotHashTag = not (len(path) == 1 and path[0].startswith("#"))
    hasCheckBox = "- [ ] " in path[-1] or "- [x] " in path[-1] or "- [/] " in path[-1]
    todoPriority = getPriorityOfToDo(path)

    return hasNoChildren and isNotHashTag and hasCheckBox and (not todoPriority)


def prioritiseUnprioritisedTodos(todoPaths, todoFileName):
    prioritisedPaths = []
    noOfTodosToPrioritise = len(
        [
            path
            for i, path in enumerate(todoPaths)
            if checkIfTodoShouldBePrioritised(todoPaths, i)
        ]
    )
    for i, path in enumerate(todoPaths):
        if checkIfTodoShouldBePrioritised(todoPaths, i):
            remaining = noOfTodosToPrioritise - i - 1
            path = askForPriority(path, todoFileName, remaining)
        prioritisedPaths.append(path)

    return prioritisedPaths


def evenly_distribute_values(data, max_new):
    if not isinstance(data, dict) or not isinstance(max_new, (int, float)):
        raise TypeError(
            "Invalid input types. 'data' must be a dictionary and 'max_new' must be a number."
        )

    if len(data) == 0:
        return {}

    # Sorting the values and assigning ranks
    sorted_values = sorted((value, key) for key, value in data.items() if value)
    ranks = {key: rank for rank, (_, key) in enumerate(sorted_values)}

    # Total number of items
    total_items = len(list(ranks.keys()))

    # Assigning each value a percentile and scaling it to the new range
    distributed_data = {}
    for key in data:
        if data[key]:
            # Percentile is the rank of the value divided by the total number of items
            percentile = (ranks[key] + 1) / total_items
            # The new value is the percentile multiplied by the new range
            distributed_data[key] = int(percentile * max_new)
        else:
            distributed_data[key] = False

    return distributed_data


def normalisePriorities(todoPaths):
    pathPriorities = {}
    for path in todoPaths:
        priority = getPriorityOfToDo(path)
        if not priority:
            pathPriorities[str(path)] = False
        else:
            pathPriorities[str(path)] = priority
    pathPriorities = evenly_distribute_values(pathPriorities, 99)
    normalisedPaths = []
    for path in todoPaths:
        if pathPriorities[str(path)]:
            path = replacePriorityOfTodo(path, pathPriorities[str(path)])
        normalisedPaths.append(path)

    return normalisedPaths


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
        nonInteractive = True
    else:
        nonInteractive = False
    excludedFiles = utils.getConfig()["todosExcludedFromPrioritisation"]
    toDoFiles = utils.getAllToDos()
    for file in toDoFiles:
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]
        if path in excludedFiles:
            continue
        todoPaths = toDo.getAllToDoPaths(text)
        if not nonInteractive:
            todoPaths = prioritiseUnprioritisedTodos(todoPaths, path.split("/")[-1])
        todoPaths = normalisePriorities(todoPaths)
        fileText = toDo.constructFileFromPaths(todoPaths)
        with open(path, "w") as f:
            f.write(fileText)


if __name__ == "__main__":
    main()
