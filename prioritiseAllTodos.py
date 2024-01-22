import utils.utils as utils
import random
import utils.toDo as toDo


def getPriorityOfToDo(todoPath):
    potentialPriority = todoPath[-1].split("#")[-1].strip(" ")
    if potentialPriority.isdigit() and len(potentialPriority) < 3:
        return int(potentialPriority)
    else:
        return False


def askForPriority(todoPath):
    priority = input("Prioritise (0 - 99): \n" + " ".join(todoPath) + ": ")
    if priority.isdigit() and len(priority) < 3:
        todoPath = replacePriorityOfTodo(todoPath, priority)
        return todoPath
    else:
        return askForPriority(todoPath)


def replacePriorityOfTodo(todoPath, newPriority):
    if getPriorityOfToDo(todoPath):
        todoPath[-1] = "#".join(todoPath[-1].split("#")[:-1]) + " #" + str(newPriority)
    else:
        todoPath[-1] = todoPath[-1] + " #" + str(newPriority)
    todoPath[-1] = todoPath[-1].replace("  ", " ")
    return todoPath


def prioritiseUnprioritisedTodos(todoPaths):
    prioritisedPaths = []
    for i, path in enumerate(todoPaths):
        isLastTodoInList = len(todoPaths) - 1 == i
        if isLastTodoInList:
            todoHasNoChildren = True
        else:
            todoHasNoChildren = len(todoPaths[i + 1]) <= len(todoPaths[i])

        if todoHasNoChildren:
            todoPriority = getPriorityOfToDo(path)
            if not todoPriority:
                path = askForPriority(path)
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
    toDoFiles = utils.getAllToDos()
    for file in toDoFiles:
        if "conflict" in toDoFiles[file]:
            continue
        fileObj = toDoFiles[file]["master"]
        text, path = fileObj["text"], fileObj["path"]
        todoPaths = toDo.getAllToDoPaths(text)
        todoPaths = prioritiseUnprioritisedTodos(todoPaths)
        todoPaths = normalisePriorities(todoPaths)
        print("\n\n\n\n\n\n", toDo.constructFileFromPaths(todoPaths))


if __name__ == "__main__":
    main()
