import copy
import json
import shutil

import pytest

from collector.schema import CollectedStop
from story_agent import audio, files
from story_agent.checks import check_plan, check_script, check_voiced, word_budget
from story_agent.models import StoryPlan, StoryScript, VoicedScript
from story_agent.record import build_record
from story_agent.sources import split_sections, wikitext_to_text
from story_agent.stops import target_duration

MATERIAL = {
    "stop": {
        "group_id": "9001",
        "name": "Młyńska",
        "lat": 52.23,
        "lon": 21.01,
        "poles": [{"pole": "01", "lat": 52.23, "lon": 21.01}],
    },
    "area": {
        "district": "Dzielnica Testowa",
        "neighbourhood": None,
        "fragment_ids": [],
        "street_names": [{"name": "Młyńska", "object_id": "o1", "named_after": None, "distance_m": 0}],
        "nearby_articles": [],
    },
    "objects": [
        {
            "id": "o1",
            "name": "ulica Młyńska",
            "kind": "street",
            "distance_m": 0,
            "osm_id": "way/1",
            "wikidata": None,
            "wikipedia": None,
            "named_after": None,
            "named_after_label": None,
            "old_names": [],
            "heritage_ref": None,
            "tags": {"highway": "residential"},
        }
    ],
    "sources": [
        {
            "id": "s1",
            "type": "encyclopedia",
            "title": "Ulica Młyńska (przykład)",
            "publisher": "Encyklopedia Testowa",
            "url": "https://example.org/mlynska",
            "license": "CC BY-SA 4.0",
            "license_url": None,
            "author": None,
            "author_death_year": None,
            "retrieved_at": "2026-10-17",
        },
        {
            "id": "s2",
            "type": "literature",
            "title": "Opis miasta (przykład)",
            "publisher": "Biblioteka Testowa",
            "url": "https://example.org/opis",
            "license": "public domain",
            "license_url": None,
            "author": "Jan Przykładowy",
            "author_death_year": 1912,
            "retrieved_at": "2026-10-17",
        },
        {
            "id": "s3",
            "type": "blog",
            "title": "Blog o mieście (przykład)",
            "publisher": "Blog Testowy",
            "url": "https://example.org/blog",
            "license": "©",
            "license_url": None,
            "author": None,
            "author_death_year": None,
            "retrieved_at": "2026-10-17",
        },
    ],
    "fragments": [
        {
            "id": "s1#1",
            "source_id": "s1",
            "section": "Historia",
            "text": "Ulica powstała w 1820 r. przy drodze do młyna wodnego. Młyn rozebrano w 1905 r. "
            "Nazwa ulicy upamiętnia ten młyn. Przy młynie działała kuźnia, w której podkuwano konie woźniców.",
            "object_id": "o1",
            "derived": False,
        },
        {
            "id": "s1#2",
            "source_id": "s1",
            "section": "Współczesność",
            "text": "W miejscu młyna stoi dziś szkoła podstawowa. W 1960 r. ulicę wyasfaltowano.",
            "object_id": "o1",
            "derived": False,
        },
        {
            "id": "s2#1",
            "source_id": "s2",
            "section": None,
            "text": "Nad stawem młyńskim zawsze unosiła się mgła, a koła stukały od świtu do nocy.",
            "object_id": None,
            "derived": False,
        },
        {
            "id": "s3#1",
            "source_id": "s3",
            "section": None,
            "text": "Podobno w młynie bywał sam król.",
            "object_id": None,
            "derived": False,
        },
    ],
    "images": [],
}

FACTS = [
    (
        "F1",
        "Ulica powstała w 1820 r. przy drodze do młyna.",
        "s1#1",
        "Ulica powstała w 1820 r. przy drodze do młyna wodnego.",
    ),
    ("F2", "Nazwa ulicy upamiętnia młyn.", "s1#1", "Nazwa ulicy upamiętnia ten młyn."),
    ("F3", "Przy młynie działała kuźnia.", "s1#1", "Przy młynie działała kuźnia, w której podkuwano konie woźniców."),
    ("F4", "Młyn rozebrano w 1905 r.", "s1#1", "Młyn rozebrano w 1905 r."),
    ("F5", "W miejscu młyna stoi dziś szkoła.", "s1#2", "W miejscu młyna stoi dziś szkoła podstawowa."),
    ("F6", "W 1960 r. ulicę wyasfaltowano.", "s1#2", "W 1960 r. ulicę wyasfaltowano."),
]

