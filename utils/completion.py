#### COMPLETION


## GET COMPLETION INFO
def isTodoSegmentDone(todoSegment):
    return "- [x] " in todoSegment


def isTodoDone(todoPath):
    return isTodoSegmentDone(todoPath[-1])


## MODIFY COMPLETION INFO
def markTodoSegmentAsDone(todoSegment):
    todoSegment = todoSegment.replace("- [ ] ", "- [x] ")
    todoSegment = todoSegment.replace("- [/] ", "- [x] ")
    return todoSegment


def markTodoAsDone(todoPath):
    todoPath[-1] = markTodoSegmentAsDone(todoPath[-1])
    return todoPath


def markTodoSegmentAsUnDone(todoSegment):
    todoSegment = todoSegment.replace("- [x] ", "- [ ] ")
    todoSegment = todoSegment.replace("- [/] ", "- [ ] ")
    return todoSegment


def markTodoAsUnDone(todoPath):
    todoPath[-1] = markTodoSegmentAsUnDone(todoPath[-1])
    return todoPath
