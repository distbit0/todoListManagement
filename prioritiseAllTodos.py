import sys
import utils.general as general
import utils.priority as priorityLib
import utils.parseLists as parseLists
import utils.recurrence as recurrence
import utils.completion as completion
import utils.formatting as formatting

tasksToAssignPriority = general.getConfig()["tasksToAssignPriority"]


def updatePathPriorities(todoPaths, indexOfPath, priority):
    if priority == "d":
        todoMarkedAsDone = completion.markTodoAsDone(todoPaths[indexOfPath])
        print("marked todo as done: ", todoMarkedAsDone)
        todoPaths[indexOfPath] = todoMarkedAsDone
    else:
        if priority != "n":
            prioritySubstitutions = dict(
                [(j, j + 1) for j in range(priority, tasksToAssignPriority + 1)]
            )
            ## added +1 to tasksToAssignPriority so that we do not erase the info re: the priority of a task just because it is no longer in top n
            # prioritySubstitutions[tasksToAssignPriority] = "n" ##commented out this for the same reason as above
            todoPaths = priorityLib.substitutePriority(prioritySubstitutions, todoPaths)
        todoPaths[indexOfPath] = priorityLib.replacePriorityOfTodo(
            todoPaths[indexOfPath], priority
        )

    return todoPaths


def prioritiseUnprioritisedTodos(todoPaths, todoFileName):
    prioritisedPaths = []
    noOfTodosToPrioritise = len(
        [
            path
            for i, path in enumerate(todoPaths)
            if priorityLib.shouldTodoBePrioritised(todoPaths, i, True)[0]
        ]
    )
    prioritisedSoFar = 0
    receivedCtrlC = False
    prioritisedPaths = list(todoPaths)
    for i, path in enumerate(todoPaths):
        shouldBePrioritised = priorityLib.shouldTodoBePrioritised(todoPaths, i, True)[0]
        if shouldBePrioritised:
            try:
                remaining = noOfTodosToPrioritise - prioritisedSoFar - 1
                if not receivedCtrlC:
                    while True:
                        priorityLib.printTopNTodos(
                            prioritisedPaths, tasksToAssignPriority
                        )
                        priority = priorityLib.askForPriority(
                            path, todoFileName, remaining
                        )
                        if type(priority) == list:
                            priority1 = (
                                int(priority[0])
                                if priority[0].isdigit()
                                else priority[0]
                            )
                            priority2 = (
                                int(priority[1])
                                if priority[1].isdigit()
                                else priority[1]
                            )
                            prioritisedPaths = priorityLib.swapPriorities(
                                prioritisedPaths, priority1, priority2
                            )
                            prioritisedPaths = removeGapsInPriorities(prioritisedPaths)
                        else:
                            break
                prioritisedSoFar += 1
            except KeyboardInterrupt:
                receivedCtrlC = True
                print("\n\nskipping all other todos in {}".format(todoFileName))
            else:
                if not receivedCtrlC:
                    prioritisedPaths = updatePathPriorities(
                        prioritisedPaths, i, priority
                    )
                    prioritisedPaths = removeGapsInPriorities(prioritisedPaths)

    return prioritisedPaths, receivedCtrlC


def removePriorityFromParentTodos(todoPaths):
    revisedPaths = []
    # purpose is to prevent ambiguity surrounding priority of a given todo
    for i, path in enumerate(todoPaths):
        isLastPath = i == len(todoPaths) - 1
        hasPriority = priorityLib.getPriorityOfTodo(path)
        hasChild = False if isLastPath else len(todoPaths[i + 1]) > len(todoPaths[i])
        if hasChild and hasPriority:
            path = priorityLib.removePriorityFromTodo(path)
        revisedPaths.append(path)

    outputPaths = []
    for path in revisedPaths:
        reconstructedPath = []
        for i, element in enumerate(path):
            hasChild = i != len(path) - 1
            hasPriority = priorityLib.getPriorityOfTodoSegment(element)
            if hasChild and hasPriority:
                element = priorityLib.removePriorityFromTodoSegment(element)
            reconstructedPath.append(element)
        outputPaths.append(reconstructedPath)

    return outputPaths