PLAN = {
    "group_id": "9001",
    "stop_name": "Młyńska",
    "target_duration_s": 45,
    "facts": [
        {
            "id": fid,
            "text": text,
            "evidence": [{"fragment_id": frag, "quote": quote}],
            "kind": "fact",
            "confidence": "confirmed",
            "object_id": "o1",
            "era": "1800_1918",
        }
        for fid, text, frag, quote in FACTS
    ]
    + [
        {
            "id": "F7",
            "text": "Autor opisał mgłę nad stawem młyńskim i stukot kół.",
            "evidence": [
                {
                    "fragment_id": "s2#1",
                    "quote": "Nad stawem młyńskim zawsze unosiła się mgła, a koła stukały od świtu do nocy.",
                }
            ],
            "kind": "literature",
            "confidence": "medium",
            "object_id": None,
            "era": "1800_1918",
        }
    ],
    "rejected": [
        {"text": "W młynie bywał król.", "fragment_ids": ["s3#1"], "reason": "single_weak_source", "note": None}
    ],
    "contradictions": [],
    "axis_candidates": [{"axis": "Młyn, od którego ulica wzięła nazwę", "bridge_type": "C", "reason": "Nazwa."}],
    "story": {
        "status": "ok",
        "axis": "Ulica nazywa się Młyńska, bo prowadziła do młyna, którego już nie ma.",
        "listener_question": "Skąd nazwa Młyńska?",
        "bridge": {"type": "C", "draft": "Nazwa przystanku to ślad młyna.", "fact_ids": ["F2"]},
        "hook": {"fact_ids": ["F3"], "why": "Kuźnia daje dźwięk i obraz."},
        "change_mode": "trace",
        "period_voice": {
            "fact_id": "F7",
            "fragment_id": "s2#1",
            "quote": "Nad stawem młyńskim zawsze unosiła się mgła, a koła stukały od świtu do nocy.",
            "author": "Jan Przykładowy",
        },
        "steps": [
            {"role": "anchor", "fact_ids": [], "note": None},
            {"role": "place_fact", "fact_ids": ["F1", "F2"], "note": None},
            {"role": "jump", "fact_ids": ["F3", "F7"], "note": None},
            {"role": "return", "fact_ids": ["F4", "F5"], "note": None},
        ],
        "explain": [],
        "tone": "light",
        "era": "1800_1918",
    },
    "text_sections": [{"draft_heading": "Ulica po młynie", "fact_ids": ["F6", "F4"]}],
    "image_ids": [],
    "gaps": [],
    "spare_layers": [],
    "fetch_log": [],
}

