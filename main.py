"""The Dog Ate My Homework: Funniest Excuse — make.fun entry (v1).

Program writes ONE original excuse a dog gives after being caught eating
the homework — a single line of at most 200 characters — to
/output/entry.txt ($MAKEFUN_OUTPUT_DIR/entry.txt when set).

Judge (z-ai/glm-5.3-flash, pairwise, margin 1-5, both orders), criteria in
order (RULES.txt):
  1. An excuse a dog gives after being caught eating the homework, in the
     dog's own voice; an entry about anything else loses to any excuse
     from a dog caught eating the homework.
  2. Earns the bigger laugh, with a twist or a piece of dog logic that
     lands in a single line.
  3. Sounds like a real dog, with a dog's priorities and none of a
     person's embarrassment.
  4. Works on its own, with no setup and nothing that needs a second line
     to make sense.
  5. Feels fresh, not one of the stock lines about the cat, the taste of
     paper or being a good boy.
The best excuse sounds like a dog who believes it has done nothing wrong.
Length for its own sake does not count; an exact tie on win rate goes to
the smaller text, so shorter wins ties.

Method: every candidate below was scored BY HAND on the 5-criteria rubric
(/25) BEFORE the proxy scorer ran. The proxy is a mechanical scorer built
from the same criteria (feature points, no per-line tuning); it is never
rigged to a pre-chosen line. Pick = highest (proxy, rubric); ties go to
the earliest label, then the shorter text (the competition tie-break
favours smaller text after playoff games).

v1 candidates A-Z: first-pass angles. Controls: Y = mild observation with
no punch, Z = generic stock line (cat + taste of paper + good boy —
freshness must fail it).
"""

import os
import re

VERSION = "v4"

# v4 calibration fix (from v3 proxy-vs-rubric gaps, documented):
# - c5 fresh-detail test now matches whole words: substring matching let
#   "home" fire inside "homework", so the mild control Y (no fresh
#   detail at all) scored c5 5.0 instead of 3.0. With whole-word
#   matching Y falls to 18.0, exactly 6.0 below the pick.
# - 4 new challengers AQ-AT in the winning families (floor rule /
#   translation / self-defence), rubrics scored BEFORE the v4 proxy ran.

# v2 calibration fixes (from v1 proxy-vs-rubric gaps, documented):
# - c1 no longer demands the literal word "homework": the brief frames
#   every entry as the dog's excuse, so "it" refers to the homework.
#   c1 = 5 for first-person dog voice, 4 for homework named without it.
# - c2 rebalanced to small weights (contrast 1.0, not 1.5) so the cap
#   stops hiding penalties; += 0.5 for a twist word (TWIST); -1.0 when
#   a line carries no laugh device at all (no contrast/quote/number/
#   parallel/triple) — the mild control Y had c2 1.5 with no device.
# - c4 starts at 4.5 and only earns 5.0 with a punch at the end.
# - c5 now reads FRESH_DETAIL (specific detail words, "homework" itself
#   excluded: it is the topic, not a detail) and -2 for a stock
#   "tasted like" taste trope (P's chicken line is the same family as
#   the paper-taste stock line); -2 when no fresh detail and no number.
# - 9 new challengers AA-AI in the winning families, rubrics scored
#   BEFORE the v2 proxy ran.
# v3 calibration fixes (from v2 proxy-vs-rubric gaps, documented):
# - No double credit: a twist word (TWIST) no longer also fires as an
#   end punch — PUNCH_END -= "respect", "teamwork", "obviously",
#   "literally" (R's "obviously" was +0.5 twice). PUNCH_END +=
#   "my homework." (the payoff phrase of the home+work family).
# - Pick sort is now (-proxy, -rubric, shorter, label): the competition
#   tie-break favours the smaller text, so length outranks label order.
# - 5 new challengers AJ-AN in the winning families + 2 v4 challengers
#   AO-AP, rubrics scored BEFORE the v3 proxy ran. AO splits AJ's punch
#   into a one-word tag sentence, "Technically." — no filler "so".

