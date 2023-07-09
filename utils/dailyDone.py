import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from datetime import datetime
from utils.utils import *

# from utils.routines import *


def addToDailyDoneFile(paths):
    dailyDoneFile = getConfig()["dailyDoneFilePath"]
    tasks = [
        " < ".join(
            reversed(
                [
                    element.replace("- [x] ", "").replace("- [ ] ", "")
                    for element in path
                ]
            )
        )
        for path in paths
    ]
    curDTObj = datetime.now()
    todaysDate = str(curDTObj.strftime("%d %b, %Y"))
    dailyDoneSoFar = readJson(readFromFile(dailyDoneFile))
    if todaysDate in dailyDoneSoFar:
        dailyDoneSoFar[todaysDate].extend(tasks)
    else:
        dailyDoneSoFar[todaysDate] = tasks
    dailyDoneSoFar[todaysDate] = dedup(dailyDoneSoFar[todaysDate])
    writeToFile(dailyDoneFile, dumpJson(dailyDoneSoFar))


def addToReadableDailyDoneFile(paths):
    readableDailyDoneFile = getConfig()["readableDailyDoneFilePath"]
    readableTasks = [
        path[-1].replace("- [x] ", "").replace("- [ ] ", "") for path in paths
    ]
    curDTObj = datetime.now()
    todaysDate = str(curDTObj.strftime("%d %b, %Y"))
    readableDailyDoneSoFar = readJson(readFromFile(readableDailyDoneFile))
    if todaysDate in readableDailyDoneSoFar:
        readableDailyDoneSoFar[todaysDate].extend(readableTasks)
    else:
        readableDailyDoneSoFar[todaysDate] = readableTasks
    readableDailyDoneSoFar[todaysDate] = dedup(readableDailyDoneSoFar[todaysDate])
    writeToFile(readableDailyDoneFile, dumpJson(readableDailyDoneSoFar))
