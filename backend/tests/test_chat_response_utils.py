from app.docs.response_utils import is_greeting, trim_answer


def test_is_greeting_detects_common_greetings():
    assert is_greeting("hi") is True
    assert is_greeting("Hello there") is True
    assert is_greeting("good morning") is True
    assert is_greeting("What is the status of the machine?") is False


def test_trim_answer_caps_words():
    long_text = " ".join([f"word{i}" for i in range(120)])
    trimmed = trim_answer(long_text, max_words=100)
    assert len(trimmed.split()) <= 100
    assert trimmed.endswith("...")