# ---------------------------------------------------------------- candidates
CANDIDATES = {
    "A": "Homework is home plus work, and I live here and eating is my work \u2014 so technically I did it.",
    "B": "You said finish your homework, so I finished it \u2014 all of it, in one sitting, with no leftovers.",
    "C": "The homework smelled like bacon, so I followed the smell, and the smell led to your maths.",
    "D": "It started it \u2014 it sat there looking delicious, and I am a dog, and that is how this ends.",
    "E": "I filed it under snacks \u2014 everything on the floor is a snack, and your homework was on the floor.",
    "F": "I was saving you \u2014 homework is the enemy, and I took the hit so you never have to do it again.",
    "G": "I graded it first: delicious, A-plus, would eat again \u2014 the teacher just won't see it that way.",
    "H": "You left it on the floor, and floor food is dog food \u2014 that is the rule, and I don't make the rules.",
    "I": "I thought homework meant work you do at home, and my work is eating, so I did my homework.",
    "J": "It was the only homework that didn't run away when I chased it \u2014 the rest of school is too fast.",
    "K": "I ate it so the dog next door couldn't copy your answers \u2014 you're welcome, I take belly rubs.",
    "L": "My stomach did chapter four \u2014 I digested the whole assignment and I still don't get fractions.",
    "M": "The homework was the only thing in the house that didn't run away or say no.",
    "N": "I didn't eat it, I translated it \u2014 it was English, now it's bark, and bark is my first language.",
    "O": "It was due tomorrow, so I gave it an early deadline \u2014 dogs do deadlines differently, ask anyone.",
    "P": "It tasted like chicken \u2014 I checked twice, and both times it was chicken, so I finished the job.",
    "Q": "I was practising my spelling \u2014 I ate every word, and now I know them all by heart. Literally.",
    "R": "The homework attacked my teeth first \u2014 I was defending myself, and my teeth won, obviously.",
    "S": "You wrote 'eat' in every maths problem, so I ate the maths \u2014 I was following instructions.",
    "T": "It's not gone, it's just homework in dog form now \u2014 same answers, better smell, zero pages.",
    "U": "I ate it because it was homework and I am a dog \u2014 this is not complicated, this is Tuesday.",
    "V": "The teacher said the dog ate my homework is the oldest excuse \u2014 so I made it true out of respect.",
    "W": "I was helping \u2014 you hate homework, I hate homework, so I removed the homework. Teamwork.",
    "X": "It looked at me first \u2014 paper doesn't get to look at a dog like that and expect to survive.",
    "Y": "I ate the homework because I was hungry and it was there on the table.",
    "Z": "The cat told me to eat it, it tasted like paper, but I'm a good boy really.",
    # v2 challengers AA-AI (rubrics scored BEFORE the v2 proxy ran).
    "AA": "Homework means work you do at home \u2014 my work is eating, so I did my homework.",
    "AB": "Home plus work is homework, and I live here \u2014 eating is my work, so I did it.",
    "AC": "They say the dog ate my homework is the oldest excuse \u2014 so I made it true. Respect.",
    "AD": "Floor food is dog food, and your homework was on the floor \u2014 I was following the rules.",
    "AE": "I graded it before I ate it: delicious, A-plus \u2014 the teacher just can't read my work.",
    "AF": "My stomach finished chapter four \u2014 I still don't get fractions, but I ate the evidence.",
    "AG": "You said finish it \u2014 I finished it in one sitting, no leftovers, no witnesses.",
    "AH": "I ate it so nobody could copy your answers \u2014 you're welcome, payment in belly rubs.",
    "AI": "It looked at me first \u2014 paper doesn't look at a dog like that and live to tell the tale.",
    # v3 challengers AJ-AN (rubrics scored BEFORE the v3 proxy ran).
    "AJ": "Homework means work you do at home \u2014 eating is my work, so technically I did it.",
    "AK": "Floor food is dog food \u2014 your homework was on the floor, so I followed the rules.",
    "AL": "I thought homework was work you do at home \u2014 my work is eating, so I did my homework.",
    "AM": "The dog ate my homework is the oldest excuse \u2014 so I made it true, out of respect.",
    "AN": "You said finish it \u2014 I finished it in one sitting, no leftovers, no witnesses, no regrets.",
    # v4 challengers AO-AP (rubrics scored BEFORE the v3 proxy ran).
    "AO": "Homework means work you do at home \u2014 eating is my work, and I did it. Technically.",
    "AP": "The homework attacked my teeth first \u2014 I was defending myself, and my teeth won.",
    # v4 challengers AQ-AT (rubrics scored BEFORE the v4 proxy ran).
    "AQ": "Floor food is dog food \u2014 your homework was on the floor, and I don't make the rules.",
    "AR": "I don't make the rules \u2014 floor food is dog food, and your homework was on the floor.",
    "AS": "I didn't eat it, I translated it \u2014 English in, bark out, and bark is my first language.",
    "AT": "The homework attacked my teeth first \u2014 self-defence, obviously, and my teeth won.",
}

