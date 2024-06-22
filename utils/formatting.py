## in order to sort todos with deps to end of sublist, move them down to just above the next todo which is less indented than them, and only if the todo below it doest also have a dep (because this would indicate that it has already been moved down previously)
import re
import os
import utils.general as general
from prompt_toolkit import prompt


def formatTodoSegmentDepencency(todoSegment):
    if "] dep " in todoSegment.lower() and ":" in todoSegment:
        todoSegment = todoSegment.replace("] dep ", "] (DEP) ")
        todoSegment = todoSegment.replace("] DEP ", "] (DEP) ")

    return todoSegment


### objective: avoid formatting lines that contain non-outliner text
def formatTodoSegment(todoSegment, hasChild):
    hasCheckbox = (
        "- [x]" in todoSegment or "- [/]" in todoSegment or "- [ ]" in todoSegment
    )
    if not hasCheckbox or hasChild:
        return todoSegment
    todoSegment = formatTodoSegmentDepencency(todoSegment)
    return todoSegment


def formatTodo(todoPath, hasChild):
    todoPath[-1] = formatTodoSegment(todoPath[-1], hasChild)
    return todoPath


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
    if priority and priority[0] == "[" and priority[-1] == "]":
        newFileName = priority.strip("[]")
    elif len(oldTodoName) < 50 and autoCreate:
        newFileName = oldTodoName
    else:
        return todoPaths

    newFileName = "".join(
        [char for char in newFileName if char.isalnum() or char == " "]
    ).lower()
    newFileName += ".md"
    newNotePath = os.path.join(
        config["toDoFolderPath"],
        config["newNotesSubDir"],
        newFileName,
    )
    linkIndicators = ["[[", "]]", "http", "]("]
    todoAlreadyContainsLink = any(
        [linkIndicator in oldTodoName for linkIndicator in linkIndicators]
    )
    if todoAlreadyContainsLink and autoCreate:
        return todoPaths

    if not os.path.exists(newNotePath):
        with open(newNotePath, "w") as f:
            if autoCreate:
                f.write("#task\n#### " + oldTodoName + "\n")
            else:
                f.write("#task\n" + oldTodoName + "\n")
        print("created new note: {}".format(newNotePath))
    indexOfPath = todoPaths.index(path)
    linkToNewNote = f"[[{newFileName.replace('.md', '')}]]"
    path[-1] = path[-1].replace(oldTodoName, linkToNewNote)
    todoPaths[indexOfPath] = path
    return todoPaths
