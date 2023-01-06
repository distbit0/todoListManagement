import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from datetime import datetime
from utils.utils import *
from utils.routines import *


def addToDailyDoneFile(paths):
    dailyDoneFile = getConfig()["dailyDoneFile"]
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
    dailyDoneSoFar = readJson(open(dailyDoneFile).read())
    if todaysDate in dailyDoneSoFar:
        dailyDoneSoFar[todaysDate].extend(tasks)
    else:
        dailyDoneSoFar[todaysDate] = tasks
    dailyDoneSoFar[todaysDate] = dedup(dailyDoneSoFar[todaysDate])
    dailyDoneSoFar[todaysDate] = sortRoutinesToTop(dailyDoneSoFar[todaysDate])
    with open(dailyDoneFile, "w") as dailyDoneF:
        dailyDoneF.write(dumpJson(dailyDoneSoFar))


def addToReadableDailyDoneFile(paths):
    readableDailyDoneFile = getConfig()["readableDailyDoneFile"]
    readableTasks = [
        path[-1].replace("- [x] ", "").replace("- [ ] ", "") for path in paths
    ]
    curDTObj = datetime.now()
    todaysDate = str(curDTObj.strftime("%d %b, %Y"))
    readableDailyDoneSoFar = readJson(open(readableDailyDoneFile).read())
    if todaysDate in readableDailyDoneSoFar:
        readableDailyDoneSoFar[todaysDate].extend(readableTasks)
    else:
        readableDailyDoneSoFar[todaysDate] = readableTasks
    readableDailyDoneSoFar[todaysDate] = dedup(readableDailyDoneSoFar[todaysDate])
    readableDailyDoneSoFar[todaysDate] = sortRoutinesToTop(
        readableDailyDoneSoFar[todaysDate]
    )
    with open(readableDailyDoneFile, "w") as readableDailyDoneF:
        readableDailyDoneF.write(dumpJson(readableDailyDoneSoFar))