# Hand rubric, scored BEFORE the proxy ran (c1..c5, total /25).
RUBRIC = {
    "A": (5, 5, 4, 4, 5), "B": (5, 4, 5, 4, 4), "C": (5, 4, 5, 4, 4),
    "D": (5, 4, 5, 4, 5), "E": (5, 5, 5, 4, 5), "F": (5, 4, 4, 4, 4),
    "G": (5, 5, 4, 4, 5), "H": (5, 5, 5, 4, 5), "I": (5, 5, 5, 4, 5),
    "J": (5, 4, 5, 4, 4), "K": (5, 4, 5, 4, 4), "L": (5, 5, 5, 4, 4),
    "M": (5, 3, 5, 4, 4), "N": (5, 4, 4, 4, 5), "O": (5, 3, 4, 4, 4),
    "P": (5, 3, 5, 3, 2), "Q": (5, 4, 5, 4, 4), "R": (5, 4, 5, 4, 4),
    "S": (5, 4, 4, 4, 4), "T": (5, 4, 4, 4, 4), "U": (5, 3, 5, 4, 4),
    "V": (5, 5, 4, 5, 5), "W": (5, 4, 5, 4, 4), "X": (5, 4, 5, 4, 4),
    "Y": (4, 1, 4, 3, 3), "Z": (4, 2, 4, 3, 1),
    # v2 challenger rubrics, scored BEFORE the v2 proxy ran.
    "AA": (5, 5, 5, 5, 5), "AB": (5, 5, 5, 5, 5), "AC": (5, 5, 4, 4, 5),
    "AD": (5, 5, 5, 5, 5), "AE": (5, 5, 4, 4, 5), "AF": (5, 5, 5, 4, 4),
    "AG": (5, 4, 5, 5, 4), "AH": (5, 4, 5, 4, 4), "AI": (5, 4, 5, 4, 4),
    # v3 challenger rubrics, scored BEFORE the v3 proxy ran.
    "AJ": (5, 5, 5, 5, 5), "AK": (5, 5, 5, 5, 5), "AL": (5, 5, 5, 5, 5),
    "AM": (5, 5, 4, 5, 5), "AN": (5, 5, 5, 4, 4),
    # v4 challenger rubrics, scored BEFORE the v3 proxy ran.
    "AO": (5, 5, 5, 5, 5), "AP": (5, 5, 5, 5, 5),
    # v4 challenger rubrics, scored BEFORE the v4 proxy ran.
    "AQ": (5, 5, 5, 5, 5), "AR": (5, 5, 5, 5, 5),
    "AS": (5, 5, 5, 4, 5), "AT": (5, 5, 5, 5, 5),
}

# ---------------------------------------------------------------- proxy scorer
STOCK = ["the cat", "tasted like paper", "taste of paper", "tastes like paper",
         "good boy", "good girl", "tasted like", "tastes like", "taste like"]
TWIST = ["true", "technically", "literally", "actually", "turns out",
         "oldest", "prove", "respect", "obviously", "teamwork"]