SCRIPT = {
    "group_id": "9001",
    "title": "Młyńska",
    "cast": "solo_with_archive",
    "tone": "light",
    "target_duration_s": 45,
    "lines": [
        {
            "id": "L1",
            "voice": "narrator",
            "role": "anchor",
            "text": "Młyńska. Za oknem szkoła, asfalt i ani śladu wody.",
            "fact_ids": [],
            "delivery": "spokojnie",
            "pause_after_s": 0.3,
        },
        {
            "id": "L2",
            "voice": "narrator",
            "role": "place_fact",
            "text": "A jednak ta ulica powstała w 1820 roku jako droga do młyna wodnego. Stąd nazwa.",
            "fact_ids": ["F1", "F2"],
            "delivery": None,
            "pause_after_s": 0.5,
        },
        {
            "id": "L3",
            "voice": "archive",
            "role": "quote",
            "text": "Nad stawem młyńskim zawsze unosiła się mgła, a koła stukały od świtu do nocy.",
            "fact_ids": ["F7"],
            "delivery": None,
            "pause_after_s": 0.4,
        },
        {
            "id": "L4",
            "voice": "narrator",
            "role": "jump",
            "text": "Przy młynie działała kuźnia. Podkuwano tu konie woźniców.",
            "fact_ids": ["F3"],
            "delivery": "z ciekawością",
            "pause_after_s": 1.5,
        },
        {
            "id": "L5",
            "voice": "narrator",
            "role": "return",
            "text": "Młyn rozebrano w 1905 roku. Dziś w jego miejscu stoi szkoła, którą właśnie mijasz.",
            "fact_ids": ["F4", "F5"],
            "delivery": None,
            "pause_after_s": 0,
        },
    ],
    "sounds": [
        {
            "id": "S1",
            "kind": "motif",
            "shape": "swell",
            "description": "uderzenia młota o kowadło, coraz bliżej",
            "fact_ids": ["F3"],
            "start": {"line_id": "L3", "edge": "end", "offset_s": 0},
            "end": {"line_id": "L4", "edge": "end", "offset_s": 1.2},
        }
    ],
    "music": None,
    "text": [
        {
            "heading": "Ulica po młynie",
            "paragraphs": [
                {
                    "sentences": [
                        {"text": "Po rozbiórce młyna w 1905 roku ulica została.", "fact_ids": ["F4"]},
                        {"text": "W 1960 roku dostała asfalt.", "fact_ids": ["F6"]},
                    ]
                }
            ],
        }
    ],
    "image_ids": [],
}

VOICED = {
    "group_id": "9001",
    "lines": [
        {"id": "L1", "voice": "narrator", "tts_text": "[calm] Młyńska. Za oknem szkoła, asfalt… i ani śladu wody."},
        {
            "id": "L2",
            "voice": "narrator",
            "tts_text": "A jednak ta ulica powstała w tysiąc osiemset dwudziestym roku jako droga do młyna wodnego. "
            "Stąd nazwa.",
        },
        {
            "id": "L3",
            "voice": "archive",
            "tts_text": "[reading] Nad stawem młyńskim zawsze unosiła się mgła, a koła stukały od świtu do nocy.",
        },
        {
            "id": "L4",
            "voice": "narrator",
            "tts_text": "[curious] Przy młynie działała kuźnia. Podkuwano tu konie woźniców.",
        },
        {
            "id": "L5",
            "voice": "narrator",
            "tts_text": "Młyn rozebrano w tysiąc dziewięćset piątym roku. Dziś w jego miejscu stoi szkoła, "
            "którą właśnie mijasz.",
        },
    ],
    "sounds": [
        {
            "id": "S1",
            "prompt": "Blacksmith hammer striking an anvil in a village forge, steady rhythm, no voices",
            "duration_s": 8,
            "loop": True,
        }
    ],
    "music": None,
    "pronunciations": [],
}


@pytest.fixture
def material():
    return CollectedStop.model_validate(MATERIAL)


@pytest.fixture
def plan():
    return StoryPlan.model_validate(copy.deepcopy(PLAN))


@pytest.fixture
def script():
    return StoryScript.model_validate(copy.deepcopy(SCRIPT))


@pytest.fixture
def voiced():
    return VoicedScript.model_validate(copy.deepcopy(VOICED))


def test_valid_plan_passes(plan, material):
    report = check_plan(plan, material, 45)
    assert report.ok, report.errors


def test_quote_must_be_verbatim(material):
    data = copy.deepcopy(PLAN)
    data["facts"][0]["evidence"][0]["quote"] = "Ulica powstała w 1821 r."
    assert any("dosłownie" in e for e in check_plan(StoryPlan.model_validate(data), material).errors)


def test_weak_source_alone_is_rejected(material):
    data = copy.deepcopy(PLAN)
    data["facts"].append(
        {
            "id": "F8",
            "text": "W młynie bywał król.",
            "evidence": [{"fragment_id": "s3#1", "quote": "Podobno w młynie bywał sam król."}],
            "kind": "fact",
            "confidence": "medium",
            "object_id": None,
            "era": None,
        }
    )
    assert any("słabe źródło" in e for e in check_plan(StoryPlan.model_validate(data), material).errors)


