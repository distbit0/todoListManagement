import random


def select_pair(items, comparison_counts, compared_pairs):
    items = list(items.items())
    while True:
        probabilities = []
        for item1, score1 in items:
            for item2, score2 in items:
                if (item1, item2) in compared_pairs or (
                    item2,
                    item1,
                ) in compared_pairs:
                    repetitionPenalty = 0
                else:
                    repetitionPenalty = 1
                equalityPenalty = 0 if item1 == item2 else 1
                absScoreDelta = max(abs(score1 - score2), 0.01)
                scoreProduct = score1 * score2
                comparisonCountProduct = (
                    comparison_counts[item1] * comparison_counts[item2]
                )
                probability = (
                    scoreProduct**2
                    * equalityPenalty
                    * repetitionPenalty
                    / (comparisonCountProduct * absScoreDelta)
                )
                probabilities.append(probability)

        if probabilities and sum(
            probabilitiesupdate_scores_and_counts
        ):  # Check if there is any pair left to compare
            chosen_pair = random.choices(
                [
                    (items[i][0], items[j][0])
                    for i in range(len(items))
                    for j in range(len(items))
                ],
                weights=probabilities,
                k=1,
            )[0]
            return chosen_pair
        else:
            return None  # No more pairs left to compare


def update_scores_and_counts(items, comparison_counts, winner, loser, learningRate):
    items[winner] += learningRate * items[loser] / comparison_counts[winner] ** 3
    comparison_counts[winner] *= 1.1
    comparison_counts[loser] *= 1.1


def borda_count_sort(initial_items, comparisonsToMake, learningRate):
    items = initial_items.copy()
    comparison_counts = {
        item: 1 if score else 1 / len(items) for item, score in items.items()
    }

    average_score = sum([item for item in items.values() if item]) / len(items)
    for item in items:
        if items[item] is False or items[item] is None:
            items[item] = average_score

    compared_pairs = set()
    comparisonsMade = 0
    while True:
        pair = select_pair(items, comparison_counts, compared_pairs)
        if not pair:  # If there are no more pairs to compare
            break
        item1, item2 = pair
        user_input = getUserInput(pair, comparisonsMade, comparisonsToMake)
        if user_input == "stop":
            break
        elif user_input == "1":
            update_scores_and_counts(
                items, comparison_counts, item1, item2, learningRate
            )
            compared_pairs.add(pair)
        elif user_input == "2":
            update_scores_and_counts(
                items, comparison_counts, item2, item1, learningRate
            )
            compared_pairs.add(pair)
        comparisonsMade += 1

    return sorted(items.items(), key=lambda x: x[1])


def getUserInput(pair, comparisonsMade, comparisonsToMake):
    item1, item2 = pair
    # print(f"Compare: {item1} vs {item2}")

    if comparisonsMade >= comparisonsToMake:
        user_input = "stop"
    else:
        if item1 > item2:
            user_input = "1"
        elif item1 < item2:
            user_input = "2"
    return user_input


def average_difference(arr):
    return sum(abs(x - (i + 1)) for i, x in enumerate(arr)) / len(arr) ** 2


items = [(number, 1) for number in range(1, 10)]
random.shuffle(items)
initial_items = dict(items)


samples = 50
comparisons = 20
learningRate = 0.4
for j in range(10):
    lr = learningRate  # * (j + 1) / 10
    comps = comparisons * (j + 1) / 10
    sumAvError = 0
    for i in range(samples):
        sorted_items = [item[0] for item in borda_count_sort(initial_items, comps, lr)]
        averageError = average_difference(sorted_items)
        sumAvError += averageError
    output = sumAvError / samples
    print(f"{int(output * 100)}% error for {lr} lr and {comps} comparisons")
