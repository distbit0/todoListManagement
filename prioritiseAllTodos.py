import sys
from prompt_toolkit import prompt
import os
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


def prioritiseUnprioritisedTodos(todoPaths, todoFileName, maxTodosToPrioritise):
    prioritisedPaths = []
    noOfTodosToPrioritise = priorityLib.getNoOfTodosToPrioritise(todoPaths)
    noOfTodosToPrioritise = min(noOfTodosToPrioritise, maxTodosToPrioritise)
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
                        priorityLib.printTopNTodos(
                            prioritisedPaths, tasksToAssignPriority
                        )
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
                            goBack = True
                            break
                        elif type(priority) == list:
                            prioritisedPaths = priorityLib.swapPriorities(
                                prioritisedPaths, priority[0], priority[1]
                            )
                            prioritisedPaths = removeGapsInPriorities(prioritisedPaths)
                        elif str(priority)[0] == "[" and str(priority)[-1] == "]":
                            prioritisedPaths = createNoteFromTodo(
                                prioritisedPaths, path, priority
                            )
                        elif priority == "edit":
                            prioritisedPaths = renameTodo(prioritisedPaths, path)
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
        isATodo = priorityLib.shouldTodoBePrioritised(todoPaths, i, False)[0]
        if isATodo:
            prioritisedPaths = createNoteFromTodo(
                prioritisedPaths, path, "", autoCreate=True
            )
        i += 1
    return prioritisedPaths, receivedCtrlC


def renameTodo(prioritisedPaths, path):
    todoName = general.getTodoSegmentName(path[-1])
    newName = prompt(f"\n\n\nRename to: ", default=todoName)
    if newName == "":
        return prioritisedPaths
    indexOfPath = prioritisedPaths.index(path)
    path[-1] = path[-1].replace(todoName, newName)
    prioritisedPaths[indexOfPath] = path
    return prioritisedPaths


def createNoteFromTodo(todoPaths, path, priority, autoCreate=False):
    config = general.getConfig()
    oldTodoName = general.getTodoSegmentName(path[-1])
    if "[[" in priority and "]]" in priority:
        newFileName = priority.strip("[]")
    elif len(oldTodoName) < 45 and autoCreate:
        newFileName = oldTodoName
    else:
        return todoPaths

    newFileName = "".join(
        [char for char in newFileName if char.isalnum() or char == " "]
    )
    newFileName += ".md"
    newNotePath = os.path.join(
        config["toDoFolderPath"],
        config["newNotesSubDir"],
        newFileName,
    )
    if "[[" in oldTodoName and "]]" in oldTodoName:
        # print("todo already contains wikilink, not creating new note: ", oldTodoName)
        return todoPaths
    if not os.path.exists(newNotePath):
        with open(newNotePath, "w") as f:
            f.write(oldTodoName)
        print("created new note: {}".format(newNotePath))
    indexOfPath = todoPaths.index(path)
    linkToNewNote = f"[[{newFileName.replace('.md', '')}]]"
    path[-1] = path[-1].replace(oldTodoName, linkToNewNote)
    todoPaths[indexOfPath] = path
    return todoPaths


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


def processTodoPaths(todoPathsOrig, filePath, interactive, maxTodosToPrioritise):
    print("processing: {}".format(filePath))
    todoPaths = list(todoPathsOrig)
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
            todoPaths, todoPathsOrig, filePath, functionToExecute.__name__ + str(i)
        )

    if interactive:
        fileName = filePath.split("/")[-1]
        todoPaths = regularisePriorities(todoPaths, setToN=True)
        checkThatHashesMatch(
            todoPaths, todoPathsOrig, filePath, "regularisePriorities (setToN)"
        )
        todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(
            todoPaths, fileName, maxTodosToPrioritise
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

    excludedFiles = general.getConfig()["todosExcludedFromPrioritisation"]
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
        maxTodosToPrioritise = general.getConfig()["maxTodosToPrioritise"]
        maxTodosToPrioritise *= (i + 1) / len(toDoFiles)
        maxTodosToPrioritise -= processedTodos
        maxTodosToPrioritise = int(maxTodosToPrioritise)
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]
        text = priorityLib.removeTopTodosFromText(text).lstrip("\n")

        if path in excludedFiles:
            continue
        prevInteractiveState = bool(interactive)
        todoPathsOrig = parseLists.getAllToDoPaths(text)
        processedTodos += min(
            priorityLib.getNoOfTodosToPrioritise(todoPathsOrig), maxTodosToPrioritise
        )
        interactive, fileText = processTodoPaths(
            todoPathsOrig,
            path,
            interactive or str(onlyInteractiveTodo).lower() in path.lower(),
            maxTodosToPrioritise,
        )
        interactive = prevInteractiveState and interactive
        general.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