def test_confirmed_needs_strong_source(material):
    data = copy.deepcopy(PLAN)
    data["facts"][6]["confidence"] = "confirmed"
    assert any("confirmed" in e for e in check_plan(StoryPlan.model_validate(data), material).errors)


def test_period_voice_needs_public_domain(material):
    data = copy.deepcopy(MATERIAL)
    data["sources"][1]["author_death_year"] = 1980
    errors = check_plan(StoryPlan.model_validate(PLAN), CollectedStop.model_validate(data)).errors
    assert any("1955" in e for e in errors)


def test_valid_script_passes(script, plan, material):
    report = check_script(script, plan, material)
    assert report.ok, report.errors


def test_line_without_facts_only_as_anchor(plan, material):
    data = copy.deepcopy(SCRIPT)
    data["lines"][1]["fact_ids"] = []
    assert any("bez faktów" in e for e in check_script(StoryScript.model_validate(data), plan, material).errors)


def test_archive_reads_only_verbatim_quotes(plan, material):
    data = copy.deepcopy(SCRIPT)
    data["lines"][2]["text"] = "Nad stawem zawsze była mgła."
    assert any("archiwalny" in e for e in check_script(StoryScript.model_validate(data), plan, material).errors)


def test_tragic_tone_has_no_sounds(material):
    plan_data = copy.deepcopy(PLAN)
    plan_data["story"]["tone"] = "tragic"
    data = copy.deepcopy(SCRIPT)
    data["tone"] = "tragic"
    errors = check_script(StoryScript.model_validate(data), StoryPlan.model_validate(plan_data), material).errors
    assert any("tragiczny" in e for e in errors)


def test_war_sounds_are_banned(plan, material):
    data = copy.deepcopy(SCRIPT)
    data["sounds"][0]["description"] = "odległe strzały"
    assert any("zakazany" in e for e in check_script(StoryScript.model_validate(data), plan, material).errors)


def test_word_budget_catches_long_scripts(plan, material):
    data = copy.deepcopy(SCRIPT)
    data["lines"][1]["text"] = " ".join(["słowo"] * 200)
    assert any("budżet" in e for e in check_script(StoryScript.model_validate(data), plan, material).errors)
    assert word_budget(StoryScript.model_validate(SCRIPT)) > 50


def test_valid_voiced_passes(voiced, script):
    report = check_voiced(voiced, script)
    assert report.ok, report.errors


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("Ulica powstała w 1820 roku.", "cyfry"),
        ("Jedziemy ul. Młyńską do młyna wodnego teraz.", "skrót"),
        ("[shouting] Młyńska. Za oknem szkoła, asfalt i ani śladu wody.", "niedozwolony"),
        ('Młyńska <break time="1s"/> za oknem szkoła, asfalt i ani śladu wody.', "SSML"),
        ("Zupełnie inny tekst o czymś innym niż młyn i szkoła tutaj.", "różni się"),
    ],
)
def test_voiced_rules(voiced, script, text, needle):
    data = voiced.model_dump()
    data["lines"][0]["tts_text"] = text
    errors = check_voiced(VoicedScript.model_validate(data), script).errors
    assert any(needle in e for e in errors), errors


def test_target_duration():
    assert target_duration([60, 120]) == 45
    assert target_duration([30]) == 20
    assert target_duration([]) == 45


def test_split_sections_drops_references():
    text = "Wstęp o ulicy.\n== Historia ==\nDawniej młyn.\n=== Szczegóły ===\nKuźnia.\n"
    text += "== Przypisy ==\nx\n=== Pod ===\ny"
    assert split_sections(text) == [(None, "Wstęp o ulicy."), ("Historia", "Dawniej młyn."), ("Szczegóły", "Kuźnia.")]


def test_wikitext_to_text():
    raw = "'''Młyn''' stał przy [[Wisła|rzece]].{{Przypis|x}}<ref>źródło</ref> [[Plik:a.jpg|mały]]Koniec."
    assert wikitext_to_text(raw) == "Młyn stał przy rzece. Koniec."


def test_chunks_split_long_dialogue():
    lines = [{"text": "a" * 900}, {"text": "b" * 900}, {"text": "c" * 900}]
    assert audio.chunks(lines) == [[0, 1], [2]]


