import pysnooper
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
                [(j, j + 1) for j in range(priority, tasksToAssignPriority)]
            )
            prioritySubstitutions[tasksToAssignPriority] = "n"
            # the new solution is to just set tasksToAssignPriority to be higher than the number of tasks displayed. so a task's priority is not immediately erased (set to n) after exceeding the number of tasks displayed. only when it actually exceeds tasksToAssignPriority will it be erased.
            todoPaths = priorityLib.substitutePriority(prioritySubstitutions, todoPaths)
        todoPaths[indexOfPath] = priorityLib.replacePriorityOfTodo(
            todoPaths[indexOfPath], priority
        )

    return todoPaths


def prioritiseUnprioritisedTodos(
    todoPaths, todoFileName, todosPerPrioritisationSession
):
    prioritisedPaths = []
    noOfTodosToPrioritise = priorityLib.getNoOfTodosToPrioritise(todoPaths)
    noOfTodosToPrioritise = min(noOfTodosToPrioritise, todosPerPrioritisationSession)
    prioritisedSoFar = 0
    receivedCtrlC = False
    prioritisedPaths = list(todoPaths)
    i = 0
    while i < len(todoPaths):
        path = todoPaths[i]
        goBack = False
        shouldBePrioritised = priorityLib.shouldTodoBePrioritised(todoPaths, i, True)[0]
        if shouldBePrioritised and prioritisedSoFar < noOfTodosToPrioritise:
            try:
                remaining = noOfTodosToPrioritise - prioritisedSoFar - 1
                if not receivedCtrlC:
                    while True:
                        priorityLib.printTopNTodos(prioritisedPaths)
                        priority = priorityLib.askForPriority(
                            path, todoFileName, remaining
                        )
                        if priority == "back" and i > 0:
                            prioritisedPaths[i - 1] = (
                                priorityLib.removePriorityFromTodo(
                                    prioritisedPaths[i - 1]
                                )
                            )
                            i -= 2
                            prioritisedSoFar -= 2
                            goBack = True
                            break
                        elif type(priority) == list:
                            prioritisedPaths = priorityLib.swapPriorities(
                                prioritisedPaths, priority[0], priority[1]
                            )
                            prioritisedPaths = removeGapsInPriorities(prioritisedPaths)
                        elif str(priority)[0] == "[" and str(priority)[-1] == "]":
                            prioritisedPaths = formatting.createNoteFromTodo(
                                prioritisedPaths, path, priority
                            )
                        elif priority == "edit":
                            prioritisedPaths = formatting.renameTodo(
                                prioritisedPaths, path
                            )
                        else:
                            break
                prioritisedSoFar += 1
            except KeyboardInterrupt:
                receivedCtrlC = True
                print("\n\nskipping all other todos in {}".format(todoFileName))
            else:
                if not receivedCtrlC and not goBack:
                    prioritisedPaths = updatePathPriorities(
                        prioritisedPaths, i, priority
                    )
                    prioritisedPaths = removeGapsInPriorities(prioritisedPaths)
        i += 1
    return prioritisedPaths, receivedCtrlC


def autoCreateNotesFromTodos(todoPaths):
    outputTodos = list(todoPaths)
    for i, path in enumerate(todoPaths):
        isATodo = priorityLib.shouldTodoBePrioritised(todoPaths, i, False)[0]
        if isATodo:
            outputTodos = formatting.createNoteFromTodo(
                outputTodos, path, "", autoCreate=True
            )
    return outputTodos


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


def regularisePriorities(todoPaths):
    regularisedTodos = []
    for path in todoPaths:
        priority = priorityLib.getPriorityOfTodo(path)
        if not priority or priority == "n":
            regularisedTodos.append(path)
            continue
        elif type(priority) is int:
            if priority > tasksToAssignPriority:
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
    indexed_prioritized_todos = [
        (index, todo)
        for index, todo in enumerate(todos)
        if priorityLib.getPriorityOfTodo(todo) not in [False, "n"]
    ]

    indexed_prioritized_todos.sort(key=lambda x: priorityLib.getPriorityOfTodo(x[1]))

    # Reassign priorities starting from 1
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

    if highestPriorityTask == 0:
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
    topNTodos = priorityLib.getTopNTodosAsText(todoPaths)
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


