import re


def extractToDoText(todoSegment):
    # Check if the text contains any of the specified patterns
    if (
        "[[" in todoSegment
        or "]]" in todoSegment
        or "](" in todoSegment
        or "!(" in todoSegment
        or "://" in todoSegment
    ):
        return None

    todoSegment = (
        todoSegment.replace("- [ ] ", "").replace("- [x] ", "").replace("- [/] ", "")
    ).strip()

    # Check if the text starts with "dep " (case-insensitive) and contains a colon
    if todoSegment.lower().startswith("dep ") and ":" in todoSegment:
        todoSegment = todoSegment.split(":", 1)[1].strip()

    # Define the regex patterns
    patterns = [r"\s*#(\d+|[a-zA-Z])", r"@(\d+)", r"\^(\d{1,2}/\d{1,2})"]

    # Find the earliest occurrence of any of the patterns
    earliest_match_index = float("inf")
    for pattern in patterns:
        match = re.search(pattern, todoSegment)
        if match and match.start() < earliest_match_index:
            earliest_match_index = match.start()

    # If any patterns are found, cut the text from the earliest occurrence
    if earliest_match_index != float("inf"):
        return todoSegment[:earliest_match_index].strip()

    # If no patterns are found, return the entire text
    return todoSegment.strip()


def formatTodoSegmentDepencency(todoSegment):
    if "] dep " in todoSegment.lower() and ":" in todoSegment:
        todoSegment = todoSegment.replace("] dep ", "] (DEP) ")
        todoSegment = todoSegment.replace("] DEP ", "] (DEP) ")

    return todoSegment


def formatTodoSegment(todoSegment, hasChild):
    hasCheckbox = (
        "- [x]" in todoSegment or "- [/]" in todoSegment or "- [ ]" in todoSegment
    )
    if not hasCheckbox or hasChild:
        return todoSegment
    # only do this once I can prevent files created by foam from replacing spaces with dashes
    # todoText = extractToDoText(todoSegment)
    # if todoText != None and len(todoText) > 0 and len(todoText) < 55:
    # todoSegment = todoSegment.replace(todoText, f"[[{todoText}]]")
    todoSegment = formatTodoSegmentDepencency(todoSegment)
    return todoSegment


def formatTodo(todoPath, hasChild):
    todoPath[-1] = formatTodoSegment(todoPath[-1], hasChild)
    return todoPath