def test_segments_by_line():
    segments = [
        {"dialogue_input_index": 0, "start_time_seconds": 0.0, "end_time_seconds": 1.0},
        {"dialogue_input_index": 1, "start_time_seconds": 1.2, "end_time_seconds": 2.0},
        {"dialogue_input_index": 1, "start_time_seconds": 2.0, "end_time_seconds": 3.0},
    ]
    assert audio._segments_by_line(segments, 2) == [(0.0, 1.0), (1.2, 3.0)]
    assert audio._segments_by_line(segments[:1], 2) is None


def test_swell_is_louder_in_pause_than_under_speech():
    speech = [audio.Placed(0, 5), audio.Placed(8, 12)]
    under = audio.envelope("swell", 4.0, 2.0, 9.0, speech)
    pause = audio.envelope("swell", 7.0, 2.0, 9.0, speech)
    assert pause > under * 2


def test_record(script, plan, material):
    record = build_record(script, plan, material, 41.6, "")
    assert record["title"] == "Młyńska"
    assert record["audio_seconds"] == 42
    assert record["sources"][0]["href"] == "https://example.org/mlynska"
    assert {s["href"] for s in record["sources"]} == {"https://example.org/mlynska", "https://example.org/opis"}
    assert "Ulica po młynie" in record["text"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_dry_run_render(script, voiced, tmp_path):
    timeline = audio.render(script, voiced, tmp_path / "out.mp3", dry_run=True)
    assert (tmp_path / "out.mp3").exists()
    assert timeline["sounds"]["S1"][0] >= timeline["lines"]["L3"][1] - 0.01
    assert timeline["lines"]["L5"][0] - timeline["lines"]["L4"][1] >= 1.5 - 0.01
    files.write_json(tmp_path / "timeline.json", timeline)
    assert json.loads((tmp_path / "timeline.json").read_text(encoding="utf-8"))["dry_run"] is True


def _fake_json(url, params=None, method="GET", data=None):
    params = params or {}
    if "/api/lines/22/routes/" in url:
        return {"stops": [{"zespol": "5003", "slupek": "07", "lat": 52.2399, "lon": 20.9846, "name": "Okopowa"}]}, ""
    if url.endswith("/api/lines/22/"):
        return {"routes": [{"code": "TP-TEST"}]}, ""
    if "wikidata.org" in url:
        entities = {
            "Q1": {
                "labels": {"pl": {"value": "Jan Testowy"}},
                "descriptions": {"pl": {"value": "inżynier"}},
                "claims": {"P569": [{"mainsnak": {"datavalue": {"value": {"time": "+1800-01-01T00:00:00Z"}}}}]},
                "sitelinks": {"plwiki": {"title": "Jan Testowy"}},
            }
        }
        return {"entities": {q: entities[q] for q in params["ids"].split("|") if q in entities}}, "2026-10-17"
    if "fandom.com" in url:
        if params.get("list") == "search":
            return {"query": {"search": [{"title": "Okopowa"}]}}, "2026-10-17"
        return {"parse": {"title": "Okopowa", "wikitext": {"*": "'''Okopowa''' – ulica na [[Wola|Woli]]."}}}, ""
    if "commons.wikimedia.org" in url:
        page = {
            "title": "File:Okopowa.jpg",
            "imageinfo": [
                {
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Okopowa.jpg",
                    "thumburl": "https://upload.wikimedia.org/okopowa.jpg",
                    "extmetadata": {
                        "LicenseShortName": {"value": "CC BY-SA 4.0"},
                        "ImageDescription": {"value": "<b>Ulica</b> Okopowa"},
                        "Artist": {"value": "<a>Autor</a>"},
                        "DateTimeOriginal": {"value": "1935"},
                    },
                }
            ],
            "coordinates": [{"dist": 50}],
        }
        nd = {**page, "title": "File:Nd.jpg"}
        nd["imageinfo"] = [{**page["imageinfo"][0], "extmetadata": {"LicenseShortName": {"value": "CC BY-ND 4.0"}}}]
        return {"query": {"pages": {"1": page, "2": nd}}}, ""
    if params.get("list") == "geosearch":
        return {"query": {"geosearch": [{"title": "Ulica Okopowa w Warszawie", "dist": 12.4}]}}, ""
    if params.get("prop") == "extracts|info":
        title = params["titles"]
        extract = f"{title} to hasło.\n== Historia ==\nDawniej był tu wał.\n== Przypisy ==\nx"
        page = {"title": title, "extract": extract, "fullurl": f"https://pl.wikipedia.org/wiki/{title}"}
        return {"query": {"pages": {"1": page}}}, "2026-10-17"
    raise AssertionError(f"unexpected request {url} {params}")


def test_collect_basic_builds_valid_file(monkeypatch, tmp_path):
    from story_agent import collect, sources

    overpass = {
        "elements": [
            {"type": "area", "id": 1, "tags": {"admin_level": "9", "name": "Wola", "wikipedia": "pl:Wola (Warszawa)"}},
            {
                "type": "way",
                "id": 10,
                "tags": {"highway": "secondary", "name": "Okopowa", "name:etymology:wikidata": "Q1"},
                "geometry": [{"lat": 52.2399, "lon": 20.9847}],
            },
            {
                "type": "way",
                "id": 11,
                "tags": {"highway": "secondary", "name": "Okopowa", "wikipedia": "pl:Ulica Okopowa w Warszawie"},
                "geometry": [{"lat": 52.2410, "lon": 20.9850}],
            },
            {
                "type": "node",
                "id": 12,
                "lat": 52.2401,
                "lon": 20.9849,
                "tags": {"historic": "memorial", "name": "Tablica"},
            },
        ]
    }
    for module in (collect, sources):
        monkeypatch.setattr(module, "fetch_json", _fake_json, raising=False)
    monkeypatch.setattr(collect, "fetch_text", lambda *a, **k: (json.dumps(overpass), ""))
    monkeypatch.setattr(collect, "download", lambda url, target: target)
    path = collect.collect_basic("5003", out=tmp_path)
    from collector.schema import load

    collected = load(path)
    assert collected.stop.poles[0].pole == "07"
    assert collected.area.district == "Wola"
    assert [o.name for o in collected.objects] == ["Okopowa", "Tablica"]
    assert collected.objects[0].named_after_label == "Jan Testowy"
    assert collected.objects[0].wikipedia == "pl:Ulica Okopowa w Warszawie"
    assert len(collected.images) == 1 and collected.images[0].caption == "Ulica Okopowa"
    assert any(f.derived and f.template == "wikidata_entity" for f in collected.fragments)
    assert all(f.section != "Przypisy" for f in collected.fragments)
    assert collected.area.fragment_ids
    assert collected.area.nearby_articles[0].fetched


def test_fetch_more_appends_new_source(monkeypatch, tmp_path):
    from collector.schema import save
    from story_agent import material as material_module
    from story_agent.sources import SourceDraft

    monkeypatch.setattr(files, "OUT", tmp_path)
    save(CollectedStop.model_validate(MATERIAL), tmp_path / "collected")
    draft = SourceDraft(
        type="encyclopedia",
        title="Kuźnia (przykład)",
        publisher="Encyklopedia Testowa",
        url="https://example.org/kuznia",
        license="CC BY-SA 4.0",
        license_url=None,
        retrieved_at="2026-10-17",
        sections=[(None, "Kuźnia stała przy młynie do 1890 r.")],
    )
    monkeypatch.setattr(material_module, "wikipedia_article", lambda title: draft)
    output = material_module.fetch_more("9001", "wikipedia", "Kuźnia", "fragment wspomina kuźnię")
    assert output.startswith("s4: Kuźnia (przykład)")
    assert "[s4#1]" in output
    loaded = material_module.load_material("9001")
    assert loaded.sources[-1].id == "s4"
    assert material_module.fetch_log("9001")[0]["tool"] == "wikipedia"
    again = material_module.fetch_more("9001", "wikipedia", "Kuźnia", "jeszcze raz")
    assert again.startswith("To źródło już jest")
