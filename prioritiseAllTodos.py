import sys
import utils.general as general
import utils.priority as priorityLib
import utils.parseLists as parseLists
import utils.recurrence as recurrence
import utils.completion as completion

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
            todoPaths = priorityLib.substitePriority(prioritySubstitutions, todoPaths)
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


def assignPriorityOfParentsToChildren(todoPaths):
    outputPaths = []
    for path in todoPaths:
        parentSegmentPriority = False
        reconstructedPath = []
        for i, element in enumerate(path):
            isLastElement = i == len(path) - 1
            hasPriority = priorityLib.getPriorityOfTodoSegment(element)
            if hasPriority and not isLastElement:
                parentSegmentPriority = hasPriority
                element = priorityLib.removePriorityFromTodoSegment(element)
            if isLastElement and parentSegmentPriority and not hasPriority:
                element = priorityLib.replacePriorityOfTodoSegment(
                    element, parentSegmentPriority
                )
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
        if daysUntilNextOccurrence == "noPeriod":
            pass
        elif daysUntilNextOccurrence == "noLastOccurrence":
            todo = recurrence.updateTodoLastOccurrence(todo)
        elif daysUntilNextOccurrence <= 0:
            todo = recurrence.updateTodoLastOccurrence(todo)
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


def saveErrorData(newText, oldText):
    with open(general.getAbsPath("errorNewText.txt"), "w") as f:
        f.write(newText)
    with open(general.getAbsPath("errorOldText.txt"), "w") as f:
        f.write(oldText)


def addTopTodosToText(text, todoPaths):
    topNTodos = priorityLib.getTopNTodosAsText(todoPaths, tasksToAssignPriority)
    text = "+++++\n" + topNTodos + "\n+++++\n\n" + text
    return text


# check that priority logic does not assume that hashtag is at the end of the line


def processTodoPaths(text, path, interactive):
    todoPathsOrig = parseLists.getAllToDoPaths(text)
    todoPaths = regularisePriorities(todoPathsOrig)
    todoPaths = manageRecurringTasks(todoPaths)
    todoPaths = removeGapsInPriorities(todoPaths)
    todoPaths = regularisePriorities(
        todoPathsOrig
    )  # to account for impact of removeGaps after adding priorities for recurring tasks
    todoPaths = deduplicatePriorities(todoPaths)
    todoPaths = assignPriorityOfParentsToChildren(todoPaths)
    todoPaths = triggerReprioritisationIfNecessary(todoPaths)

    if interactive:
        fileName = path.split("/")[-1]
        todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(todoPaths, fileName)
        if receivedCtrlC:
            interactive = False
            print("disabling interactive mode for all following files..")

    fileText = parseLists.constructFileFromPaths(todoPaths)
    inputHash = general.generateTodoListHash(todoPathsOrig)
    outputHash = general.generateTodoListHash(todoPaths)
    if inputHash != outputHash:
        print("input hash: {}, output hash: {}".format(inputHash, outputHash))
        saveErrorData(fileText, text)
        raise Exception("hashes do not match!!!!")
    print("hashes match for {}".format(path))

    fileText = addTopTodosToText(fileText, todoPaths)
    return interactive, fileText


def main():
    interactive = True
    if len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
        interactive = False
    excludedFiles = general.getConfig()["todosExcludedFromPrioritisation"]
    toDoFiles = general.getAllToDos()
    # testFileText = utils.readFromFile("testFile.md")
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
        interactive, fileText = processTodoPaths(text, path, interactive)
        general.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
