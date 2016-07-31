import copy
from random import randrange
import requests
import re
from google.appengine.api import urlfetch
import json
import os

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

# filters
NEGATIVE_WORDS = [
    'death', 'desolation', 'endurance', 'fall', 'endure', 'die', 'cold', 'stormy', 'rough', 'dead', 'roughly', 'command', 'gab',
    'noise', 'anger', 'exhaustion', 'shove', 'desire', 'hustle', 'run', 'shrink', 'dark', 'dusty', 'grimy', 'noisy', 'damn'
]
POSITIVE_WORDS = [
    'courage', 'life', 'love', 'faith', 'lead', 'desire', 'rise', 'warm', 'clear', 'lively', 'calmly', 'quietly',
    'god'
]

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


def get_word_type(word):
    if word in POSITIVE_WORDS:
        return 1
    if word in NEGATIVE_WORDS:
        return -1
    return 0


def word_filter(word_list, fill_positive):
    output = []
    for word in word_list:
        wtype = get_word_type(word)
        if (wtype == 0) or (fill_positive and wtype == 1) or (not fill_positive and wtype == -1):
            output.append(word)
    return output


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


def generate(keywords, emotions, nlines, is_positive=True):
    output = []
    word_lists = copy.deepcopy(word_lists_sea)
    word_lists[1] = keywords
    for i in range(len(word_lists)):
        word_lists[i] = word_filter(word_lists[i], is_positive)

    for i in range(nlines):
        idx = randrange(len(sentence_patterns))
        sentence = generate_sentence(idx, word_lists)
        output.append(sentence)

    return output


def en_to_vi(word):
    # import urllib3
    # http = urllib3.PoolManager()
    # x = http.request('GET', 'https://www.googleapis.com/language/translate/v2?key=AIzaSyAUYzZ4y9NCy6gV0nhtXeSq2R8eLjFr59o&q=hello&source=en&target=vi')

    url = "https://www.googleapis.com/language/translate/v2?key=AIzaSyAUYzZ4y9NCy6gV0nhtXeSq2R8eLjFr59o&q=" + word + "&source=en&target=vi"
    res = urlfetch.fetch(url=url)
    result = json.loads(res.content)
    return result['data']['translations'][0]['translatedText']


def generate_vietnamese(keywords, is_positive=True):
    # translate keywords to Vietnamese
    keywords_vi = []
    for word in keywords:
        keywords_vi.append(en_to_vi(word))
    print(keywords_vi)

    # add emotional words
    if is_positive:
        keywords_vi.append(en_to_vi('happy'))
    else:
        keywords_vi.append(en_to_vi('sad'))

    # get Vietnamese poem
    r = requests.post("http://thomay.vn/index.php?q=tutaochude2",
        data = {'tunhap_chude': ', '.join(keywords_vi)}
    )
    r.encoding = 'utf-8'
    tmp = re.search(r'contain-1 pos-r ketquacuaban.*', r.text, re.M|re.I|re.U|re.DOTALL)
    tmp2 = re.search(r'font color=Blue>.*</font>', tmp.group(), re.M|re.I|re.U|re.DOTALL)
    tmp = tmp2.group().encode('utf-8')
    tmp = tmp[16:-7]
    return tmp.split('<br>')[:-1]