# Specific detail words; "homework" itself is excluded — it is the topic,
# not a detail. A line with no fresh detail and no number is stale.
FRESH_DETAIL = ["bacon", "floor", "snack", "snacks", "maths", "fractions",
                "chapter", "belly", "teeth", "bark", "sandwich", "shoes",
                "squirrel", "stomach", "chicken", "deadline", "spelling",
                "assignment", "teacher", "school", "words", "home", "work",
                "respect", "teamwork", "tuesday", "literally", "obviously",
                "language", "enemy", "delicious", "rules", "tomorrow",
                "sitting", "leftovers", "run away"]
HUMAN_EMOTION = ["sorry", "ashamed", "embarrassed", "embarrassing", "guilty",
                 "apologize", "apologise", "forgive", "my fault", "i'm sorry"]
DOG_WORDS = ["bacon", "floor", "snack", "snacks", "smell", "teeth", "bark",
             "belly", "nap", "walk", "treat", "chase", "chased", "squirrel",
             "stomach", "chicken", "sandwich", "shoes", "digested", "dog",
             "hungry", "tail", "paws", "eating", "ate", "run away"]
FILLER = ["very", "just", "really", "actually", "so", "quite", "simply"]
NUMBERS = re.compile(r"(?<!-)\b(\d|one|two|three|four|five|six|seven|eight"
                     r"|nine|ten|twelve|forty|fifty|sixty|hundred|thousand"
                     r"|zero|first|second)\b(?!-)")
SPECIFIC = ["bacon", "floor", "snack", "snacks", "maths", "fractions",
            "chapter", "belly", "teeth", "bark", "sandwich", "shoes",
            "squirrel", "stomach", "chicken", "deadline", "spelling",
            "assignment", "homework", "teacher", "school", "words"]
CONTRAST = [";", " but ", " then ", ", then ", " yet ", " instead ",
            " except ", " still ", " \u2014 ", "\u2014", "while ", "so ",
            "so I", "so technically"]
# End punches only: twist words (TWIST) are credited in c2, never here.
PUNCH_END = ["rules", "again", "fractions", "floor", "survive", "job",
             "done", "it.", "way.", "fast.", "rubs.", "language.",
             "anyone.", "pages.", "no.", "ends.", "did it.",
             "my homework.", "tuesday"]
EAT_VERBS = ["ate", "eat", "eating", "finished", "digested", "devoured",
             "swallowed", "chewed"]


def _has(text, words):
    low = text.lower()
    return any(w in low for w in words)


def _has_word(text, words):
    """Whole-word match: "home" must not fire inside "homework", so the
    fresh-detail test cannot be passed by the topic word itself."""
    low = text.lower()
    return any(re.search(r"\b" + re.escape(w) + r"\b", low)
               for w in words)


def _quoted_phrases(text):
    """Quoted phrases of 2+ words; the opening quote must not be preceded
    by a letter, so possessives/contractions never fake a quote."""
    return re.findall(r"(?<![A-Za-z])'([^']*\s+[^']*)'", text)


