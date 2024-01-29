import sys
import re
import utils.utils as utils
import utils.toDo as toDo

tasksToAssignPriority = utils.getConfig()["tasksToAssignPriority"]


#################
################# UTILS
#################


#### get priority of todo
def getPriorityOfTodoSegment(todoSegment):
    potentialPriorityString = todoSegment.split("#")[-1].strip()
    if potentialPriorityString == "n":
        return potentialPriorityString
    elif potentialPriorityString.isdigit():
        return int(potentialPriorityString)
    return False


def getPriorityOfTodo(todo_path):
    return getPriorityOfTodoSegment(todo_path[-1])


#### remove priority from todo
def removePriorityFromTodoSegment(todoSegment):
    if getPriorityOfTodoSegment(todoSegment):
        todoSegment = "#".join(todoSegment.split("#")[:-1])
    return todoSegment


def removePriorityFromTodo(todoPath):
    todoPath[-1] = removePriorityFromTodoSegment(todoPath[-1])
    return todoPath


#### replace priority of todo
def replacePriorityOfTodoSegment(todoSegment, newPriority):
    if getPriorityOfTodoSegment(todoSegment):
        todoSegment = "#".join(todoSegment.split("#")[:-1]) + " #" + str(newPriority)
    else:
        todoSegment = todoSegment + " #" + str(newPriority)
    todoSegment = todoSegment.replace("  ", " ")
    return todoSegment


def replacePriorityOfTodo(todoPath, newPriority):
    todoPath[-1] = replacePriorityOfTodoSegment(todoPath[-1], newPriority)
    return todoPath


#### mark todo as done
def markTodoSegmentAsDone(todoSegment):
    todoSegment = todoSegment.replace("- [ ] ", "- [x] ")
    todoSegment = todoSegment.replace("- [/] ", "- [x] ")
    return todoSegment


def markTodoAsDone(todoPath):
    todoPath[-1] = markTodoSegmentAsDone(todoPath[-1])
    return todoPath


#### ask for priority of todo
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


def getTopNTodosAsText(todoPaths, n):
    textOutput = []
    textOutput.append(f"Top {n} todos:")
    allTodos = [
        (getPriorityOfTodo(path), path)
        for path in todoPaths
        if getPriorityOfTodo(path) and getPriorityOfTodo(path) != "n"
    ]
    if len(allTodos) == 0:
        textOutput.append("no prioritised todos to display")
        return "\n".join(textOutput)
    sortedTodos = sorted(allTodos, key=lambda x: x[0])
    n = min(n + 1, len(sortedTodos))
    for i in range(n):
        priority, path = sortedTodos[i]
        todoName = (
            path[-1].replace("- [x] ", "").replace("- [/] ", "").replace("- [ ] ", "")
        )
        textOutput.append(f"{priority}) {todoName}")

    textOutput = "\n".join(textOutput)
    return textOutput


def printTopNTodos(todoPaths, n):
    print(f"\n\n\n\n\n\n\n\n\n\n")
    print(getTopNTodosAsText(todoPaths, n))


#### misc
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


def substitePriority(prioritySubstitutions, todoPaths):
    for i, task in enumerate(todoPaths):
        taskPriority = getPriorityOfTodo(task)
        if taskPriority in prioritySubstitutions:
            todoPaths[i] = replacePriorityOfTodo(
                task, prioritySubstitutions[taskPriority]
            )
    return todoPaths


def updatePathPriorities(todoPaths, indexOfPath, priority):
    print("running updatePathPriorities")
    print(priority)
    if priority == "d":
        todoMarkedAsDone = markTodoAsDone(todoPaths[indexOfPath])
        print("marked todo as done: ", todoMarkedAsDone)
        todoPaths[indexOfPath] = todoMarkedAsDone
    else:
        if priority != "n":
            prioritySubstitutions = dict(
                [(j, j + 1) for j in range(priority, tasksToAssignPriority)]
            )
            prioritySubstitutions[tasksToAssignPriority] = "n"
            todoPaths = substitePriority(prioritySubstitutions, todoPaths)
        todoPaths[indexOfPath] = replacePriorityOfTodo(todoPaths[indexOfPath], priority)

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


