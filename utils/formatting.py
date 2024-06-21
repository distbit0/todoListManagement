## in order to sort todos with deps to end of sublist, move them down to just above the next todo which is less indented than them, and only if the todo below it doest also have a dep (because this would indicate that it has already been moved down previously)


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
