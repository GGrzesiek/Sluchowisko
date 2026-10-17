from pipeline.tts import sentence_timings
from pipeline.verify import structural_check

DOCS = [
    {"id": "m1", "text": "Fakt z linkiem", "url": "https://example.org/a"},
    {"id": "m2", "text": "Fakt bez linku", "url": None},
]


def _story(*sentences):
    return {"sentences": [{"text": t, "source_ids": ids} for t, ids in sentences]}


def test_structural_ok():
    story = _story(("Jedno zdanie ze źródłem.", ["m1"]))
    assert structural_check(story, DOCS, min_words=1, max_words=100) == []


def test_structural_flags_missing_unknown_and_unlinked_sources():
    story = _story(("Bez źródła.", []), ("Nieznane.", ["x9"]), ("Bez linku.", ["m2"]))
    problems = structural_check(story, DOCS, min_words=1, max_words=100)
    assert "Sentence 1: no source" in problems
    assert "Sentence 2: unknown source x9" in problems
    assert "Sentence 3: source m2 has no link" in problems


def test_structural_flags_length():
    story = _story(("Za krótko.", ["m1"]))
    assert any(p.startswith("Length") for p in structural_check(story, DOCS, min_words=60, max_words=130))


def test_structural_flags_story_without_sentences():
    assert structural_check({"sentences": []}, DOCS) == ["No sentences"]


def test_sentence_timings():
    sentences = ["Ala ma kota.", "Kot ma Alę."]
    text = " ".join(sentences)
    alignment = {
        "characters": list(text),
        "character_start_times_seconds": [i * 0.1 for i in range(len(text))],
        "character_end_times_seconds": [i * 0.1 + 0.1 for i in range(len(text))],
    }
    t = sentence_timings(sentences, alignment)
    assert t[0] == {"text": "Ala ma kota.", "start": 0.0, "end": 1.2}
    assert t[1]["start"] == 1.3
    assert t[1]["end"] == round(len(text) * 0.1, 3)