def regularisePriorities(todoPaths, setToN=False):
    regularisedTodos = []
    for path in todoPaths:
        priority = priorityLib.getPriorityOfTodo(path)
        if not priority or priority == "n":
            regularisedTodos.append(path)
            continue
        elif type(priority) is int:
            if priority > tasksToAssignPriority and setToN:
                regularisedTodos.append(priorityLib.replacePriorityOfTodo(path, "n"))
            elif priority < 1:
                regularisedTodos.append(priorityLib.replacePriorityOfTodo(path, 1))
            else:
                regularisedTodos.append(path)
        else:
            print("weird priority: {}".format(priority))
            regularisedTodos.append(priorityLib.removePriorityFromTodo(path))
    return regularisedTodos


def deduplicatePriorities(todoPaths):
    prioritiesUsedSoFar = []
    deDupedTodos = []
    for path in todoPaths:
        priority = priorityLib.getPriorityOfTodo(path)
        if priority == "n" or not priority:
            deDupedTodos.append(path)
        elif priority in prioritiesUsedSoFar:
            path = priorityLib.removePriorityFromTodo(path)
            deDupedTodos.append(path)
        else:
            prioritiesUsedSoFar.append(priority)
            deDupedTodos.append(path)

    return deDupedTodos


def removeGapsInPriorities(todos):
    # Step 1: Extract todos with numeric priorities and their indices
    indexed_prioritized_todos = [
        (index, todo)
        for index, todo in enumerate(todos)
        if priorityLib.getPriorityOfTodo(todo) not in [False, "n"]
    ]

    # Step 2: Sort the indexed todos by their priorities
    indexed_prioritized_todos.sort(key=lambda x: priorityLib.getPriorityOfTodo(x[1]))

    # Step 3: Reassign priorities starting from 1
    new_priority = 1
    for index, todo in indexed_prioritized_todos:
        todos[index] = priorityLib.replacePriorityOfTodo(todo, new_priority)
        new_priority += 1

    return todos


def manageRecurringTasks(todoPaths):
    updatedTasks = []
    for todo in todoPaths:
        daysUntilNextOccurrence = recurrence.getTodoDaysToNextOccurrence(todo)
        if daysUntilNextOccurrence == "notRecurring":
            pass
        elif daysUntilNextOccurrence == "noNextOccurrence":
            todo = recurrence.updateTodoNextOccurrence(todo)
        elif daysUntilNextOccurrence <= 0:
            todo = recurrence.updateTodoNextOccurrence(todo)
            todo = priorityLib.replacePriorityOfTodo(todo, 1)
        elif completion.isTodoDone(todo):
            todo = completion.markTodoAsUnDone(todo)
            todo = priorityLib.replacePriorityOfTodo(todo, "n")
        updatedTasks.append(todo)

    return updatedTasks


def triggerReprioritisationIfNecessary(todoPaths):
    outputTodoPaths = []
    try:
        highestPriorityTask = max(
            priorityLib.getPriorityOfTodo(todoPath)
            for todoPath in todoPaths
            if priorityLib.getPriorityOfTodo(todoPath)
            and priorityLib.getPriorityOfTodo(todoPath) != "n"
        )
    except ValueError:
        highestPriorityTask = 0

    if highestPriorityTask <= tasksToAssignPriority / 3:
        print("triggering a reprioritisation")
        outputTodoPaths = [
            (
                priorityLib.removePriorityFromTodo(todoPath)
                if priorityLib.getPriorityOfTodo(todoPath) == "n"
                else todoPath
            )
            for todoPath in todoPaths
        ]
    else:
        outputTodoPaths = todoPaths

    return outputTodoPaths