#################
################# END UTILS
#################


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
    prioritisedPaths = list(todoPaths)
    for i, path in enumerate(todoPaths):
        shouldBePrioritised = shouldTodoBePrioritised(todoPaths, i, True)[0]
        if shouldBePrioritised:
            try:
                remaining = noOfTodosToPrioritise - prioritisedSoFar - 1
                if not receivedCtrlC:
                    while True:
                        printTopNTodos(prioritisedPaths, tasksToAssignPriority)
                        priority = askForPriority(path, todoFileName, remaining)
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
                            prioritisedPaths = swapPriorities(
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
            hasPriority = getPriorityOfTodoSegment(element)
            if hasPriority and not isLastElement:
                parentSegmentPriority = hasPriority
                element = removePriorityFromTodoSegment(element)
            if isLastElement and parentSegmentPriority and not hasPriority:
                element = replacePriorityOfTodoSegment(element, parentSegmentPriority)
            reconstructedPath.append(element)
        outputPaths.append(reconstructedPath)

    return outputPaths


def regularisePriorities(todoPaths):
    regularisedTodos = []
    for path in todoPaths:
        priority = getPriorityOfTodo(path)
        if not priority or priority == "n":
            regularisedTodos.append(path)
            continue
        elif type(priority) is int:
            if priority > tasksToAssignPriority or priority < 1:
                regularisedTodos.append(removePriorityFromTodo(path))
            else:
                regularisedTodos.append(path)
        else:
            print("weird priority: {}".format(priority))
            regularisedTodos.append(removePriorityFromTodo(path))
    return regularisedTodos


def deduplicatePriorities(todoPaths):
    prioritiesUsedSoFar = []
    deDupedTodos = []
    for path in todoPaths:
        priority = getPriorityOfTodo(path)
        if priority == "n":
            deDupedTodos.append(path)
        elif priority in prioritiesUsedSoFar:
            path = removePriorityFromTodo(path)
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
        if getPriorityOfTodo(todo) not in [False, "n"]
    ]

    # Step 2: Sort the indexed todos by their priorities
    indexed_prioritized_todos.sort(key=lambda x: getPriorityOfTodo(x[1]))

    # Step 3: Reassign priorities starting from 1
    new_priority = 1
    for index, todo in indexed_prioritized_todos:
        todos[index] = replacePriorityOfTodo(todo, new_priority)
        new_priority += 1

    return todos


def triggerReprioritisationIfNecessary(todoPaths):
    outputTodoPaths = []
    try:
        highestPriorityTask = max(
            getPriorityOfTodo(todoPath)
            for todoPath in todoPaths
            if getPriorityOfTodo(todoPath) and getPriorityOfTodo(todoPath) != "n"
        )
    except ValueError:
        highestPriorityTask = 0

    if highestPriorityTask <= tasksToAssignPriority / 3:
        print("triggering a reprioritisation")
        outputTodoPaths = [
            removePriorityFromTodo(todoPath)
            if getPriorityOfTodo(todoPath) == "n"
            else todoPath
            for todoPath in todoPaths
        ]
    else:
        outputTodoPaths = todoPaths

    return outputTodoPaths


def saveErrorData(newText, oldText):
    with open(utils.getAbsPath("errorNewText.txt"), "w") as f:
        f.write(newText)
    with open(utils.getAbsPath("errorOldText.txt"), "w") as f:
        f.write(oldText)


def addTopTodosToText(text, todoPaths):
    topNTodos = getTopNTodosAsText(todoPaths, tasksToAssignPriority)
    text = "+++++\n" + topNTodos + "\n+++++\n\n" + text
    return text


def processTodoPaths(text, path, interactive):
    todoPathsOrig = toDo.getAllToDoPaths(text)
    todoPaths = regularisePriorities(todoPathsOrig)
    todoPaths = deduplicatePriorities(todoPaths)
    todoPaths = removeGapsInPriorities(todoPaths)
    todoPaths = assignPriorityOfParentsToChildren(todoPaths)
    todoPaths = triggerReprioritisationIfNecessary(todoPaths)

    if interactive:
        fileName = path.split("/")[-1]
        todoPaths, receivedCtrlC = prioritiseUnprioritisedTodos(todoPaths, fileName)
        if receivedCtrlC:
            interactive = False
            print("disabling interactive mode for all following files..")

    fileText = toDo.constructFileFromPaths(todoPaths)
    inputHash = generateTodoListHash(todoPathsOrig)
    outputHash = generateTodoListHash(todoPaths)
    if inputHash != outputHash:
        print("input hash: {}, output hash: {}".format(inputHash, outputHash))
        saveErrorData(fileText, text)
        raise Exception("hashes do not match!!!!")
    print("hashes match for {}".format(path))

    fileText = addTopTodosToText(fileText, todoPaths)
    return interactive, fileText


def removeTopTodosFromText(text):
    pattern = r"^\+{5}\n(.|\n)*?\+{5}$"
    text = re.sub(pattern, "", text, flags=re.MULTILINE)
    return text


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
        text = removeTopTodosFromText(text).lstrip("\n")

        if path in excludedFiles:
            continue
        interactive, fileText = processTodoPaths(text, path, interactive)
        utils.writeToFile(path, fileText)


if __name__ == "__main__":
    main()
