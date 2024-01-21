import utils

toDoFiles = utils.getAllToDosAndDoneText()[0]


for file in toDoFiles:
    if not "conflict" in toDoFiles[file]:
        fileObj = toDoFiles[file]["master"]
        text, path, subject = fileObj["text"], fileObj["path"], fileObj["subject"]
