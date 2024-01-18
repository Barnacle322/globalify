weights = {"bias": 0.3, "industry": 0.35, "round": 0.15, "location": 0.1, "exits": 0.1}

pass_score = 0.6


def check_weights(weights):
    total_weight = sum(weights.values())
    try:
        if total_weight != 1.0:
            raise ValueError("The weights must sum to 1.0")
    except ValueError as e:
        print(e)


check_weights(weights)
