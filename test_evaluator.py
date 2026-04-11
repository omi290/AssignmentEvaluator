import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))
from ai.evaluator import evaluate_submission

def test():
    # Test 1: Relevant answer
    ans1 = "Python is a high-level programming language used for web development and data science." * 10
    r1 = evaluate_submission(ans1, 100, "Write about Python programming language")
    print(f"TEST1 Relevant: relevant={r1['is_relevant']}, score={r1['score']}, reason={r1['relevance_reason']}")

    # Test 2: Question paper copy
    q_copy = "Question 1: Explain the importance of version control. Question 2: What is a merge conflict?"
    r2 = evaluate_submission(q_copy, 100, q_copy)
    print(f"TEST2 Copy: relevant={r2['is_relevant']}, score={r2['score']}, reason={r2['relevance_reason']}")

    # Test 3: Unrelated content
    ans3 = "The French Revolution began in 1789 with political upheaval in France leading to the fall of the monarchy." * 5
    r3 = evaluate_submission(ans3, 100, "Explain the importance of version control using Git.")
    print(f"TEST3 Unrelated: relevant={r3['is_relevant']}, score={r3['score']}, reason={r3['relevance_reason']}")

if __name__ == "__main__":
    test()
