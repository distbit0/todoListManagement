import utils.utils as utils
import sys
import utils.toDo as toDo


def getPriorityOfTodoSegment(todoSegment):
    try:
        potentialPriorityString = todoSegment.split("#")[-1].strip()
        return (
            float(potentialPriorityString)
            if 0 <= float(potentialPriorityString) <= 99
            else False
        )
    except ValueError:
        return False


def getPriorityOfToDo(todo_path):
    return getPriorityOfTodoSegment(todo_path[-1])


def askForPriority(todo_path, todo_file, remaining):
    while True:
        priority_input = input(
            f"\n\n\nPrioritise (0 - 99):\nFile: {todo_file}\nRemaining: {remaining}\n{' '.join(todo_path)}: "
        )
        try:
            priority = float(priority_input)
            return replacePriorityOfTodo(todo_path, priority)
        except ValueError:
            print("Invalid input")


def replacePriorityOfTodoSegment(todoSegment, newPriority):
    if getPriorityOfTodoSegment(todoSegment):
        todoSegment = "#".join(todoSegment.split("#")[:-1]) + " #" + str(newPriority)
    else:
        todoSegment = todoSegment + " #" + str(newPriority)
    todoSegment = todoSegment.replace("  ", " ")
    return todoSegment


def removePriorityFromTodoSegment(todoSegment):
    if getPriorityOfTodoSegment(todoSegment):
        todoSegment = "#".join(todoSegment.split("#")[:-1])
    return todoSegment


def replacePriorityOfTodo(todoPath, newPriority):
    todoPath[-1] = replacePriorityOfTodoSegment(todoPath[-1], newPriority)
    return todoPath


def shouldTodoBePrioritised(todoPaths, i, mustNotBeAlreadyPrioritised):
    path = todoPaths[i]
    isLastTodoInList = len(todoPaths) - 1 == i
    if isLastTodoInList:
        hasNoChildren = True
    else:
        hasNoChildren = len(todoPaths[i + 1]) <= len(todoPaths[i])
    isNotHashTag = not (len(path) == 1 and path[0].startswith("#"))
    hasCheckBox = "- [ ] " in path[-1] or "- [x] " in path[-1] or "- [/] " in path[-1]
    todoPriority = getPriorityOfToDo(path)
    shouldBePrioritised = hasNoChildren and isNotHashTag and hasCheckBox
    if mustNotBeAlreadyPrioritised:
        shouldBePrioritised = shouldBePrioritised and not todoPriority
    return shouldBePrioritised, hasNoChildren


def prioritiseUnprioritisedTodos(todoPaths, todoFileName):
    prioritisedPaths = []
    noOfTodosToPrioritise = len(
        [
            path
            for i, path in enumerate(todoPaths)
            if shouldTodoBePrioritised(todoPaths, i, True)[0]
        ]
    )
    prioritisedSoFar = 0
    for i, path in enumerate(todoPaths):
        shouldBePrioritised, hasNoChildren = shouldTodoBePrioritised(todoPaths, i, True)
        if shouldBePrioritised:
            remaining = noOfTodosToPrioritise - prioritisedSoFar - 1
            path = askForPriority(path, todoFileName, remaining)
            prioritisedSoFar += 1
        if hasNoChildren:
            ## to prevent dupplication due to paths being implicitly generated which do not match parent path
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


def assignPriorityOfParentsToChildren(todoPaths):
    outputPaths = []
    for path in todoPaths:
        parentSegmentPriority = False
        reconstructedPath = []
        for i, element in enumerate(path):
            isLastElement = i == len(path) - 1
            hasPriority = getPriorityOfTodoSegment(element)
            if hasPriority and not isLastElement:
                parentSegmentPriority = hasPriority
                element = removePriorityFromTodoSegment(element)
            if isLastElement and parentSegmentPriority and not hasPriority:
                element = replacePriorityOfTodoSegment(element, parentSegmentPriority)
            reconstructedPath.append(element)
        outputPaths.append(reconstructedPath)

    return outputPaths


def normalisePriorities(todoPaths):
    pathPriorities = {}
    for i, path in enumerate(todoPaths):
        shouldBePrioritised = shouldTodoBePrioritised(todoPaths, i, False)[0]
        if shouldBePrioritised:
            pathPriorities[str(path)] = getPriorityOfToDo(path)
        else:
            pathPriorities[str(path)] = False

    pathPriorities = evenly_distribute_values(pathPriorities, 99)
    normalisedPaths = []
    for i, path in enumerate(todoPaths):
        hasNoChildren = shouldTodoBePrioritised(todoPaths, i, False)[1]
        if pathPriorities[str(path)]:
            path = replacePriorityOfTodo(path, pathPriorities[str(path)])
        if hasNoChildren:
            # no need to add it to normalisedPaths if it has children, as it will be auto-regenerated by writeToFile
            normalisedPaths.append(path)

    return normalisedPaths


def main():
    interactive = True
    if len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
        interactive = False
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
        todoPaths = assignPriorityOfParentsToChildren(todoPaths)
        if interactive:
            todoPaths = prioritiseUnprioritisedTodos(todoPaths, path.split("/")[-1])
        todoPaths = normalisePriorities(todoPaths)
        fileText = toDo.constructFileFromPaths(todoPaths)
        utils.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
