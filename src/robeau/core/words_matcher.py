import json
from sklearn.feature_extraction.text import CountVectorizer  # type: ignore
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore


# Function to calculate Levenshtein Distance
def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        s1, s2 = s2, s1

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# Function to get vectors for Cosine Similarity
def get_vectors(strs):
    vectorizer = CountVectorizer().fit_transform(strs)
    vectors = vectorizer.toarray()
    return vectors


# Function to calculate Cosine Similarity
def cosine_sim(s1, s2):
    vectors = get_vectors([s1, s2])
    return cosine_similarity(vectors)[0][1]


# Function to normalize a value between 0 and 1
def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0
    return (value - min_val) / (max_val - min_val)


# Function to find the best match
def find_best_match(input_str, data):
    min_lev_distance = float("inf")
    max_cosine_sim = -1
    best_match = None

    lev_distances = []
    cosine_sims = []
    items_list = []

    for category, items in data.items():
        for item in items:
            text = item["text"]
            lev_distance = levenshtein_distance(input_str, text)
            cos_sim = cosine_sim(input_str, text)

            lev_distances.append(lev_distance)
            cosine_sims.append(cos_sim)
            items_list.append((category, item["text"]))

            if lev_distance < min_lev_distance:
                min_lev_distance = lev_distance
            if cos_sim > max_cosine_sim:
                max_cosine_sim = cos_sim

    for idx, (category, text) in enumerate(items_list):
        normalized_lev = 1 - normalize(
            lev_distances[idx], min(lev_distances), max(lev_distances)
        )
        normalized_cos = normalize(cosine_sims[idx], min(cosine_sims), max(cosine_sims))
        combined_score = normalized_lev + normalized_cos

        if best_match is None or combined_score > best_match["score"]:
            best_match = {
                "category": category,
                "content": text,
                "lev_distance": lev_distances[idx],
                "cosine_similarity": cosine_sims[idx],
                "score": combined_score,
            }

    return best_match


# Load JSON data
with open("C:\\Users\\ville\\MyMegaScript\\src\\robeau\\db_strings.json", "r") as file:
    data = json.load(file)

# Sample input string
input_string = "I'm doing fine"
best_match = find_best_match(input_string, data)

print(best_match)