def formatTodoPaths(todoPaths):
    formattedTodoPaths = []
    for i, path in enumerate(todoPaths):
        isLastPath = i == len(todoPaths) - 1
        hasChild = False if isLastPath else len(todoPaths[i + 1]) > len(todoPaths[i])
        formattedTodoPaths.append(formatting.formatTodo(path, hasChild))

    return todoPaths


def saveErrorData(newText, oldText):
    with open(general.getAbsPath("errorNewText.txt"), "w") as f:
        f.write(newText)
    with open(general.getAbsPath("errorOldText.txt"), "w") as f:
        f.write(oldText)


def addTopTodosToText(text, todoPaths):
    topNTodos = priorityLib.getTopNTodosAsText(todoPaths, tasksToAssignPriority)
    text = "+++++\n" + topNTodos + "\n+++++\n\n" + text
    return text


def checkThatHashesMatch(todoPaths, todoPathsOrig, path, operation):
    inputHash = general.generateTodoListHash(todoPathsOrig)
    outputHash = general.generateTodoListHash(todoPaths)
    if inputHash != outputHash:
        print("input hash: {}, output hash: {}".format(inputHash, outputHash))
        fileText = parseLists.constructFileFromPaths(todoPaths)
        text = parseLists.constructFileFromPaths(todoPathsOrig)
        saveErrorData(fileText, text)
        raise Exception(
            "hashes do not match!!!! for file: {} due to operation {}".format(
                path, operation
            )
        )


# check that priority logic does not assume that hashtag is at the end of the line


def processTodoPaths(text, path, interactive):
    print("processing: {}".format(path))
    todoPathsOrig = parseLists.getAllToDoPaths(text)
    todoPaths = list(todoPathsOrig)
    print(todoPaths)
    functionsToExecute = [
        regularisePriorities,
        manageRecurringTasks,
        removeGapsInPriorities,
        regularisePriorities,  # to account for impact of removeGaps after adding priorities for recurring tasks
        deduplicatePriorities,
        removePriorityFromParentTodos,
        triggerReprioritisationIfNecessary,
        formatTodoPaths,
    ]
    for i, functionToExecute in enumerate(functionsToExecute):
        todoPaths = functionToExecute(todoPaths)
        checkThatHashesMatch(
            todoPaths, todoPathsOrig, path, functionToExecute.__name__ + str(i)
        )

    if interactive:
        fileName = path.split("/")[-1]
        todoPaths = regularisePriorities(todoPaths, setToN=True)
        checkThatHashesMatch(
            todoPaths, todoPathsOrig, path, "regularisePriorities (setToN)"
        )
        todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(todoPaths, fileName)
        checkThatHashesMatch(
            todoPaths, todoPathsOrig, path, "prioritiseUnprioritisedTodos"
        )
        if receivedCtrlC:
            interactive = False
            print("disabling interactive mode for all following files..")

    fileText = parseLists.constructFileFromPaths(todoPaths)
    fileText = addTopTodosToText(fileText, todoPaths)
    return interactive, fileText


def main():
    interactive = True
    onlyInteractiveTodo = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--non-interactive":
            interactive = False
        else:
            onlyInteractiveTodo = sys.argv[1]
            interactive = False

    excludedFiles = general.getConfig()["todosExcludedFromPrioritisation"]
    toDoFiles = general.getAllToDos()
    testFileText = general.readFromFile("testFile.md")
    # toDoFiles = {
    #     "testFile": {"master": {"text": testFileText, "path": "modifiedTestFile.md"}}
    # }
    for file in toDoFiles:
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]
        text = priorityLib.removeTopTodosFromText(text).lstrip("\n")

        if path in excludedFiles:
            continue
        prevInteractiveState = bool(interactive)
        interactive, fileText = processTodoPaths(
            text, path, interactive or str(onlyInteractiveTodo).lower() in path.lower()
        )
        interactive = prevInteractiveState and interactive
        general.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
