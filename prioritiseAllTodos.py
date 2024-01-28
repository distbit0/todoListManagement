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


def generateTodoListHash(todoText, todoPaths):
    indentHash = 0
    base = 257  # A prime number used as the base for the polynomial hash
    mod = 2489  # Modulus for keeping the hash values manageable
    for todo in todoPaths:
        indentation = len(todo)
        indentHash = (indentHash * base + indentation) % mod
    indentSum = sum(len(todo) for todo in todoPaths)
    lineCount = len(todoText.strip().split("\n"))
    return (indentHash, indentSum, lineCount)


def getPriorityOfToDo(todo_path):
    return getPriorityOfTodoSegment(todo_path[-1])


def askForPriority(todo_path, todo_file, remaining):
    while True:
        priority_input = input(
            f"\n\n\nPrioritise (0 - 10):\nFile: {todo_file}\nRemaining: {remaining}\n{' '.join(todo_path)}: "
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


def printRepresentativeTodos(todoPaths, n):
    if n <= 0:
        raise ValueError("Number of percentiles (n) must be greater than 0")
    print(f"\n\n\nRepresentative {n} todos:")
    allTodos = [
        (getPriorityOfToDo(path), path) for path in todoPaths if getPriorityOfToDo(path)
    ]
    if len(allTodos) == 0:
        print("no prioritised todos")
        return
    sortedTodos = sorted(allTodos, key=lambda x: x[0])
    totalTodos = len(sortedTodos)
    for i in range(n):
        percentileIndex = int(totalTodos * (i / n))
        percentileIndex = min(
            percentileIndex, totalTodos - 1
        )  # Ensure index is within bounds
        priority, path = sortedTodos[percentileIndex]
        print(f"{priority} {path[-1]}")


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
    receivedCtrlC = False
    for i, path in enumerate(todoPaths):
        shouldBePrioritised = shouldTodoBePrioritised(todoPaths, i, True)[0]
        if shouldBePrioritised:
            try:
                remaining = noOfTodosToPrioritise - prioritisedSoFar - 1
                if not receivedCtrlC:
                    printRepresentativeTodos(todoPaths, 8)
                    path = askForPriority(path, todoFileName, remaining)
                prioritisedSoFar += 1
            except KeyboardInterrupt:
                receivedCtrlC = True
                print("skipping all other todos in {}".format(todoFileName))
        prioritisedPaths.append(path)

    return prioritisedPaths, receivedCtrlC


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


def removeParentPaths(todoPaths):
    filteredPaths = []
    for i, path in enumerate(todoPaths):
        hasNoChildren = shouldTodoBePrioritised(todoPaths, i, False)[1]
        if hasNoChildren:
            filteredPaths.append(path)
    return filteredPaths


def main():
    interactive = True
    if len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
        interactive = False
    excludedFiles = utils.getConfig()["todosExcludedFromPrioritisation"]
    toDoFiles = utils.getAllToDos()
    # testFileText = utils.readFromFile("testFile.md")
    # toDoFiles = {
    #     "testFile": {"master": {"text": testFileText, "path": "modifiedTestFile.md"}}
    # }
    for file in toDoFiles:
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]
        if path in excludedFiles:
            continue
        todoPathsOrig = toDo.getAllToDoPaths(text)
        todoPaths = assignPriorityOfParentsToChildren(todoPathsOrig)
        if interactive:
            todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(
                todoPaths, path.split("/")[-1]
            )
            if receivedCtrlC:
                interactive = False
                print("disabling interactive mode for all following files..")

        todoPaths = normalisePriorities(todoPaths)
        onlyChildTodoPaths = removeParentPaths(
            todoPaths
        )  ## this is not idempotent so very important to run it only once. otherwise will delete paths
        fileText = toDo.constructFileFromPaths(onlyChildTodoPaths)
        inputHash = generateTodoListHash(text, todoPathsOrig)
        outputHash = generateTodoListHash(fileText, todoPaths)
        if inputHash != outputHash:
            raise Exception("hashes do not match!!!!")
        print("hashes match for {}".format(path))
        utils.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