def processTodoPaths(
    todoPathsOrig, filePath, interactive, todosPerPrioritisationSession
):
    print("processing: {}".format(filePath))
    todoPaths = list(todoPathsOrig)
    excludedFunctions = general.getConfig()["functionsExcludedFromTodos"].get(
        filePath.split("/")[-1], []
    )
    functionsToExecute = [
        regularisePriorities,
        manageRecurringTasks,
        removeGapsInPriorities,
        regularisePriorities,  # to account for impact of removeGaps after adding priorities for recurring tasks
        deduplicatePriorities,
        removePriorityFromParentTodos,
        triggerReprioritisationIfNecessary,
        autoCreateNotesFromTodos,
        formatTodoPaths,
    ]
    for i, functionToExecute in enumerate(functionsToExecute):
        functionName = functionToExecute.__name__
        if functionName in excludedFunctions:
            continue
        todoPaths = functionToExecute(todoPaths)
        checkThatHashesMatch(todoPaths, todoPathsOrig, filePath, functionName + str(i))

    if interactive:
        receivedCtrlC = False
        fileName = filePath.split("/")[-1]
        if "regularisePriorities" not in excludedFunctions:
            todoPaths = regularisePriorities(todoPaths)
            checkThatHashesMatch(
                todoPaths, todoPathsOrig, filePath, "regularisePriorities (setToN)"
            )
        if "prioritiseUnprioritisedTodos" not in excludedFunctions:
            todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(
                todoPaths, fileName, todosPerPrioritisationSession
            )
            checkThatHashesMatch(
                todoPaths, todoPathsOrig, filePath, "prioritiseUnprioritisedTodos"
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

    toDoFiles = general.getAllToDos()
    # testFileText = general.readFromFile("testFile.md")
    # toDoFiles = {
    #     "testFile": {"master": {"text": testFileText, "path": "modifiedTestFile.md"}}
    # }
    processedTodos = 0
    toDoFiles = dict(
        sorted(
            toDoFiles.items(),
            key=lambda x: priorityLib.getNoOfTodosToPrioritise(
                parseLists.getAllToDoPaths(
                    priorityLib.removeTopTodosFromText(x[1]["master"]["text"]).strip(
                        "\n"
                    )
                )
            ),
        )
    )  # sort so that todo lists with fewest unprocessed todos are processed first, to evenly distribute workload across all todo lists
    for i, file in enumerate(toDoFiles):
        todosPerPrioritisationSession = general.getConfig()[
            "todosPerPrioritisationSession"
        ]
        todosPerPrioritisationSession *= (i + 1) / len(toDoFiles)
        todosPerPrioritisationSession -= processedTodos
        todosPerPrioritisationSession = int(todosPerPrioritisationSession)
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]

        excludedFunctions = general.getConfig()["functionsExcludedFromTodos"].get(
            path.split("/")[-1], []
        )
        if "all" in excludedFunctions:
            continue
        text = priorityLib.removeTopTodosFromText(text).lstrip("\n")
        prevInteractiveState = bool(interactive)
        todoPathsOrig = parseLists.getAllToDoPaths(text)
        processedTodos += min(
            priorityLib.getNoOfTodosToPrioritise(todoPathsOrig),
            todosPerPrioritisationSession,
        )
        interactive, fileText = processTodoPaths(
            todoPathsOrig,
            path,
            interactive or str(onlyInteractiveTodo).lower() in path.lower(),
            todosPerPrioritisationSession,
        )
        interactive = prevInteractiveState and interactive
        general.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
