import json
from os import path


def getAbsPath(relPath):
    basepath = path.dirname(__file__)
    return path.abspath(path.join(basepath, relPath))


def getConfig():
    configFileName = getAbsPath("config.json")
    with open(configFileName) as config:
        return json.load(config)


def readJson(text):
    return json.loads(text.strip().strip("`"))


def dumpJson(object):
    return json.dumps(object, indent=4)


def normalisePathElement(row):
    return row.lower().strip().replace("[x]", "[ ]")


def normalisePath(path):
    return normalisePathElement(" / ".join(path))


def normalisePaths(paths):
    return [normalisePath(path) for path in paths]


def checkForUnDoneSubtasks(curPos, currentIndent, totalTextLines):
    noUndoneSubTasks = True
    j = int(curPos) + 1
    while True:
        tmpLine = totalTextLines[j]
        indent = tmpLine.count("\t")
        if indent > currentIndent:
            if "[ ]" in tmpLine:
                noUndoneSubTasks = False
        else:
            break
        j += 1
    return noUndoneSubTasks


def dedup(l):
    result = []
    for i in l:
        if i not in result:
            result.append(i)
    return result