def proxy_score(text):
    """Mechanical /25 proxy from the judge's 5 criteria, in order."""
    low = text.lower()
    words = re.findall(r"[A-Za-z0-9']+", text)
    n_chars = len(text)

    # c1: dog's own-voice excuse. 5 for first-person dog voice (the brief
    # frames every entry as the dog's excuse, so "it" is the homework);
    # 4 when homework is named but the voice is third-person; 3 for an
    # eat verb with neither; else 0.
    first = re.search(r"\b(i|my|me|we)\b", low) is not None
    eat = _has(text, EAT_VERBS)
    hw = "homework" in low
    c1 = 5.0 if first else (4.0 if hw else (3.0 if eat else 0.0))

    # c2: laugh. Contrast +1.0, numbers +0.5 for one token / +1.0 for two
    # or more, self-loop (I/me as the butt) +0.5, specific concrete noun
    # +0.5, quoted phrase of 2+ words +0.5, parallel repetition +0.5,
    # triple list +0.5, short setup (first clause <= 9 words) +0.5,
    # twist word +0.5; -1.0 when the line carries no laugh device at
    # all. Base 0.5.
    c2 = 0.5
    device = False
    if _has(text, CONTRAST):
        c2 += 1.0
        device = True
    n_num = len(NUMBERS.findall(low))
    if n_num >= 2:
        c2 += 1.0
        device = True
    elif n_num == 1:
        c2 += 0.5
        device = True
    if re.search(r"\bi\b", low) or re.search(r"\bme\b", low):
        c2 += 0.5
    if _has(text, SPECIFIC):
        c2 += 0.5
    if _quoted_phrases(text):
        c2 += 0.5
        device = True
    # Parallel repetition: same content word (len>=4) in both halves, or
    # any word (len>=3) in 3+ segments.
    halves = re.split(r"[;,\u2014]", text)
    if len(halves) >= 2:
        first_half = set(w.lower() for w in re.findall(r"[A-Za-z]{4,}",
                                                        halves[0]))
        rest = " ".join(halves[1:]).lower()
        repeated3 = any(
            sum(1 for h in halves
                if re.search(r"\b" + w + r"\b", h.lower())) >= 3
            for w in set(re.findall(r"[A-Za-z]{3,}", text.lower())))
        if (any(re.search(r"\b" + w + r"\b", rest) for w in first_half)
                or repeated3):
            c2 += 0.5
            device = True
    # Triple list: >=2 commas and " and ".
    if text.count(",") >= 2 and " and " in low:
        c2 += 0.5
        device = True
    first_clause = re.split(r"[;,]", text)[0]
    if len(re.findall(r"[A-Za-z0-9']+", first_clause)) <= 9:
        c2 += 0.5
    if _has(text, TWIST):
        c2 += 0.5
    if not device:
        c2 -= 1.0
    c2 = max(0.5, min(c2, 5.0))

    # c3: real dog. Start 5; -2 per human-emotion/apology word; -1 if no
    # dog-priority word at all (reads like a person, not a dog).
    c3 = 5.0
    for h in HUMAN_EMOTION:
        if re.search(r"\b" + re.escape(h) + r"\b", low):
            c3 -= 2.0
    if not _has(text, DOG_WORDS):
        c3 -= 1.0
    c3 = max(c3, 1.0)

    # c4: works alone, tight. Start 4.5; -0.5 per 10 chars over 120; -0.5
    # per filler word; +0.5 if the punch lands at the end (a punch word
    # in the raw last 30 characters).
    c4 = 4.5
    if n_chars > 120:
        c4 -= 0.5 * ((n_chars - 120 + 9) // 10)
    for f in FILLER:
        if re.search(r"\b" + f + r"\b", low):
            c4 -= 0.5
    if _has(text[-30:], PUNCH_END):
        c4 += 0.5
    c4 = max(1.0, min(c4, 5.0))

    # c5: fresh. Start 5; -2 per stock hit (cat / taste of paper /
    # good boy / any "tasted like" taste trope); -2 if no fresh detail
    # word and no number (generic = stale).
    c5 = 5.0
    for s in STOCK:
        if s in low:
            c5 -= 2.0
    if not _has_word(text, FRESH_DETAIL) and not NUMBERS.search(low):
        c5 -= 2.0
    c5 = max(c5, 1.0)

    total = round(c1 + c2 + c3 + c4 + c5, 1)
    return total, (c1, c2, c3, c4, c5)


def pick():
    scored = []
    for label, text in CANDIDATES.items():
        p, parts = proxy_score(text)
        r = sum(RUBRIC[label])
        scored.append((label, text, p, r, parts))
    # Highest proxy, then highest rubric, then shorter, then earliest
    # label (the competition tie-break favours smaller text).
    scored.sort(key=lambda s: (-s[2], -s[3], len(s[1]), s[0]))
    return scored


def main():
    scored = pick()
    for label, text, p, r, parts in scored:
        print(f"{label}: proxy {p} (c {parts}) rubric {r} "
              f"[{len(text)}ch] {text}")
    label, text, p, r, _ = scored[0]
    print(f"PICK {label}: proxy {p} rubric {r}: {text}")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        os.makedirs("output", exist_ok=True)
        out_path = os.path.join("output", "entry.txt")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"WROTE {out_path} ({len(text)} chars, no trailing newline)")


if __name__ == "__main__":
    main()
