# ============================================================
# ai/plagiarism.py — Peer-to-Peer Plagiarism Detection (Phase-8)
# Compares a student's submission text against all other
# submissions for the same assignment using multiple methods:
#   1. Jaccard word-level similarity
#   2. Longest Common Subsequence ratio
#   3. N-gram fingerprinting
# Returns a plagiarism score and list of flagged matches.
# ============================================================

import re
from collections import Counter


# ── Configuration ────────────────────────────────────────────

SIMILARITY_THRESHOLD = 0.75    # 75% similarity = flagged
NGRAM_SIZE = 5                 # 5-word shingles for fingerprinting


# ── Text preprocessing ──────────────────────────────────────

def _normalize(text):
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _get_words(text):
    """Return list of normalized words."""
    return _normalize(text).split()


def _get_ngrams(words, n=NGRAM_SIZE):
    """Generate n-gram shingles from a word list."""
    if len(words) < n:
        return set()
    return set(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


# ── Similarity algorithms ───────────────────────────────────

def jaccard_similarity(text_a, text_b):
    """
    Word-level Jaccard similarity.
    Returns a float between 0 and 1.
    """
    words_a = set(_get_words(text_a))
    words_b = set(_get_words(text_b))

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


def ngram_similarity(text_a, text_b, n=NGRAM_SIZE):
    """
    N-gram (shingle) based similarity using Jaccard over n-grams.
    More resistant to word reordering than simple Jaccard.
    Returns a float between 0 and 1.
    """
    words_a = _get_words(text_a)
    words_b = _get_words(text_b)

    ngrams_a = _get_ngrams(words_a, n)
    ngrams_b = _get_ngrams(words_b, n)

    if not ngrams_a or not ngrams_b:
        return 0.0

    intersection = ngrams_a & ngrams_b
    union = ngrams_a | ngrams_b
    return len(intersection) / len(union) if union else 0.0


def cosine_similarity_words(text_a, text_b):
    """
    Cosine similarity over word frequency vectors.
    Returns a float between 0 and 1.
    """
    words_a = _get_words(text_a)
    words_b = _get_words(text_b)

    counter_a = Counter(words_a)
    counter_b = Counter(words_b)

    # All words in both
    all_words = set(counter_a.keys()) | set(counter_b.keys())
    if not all_words:
        return 0.0

    dot_product = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
    magnitude_a = sum(v ** 2 for v in counter_a.values()) ** 0.5
    magnitude_b = sum(v ** 2 for v in counter_b.values()) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# ── Combined similarity score ───────────────────────────────

def compute_similarity(text_a, text_b):
    """
    Compute a combined plagiarism similarity score between two texts.
    Uses a weighted average of three methods:
      - Jaccard word similarity   (weight: 0.25)
      - N-gram shingle similarity (weight: 0.40)
      - Cosine word similarity    (weight: 0.35)

    Returns:
        float: Combined similarity score between 0 and 1.
    """
    j_sim = jaccard_similarity(text_a, text_b)
    n_sim = ngram_similarity(text_a, text_b)
    c_sim = cosine_similarity_words(text_a, text_b)

    # Weighted combination: n-gram gets highest weight as it's most reliable
    combined = (0.25 * j_sim) + (0.40 * n_sim) + (0.35 * c_sim)
    return round(combined, 4)


# ── Main plagiarism check function ──────────────────────────

def check_plagiarism(submission_text, other_submissions, threshold=SIMILARITY_THRESHOLD):
    """
    Compare one submission against a list of other submissions.

    Args:
        submission_text (str): The text of the submission being checked.
        other_submissions (list[dict]): Each dict must have:
            - 'submission_id' (int)
            - 'student_id' (str)
            - 'text' (str): The extracted text of the other submission.
        threshold (float): Similarity score above which to flag as plagiarism.

    Returns:
        dict: {
            'is_plagiarized': bool,
            'max_similarity': float,
            'matches': [
                {
                    'submission_id': int,
                    'student_id': str,
                    'similarity': float,
                    'jaccard': float,
                    'ngram': float,
                    'cosine': float,
                },
                ...
            ]
        }
    """
    if not submission_text or not submission_text.strip():
        return {
            "is_plagiarized": False,
            "max_similarity": 0.0,
            "matches": [],
        }

    matches = []
    max_sim = 0.0

    for other in other_submissions:
        other_text = other.get("text", "")
        if not other_text or not other_text.strip():
            continue

        j_sim = jaccard_similarity(submission_text, other_text)
        n_sim = ngram_similarity(submission_text, other_text)
        c_sim = cosine_similarity_words(submission_text, other_text)
        combined = round((0.25 * j_sim) + (0.40 * n_sim) + (0.35 * c_sim), 4)

        if combined > max_sim:
            max_sim = combined

        if combined >= threshold:
            matches.append({
                "submission_id": other.get("submission_id"),
                "student_id": other.get("student_id"),
                "similarity": round(combined * 100, 1),
                "jaccard": round(j_sim * 100, 1),
                "ngram": round(n_sim * 100, 1),
                "cosine": round(c_sim * 100, 1),
            })

    # Sort matches by similarity descending
    matches.sort(key=lambda m: m["similarity"], reverse=True)

    return {
        "is_plagiarized": len(matches) > 0,
        "max_similarity": round(max_sim * 100, 1),
        "matches": matches,
    }
