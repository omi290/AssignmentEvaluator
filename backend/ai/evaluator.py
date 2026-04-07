# ============================================================
# ai/evaluator.py — AI Evaluation Module (Phase-3)
# Analyzes student submission text using OpenAI GPT
# Falls back to heuristic scoring if API key is missing
# ============================================================

import json
import re
import os

# Try to import openai; graceful fallback if not installed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def _build_prompt(text, max_marks=100):
    """Build the structured evaluation prompt."""
    return f"""You are an expert academic assignment evaluator. Evaluate the following student submission based on these criteria:

1. **Correctness** — Is the content factually accurate and technically correct?
2. **Clarity** — Is the writing clear, well-structured, and easy to understand?
3. **Completeness** — Does the answer cover all aspects of the topic thoroughly?

Student Submission:
\"\"\"
{text[:4000]}
\"\"\"

Maximum possible marks: {max_marks}

You MUST respond in this exact JSON format (no extra text, just JSON):
{{
  "score": <number between 0 and {max_marks}>,
  "feedback": "<2-3 lines of constructive feedback>",
  "ai_probability": <number between 0 and 100 indicating likelihood this was AI-generated>
}}

Guidelines for scoring:
- 90-100%: Excellent — thorough, accurate, well-written
- 75-89%: Good — mostly correct with minor gaps
- 60-74%: Average — acceptable but needs improvement
- 40-59%: Below Average — significant gaps or errors
- 0-39%: Poor — major issues or largely incomplete

Guidelines for AI probability:
- Look for signs of AI-generated text: overly formal tone, generic phrasing, lack of personal insight, perfect grammar with no human touch
- 0-20%: Likely human-written
- 21-50%: Some AI characteristics
- 51-80%: Likely AI-assisted
- 81-100%: Almost certainly AI-generated"""


def _parse_ai_response(response_text, max_marks=100):
    """Parse the JSON response from GPT. Returns dict or None."""
    try:
        # Try direct JSON parse
        data = json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        match = re.search(r'\{[^{}]*"score"[^{}]*\}', response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    # Validate and clamp values
    score = min(max(float(data.get("score", 0)), 0), max_marks)
    feedback = str(data.get("feedback", "No feedback generated."))
    ai_prob = min(max(float(data.get("ai_probability", 0)), 0), 100)

    return {
        "score": round(score, 1),
        "feedback": feedback,
        "ai_probability": round(ai_prob, 1),
    }


def _heuristic_evaluate(text, max_marks=100):
    """
    Fallback heuristic evaluator when OpenAI is unavailable.
    Uses text analysis (word count, structure, keyword density) to estimate a score.
    """
    if not text or not text.strip():
        return {
            "score": 0,
            "feedback": "No content found in the submission. Please upload a valid document.",
            "ai_probability": 0,
        }

    words = text.split()
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_count = len(sentences)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    # --- Score calculation ---
    score = 0

    # Length score (0-30 points on 100 scale)
    if word_count >= 500:
        length_score = 30
    elif word_count >= 200:
        length_score = 20
    elif word_count >= 50:
        length_score = 10
    else:
        length_score = 5
    score += length_score

    # Structure score (0-25 points) — paragraphs and sentence variety
    if paragraph_count >= 5:
        structure_score = 25
    elif paragraph_count >= 3:
        structure_score = 18
    elif paragraph_count >= 2:
        structure_score = 12
    else:
        structure_score = 5
    score += structure_score

    # Average sentence length (readability proxy) (0-20 points)
    if sentence_count > 0:
        avg_sentence_len = word_count / sentence_count
        if 10 <= avg_sentence_len <= 25:
            readability_score = 20
        elif 5 <= avg_sentence_len < 10 or 25 < avg_sentence_len <= 35:
            readability_score = 12
        else:
            readability_score = 5
    else:
        readability_score = 2
    score += readability_score

    # Vocabulary diversity (0-15 points)
    unique_words = len(set(w.lower() for w in words))
    if word_count > 0:
        diversity = unique_words / word_count
        if diversity >= 0.6:
            vocab_score = 15
        elif diversity >= 0.4:
            vocab_score = 10
        else:
            vocab_score = 5
    else:
        vocab_score = 0
    score += vocab_score

    # Keyword/technical content bonus (0-10 points)
    technical_patterns = [
        r'\b(therefore|however|furthermore|moreover|consequently)\b',
        r'\b(algorithm|function|variable|data|system|process|method)\b',
        r'\b(analysis|conclusion|result|hypothesis|experiment)\b',
        r'\b(figure|table|equation|formula|diagram)\b',
    ]
    tech_count = sum(1 for p in technical_patterns if re.search(p, text, re.IGNORECASE))
    tech_score = min(tech_count * 3, 10)
    score += tech_score

    # Scale to max_marks
    scaled_score = round((score / 100) * max_marks, 1)

    # --- Feedback ---
    feedback_parts = []
    if word_count < 50:
        feedback_parts.append("The submission is very short and lacks depth.")
    elif word_count < 200:
        feedback_parts.append("The submission could benefit from more detailed explanations.")
    else:
        feedback_parts.append("Good effort with reasonable content coverage.")

    if paragraph_count < 2:
        feedback_parts.append("Consider organizing your answer into multiple paragraphs for better readability.")
    else:
        feedback_parts.append("The answer has a decent structure.")

    if vocab_score < 10:
        feedback_parts.append("Try to use more varied vocabulary and technical terminology.")

    feedback = " ".join(feedback_parts)

    # --- AI probability (heuristic) ---
    ai_signals = 0
    # Very uniform sentence length suggests AI
    if sentence_count > 3:
        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        if variance < 5:
            ai_signals += 30
    # Perfect paragraph structure with headers
    if re.search(r'(Introduction|Conclusion|In conclusion|To summarize)', text, re.IGNORECASE):
        ai_signals += 15
    # Very high vocabulary diversity can indicate AI
    if word_count > 100 and diversity > 0.75:
        ai_signals += 15
    # Generic transitional phrases
    generic_count = len(re.findall(r'\b(in addition|on the other hand|it is important to note)\b', text, re.IGNORECASE))
    ai_signals += min(generic_count * 10, 25)

    ai_probability = min(ai_signals, 95)

    return {
        "score": scaled_score,
        "feedback": feedback,
        "ai_probability": round(ai_probability, 1),
    }


def evaluate_submission(text, max_marks=100):
    """
    Main evaluation function.
    
    Args:
        text (str): The extracted text from a student submission.
        max_marks (int): Maximum marks for the assignment (default 100).
    
    Returns:
        dict: { "score": float, "feedback": str, "ai_probability": float }
    """
    if not text or not text.strip():
        return {
            "score": 0,
            "feedback": "No readable content found in the submission.",
            "ai_probability": 0,
        }

    # Try OpenAI first
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if OPENAI_AVAILABLE and api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert academic evaluator. Respond only with valid JSON."},
                    {"role": "user", "content": _build_prompt(text, max_marks)},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            ai_text = response.choices[0].message.content
            result = _parse_ai_response(ai_text, max_marks)
            if result:
                result["method"] = "openai"
                return result
        except Exception as e:
            print(f"[evaluator.py] OpenAI API call failed: {e}")
            # Fall through to heuristic

    # Fallback: heuristic evaluation
    result = _heuristic_evaluate(text, max_marks)
    result["method"] = "heuristic"
    return result
