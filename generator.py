import copy
from random import randrange

# 1 = "Concrete Nouns"
# 2 = "Abstract Nouns"
# 3 = "Transitive Verbs"
# 4 = "Intransitive Verbs"
# 5 = "Adjectives"
# 6 = "Adverbs"
# 7 = ""
# 8 = ""
# 9 = "Interjections"

# sea
word_lists_sea = [[] for i in range(10)]
word_lists_sea[1] = ["sea", "ship", "sail", "wind", "breeze", "wave", "cloud", "mast", "captain", "sailor", "shark", "whale", "tuna", "seashell", "pirate", "lad", "girl", "gull", "reef", "shore", "mainland", "moon", "sun"]
word_lists_sea[2] = ["adventure", "courage", "endurance", "desolation", "death", "life", "love", "faith"]
word_lists_sea[3] = ["command", "view", "lead", "pull", "love", "desire", "fight"]
word_lists_sea[4] = ["travel", "sail", "wave", "grow", "rise", "fall", "endure", "die"]
word_lists_sea[5] = ["big", "small", "old", "cold", "warm", "sunny", "rainy", "misty", "clear", "stormy", "rough", "lively", "dead"]
word_lists_sea[6] = ["swiftly", "calmly", "quietly", "roughly"]
word_lists_sea[7] = [""]
word_lists_sea[8] = [""]
word_lists_sea[9] = ["o", "oh", "ooh", "ah", "lord", "god", "wow", "golly gosh"]

# city
word_lists_city = [[] for i in range(10)]
word_lists_city[1] = ["street", "sidewalk", "corner", "door", "window", "hood", "slum", "skyscraper", "car", "truck", "guy", "girl", "job", "flower", "light", "cigarette", "rain", "jackhammer", "driver", "worker"]
word_lists_city[2] = ["action", "work", "noise", "desolation", "death", "life", "love", "faith", "anger", "exhaustion"]
word_lists_city[3] = ["get", "grab", "shove", "love", "desire", "buy", "sell", "fight", "hustle", "drive"]
word_lists_city[4] = ["talk", "gab", "walk", "run", "stop", "eat", "grow", "shrink", "shop", "work"]
word_lists_city[5] = ["big", "small", "old", "fast", "cold", "hot", "dark", "dusty", "grimy", "dry", "rainy", "misty", "noisy", "faceless", "dead"]
word_lists_city[6] = ["quickly", "loudly", "calmly", "quietly", "roughly"]
word_lists_city[7] = [""]
word_lists_city[8] = [""]
word_lists_city[9] = ["o", "oh", "ooh", "ah", "lord", "god", "damn"]

# tokens
TO_BE_REPLACED = ['1', '2', '3', '4', '5', '6', '7', '8', '9']


# sentence patterns
sentence_patterns = [
    "The 5 1 6 3s the 1.",
    "5, 5 1s 6 3 a 5, 5 1.",
    "2 is a 5 1.",
    "9, 2!",
    "1s 4!",
    "The 1 4s like a 5 1.",
    "1s 4 like 5 1s.",
    "Why does the 1 4?",
    "4 6 like a 5 1.",
    "2, 2, and 2.",
    "Where is the 5 1?",
    "All 1s 3 5, 5 1s.",
    "Never 3 a 1.",
]


def generate_word(idx, word_lists):
    i = randrange(len(word_lists[idx]))
    return word_lists[idx][i]


def generate_sentence(idx, word_lists):
    pattern = sentence_patterns[idx]
    output = []
    for i in range(len(pattern)):
        x = pattern[i]
        if x in TO_BE_REPLACED:
            x = generate_word(ord(x)-ord('0'), word_lists)
        output.append(x)
    return ''.join(output)


def generate(keywords, emotions, nlines):
    output = []
    word_lists = copy.deepcopy(word_lists_sea)
    word_lists[1] = keywords

    for i in range(nlines):
        idx = randrange(len(sentence_patterns))
        sentence = generate_sentence(idx, word_lists)
        output.append(sentence)

    return output
