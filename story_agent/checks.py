import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from collector.schema import CollectedStop
from story_agent.material import quote_in_fragment
from story_agent.models import StoryPlan, StoryScript, VoicedScript

HIGH = {"official", "city_data", "institution", "encyclopedia"}
MEDIUM = {"varsaviana", "press", "local_portal"}
LOW = {"blog", "commercial"}
PUBLIC_DOMAIN_DEATH_YEAR = 1955
WORDS_PER_SECOND = 2.3
SOUND_LEAD_S = 3.0
UNRESOLVED = ("nierozstrzygni", "unresolved")
CAST_VOICES = {
    "solo": {"narrator"},
    "duet": {"narrator", "co_narrator"},
    "solo_with_archive": {"narrator", "archive"},
    "duet_with_archive": {"narrator", "co_narrator", "archive"},
}
BANNED_SOUND_PL = re.compile(
    r"strza|wystrza|wybuch|eksploz|syren|bomb|krzyk|płacz|placz|karabin|salw|jęk|alarm lotniczy|nalot", re.I
)
BANNED_SOUND_EN = re.compile(
    r"\b(guns?|gunfire|gunshots?|shots?|explosi\w*|sirens?|bomb\w*|scream\w*|cry|crying|war|air raid|"
    r"rifles?|artillery|moan\w*|blood\w*)\b",
    re.I,
)
ALLOWED_TAGS = {
    "calm",
    "curious",
    "thoughtful",
    "warm",
    "softly",
    "whispers",
    "serious",
    "sighs",
    "excited",
    "amused",
    "slowly",
    "matter-of-fact",
    "reading",
}
TRAGIC_TAGS = {"calm", "serious", "softly", "slowly", "reading"}
ABBREVIATIONS = re.compile(
    r"(?<![\w])(ul|al|pl|św|ok|tzw|m\.in|im|nr|gen|ks|prof|dr|r|w|wg|ds|ww|tj|np|godz|min|km|m|zł|proc)\.(?=\s|$)",
    re.I,
)
ROMAN = re.compile(r"\b[IVXLCDM]{2,}\b")
TAG = re.compile(r"\[([^\]]+)\]")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}

    def __str__(self) -> str:
        lines = ["OK" if self.ok else f"BŁĘDY: {len(self.errors)}"]
        lines += [f"  ✗ {e}" for e in self.errors]
        lines += [f"  ! {w}" for w in self.warnings]
        return "\n".join(lines)


def words(text: str) -> list[str]:
    return re.findall(r"[\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+(?:[-'][\w]+)*", text)


def narration_fact_ids(plan: StoryPlan) -> set[str]:
    story = plan.story
    ids = {f for step in story.steps for f in step.fact_ids}
    ids |= {e.fact_id for e in story.explain if e.fact_id}
    if story.hook:
        ids |= set(story.hook.fact_ids)
    if story.bridge:
        ids |= set(story.bridge.fact_ids)
    if story.period_voice:
        ids.add(story.period_voice.fact_id)
    return ids


def text_fact_ids(plan: StoryPlan) -> set[str]:
    return {f for section in plan.text_sections for f in section.fact_ids}


def check_plan(plan: StoryPlan, material: CollectedStop, target_duration_s: int | None = None) -> Report:
    report = Report()
    if plan.group_id != material.stop.group_id:
        report.errors.append(f"group_id {plan.group_id} ≠ {material.stop.group_id}")
    if target_duration_s and plan.target_duration_s != target_duration_s:
        report.errors.append(f"target_duration_s ma być {target_duration_s} (z data/demo_lines.json)")
    fragments = {f.id: f for f in material.fragments}
    sources = {s.id: s for s in material.sources}
    facts = {}
    for fact in plan.facts:
        if fact.id in facts:
            report.errors.append(f"{fact.id}: powtórzone id")
        facts[fact.id] = fact
        types = set()
        source_ids = set()
        for ev in fact.evidence:
            fragment = fragments.get(ev.fragment_id)
            if fragment is None:
                report.errors.append(f"{fact.id}: nie ma fragmentu {ev.fragment_id}")
                continue
            if not quote_in_fragment(ev.quote, fragment.text):
                report.errors.append(f"{fact.id}: cytat nie występuje dosłownie w {ev.fragment_id}: „{ev.quote[:80]}”")
            if len(ev.quote) > 400:
                report.warnings.append(f"{fact.id}: cytat dłuższy niż 400 znaków, skróć do jednego zdania")
            source = sources[fragment.source_id]
            types.add(source.type)
            source_ids.add(source.id)
        if fact.object_id and fact.object_id not in {o.id for o in material.objects}:
            report.errors.append(f"{fact.id}: nie ma obiektu {fact.object_id}")
        if not types:
            continue
        if fact.confidence == "confirmed" and not (types & HIGH) and len(source_ids) < 2:
            report.errors.append(f"{fact.id}: „confirmed” wymaga źródła o wysokiej wiarygodności albo dwóch źródeł")
        if types <= LOW and fact.kind not in ("claim", "guess", "memory"):
            report.errors.append(f"{fact.id}: tylko słabe źródło ({', '.join(sorted(types))}) — odrzuć albo oznacz")
        if fact.kind == "literature" and "literature" not in types:
            report.warnings.append(f"{fact.id}: rodzaj „literature”, ale źródło nie jest literaturą")

    def known(ids, where):
        for fact_id in ids:
            if fact_id not in facts:
                report.errors.append(f"{where}: nie ma faktu {fact_id}")

    story = plan.story
    for i, step in enumerate(story.steps):
        known(step.fact_ids, f"story.steps[{i}]")
    if story.hook:
        known(story.hook.fact_ids, "story.hook")
    if story.bridge:
        known(story.bridge.fact_ids, "story.bridge")
    for e in story.explain:
        if e.fact_id:
            known([e.fact_id], "story.explain")
    for i, section in enumerate(plan.text_sections):
        known(section.fact_ids, f"text_sections[{i}]")
    for i, layer in enumerate(plan.spare_layers):
        known(layer.fact_ids, f"spare_layers[{i}]")
    for i, c in enumerate(plan.contradictions):
        known(c.fact_ids, f"contradictions[{i}]")
        if c.resolution.lower().startswith(UNRESOLVED):
            used = narration_fact_ids(plan) & set(c.fact_ids)
            if used:
                report.errors.append(f"nierozstrzygnięta sprzeczność, a {sorted(used)} są w narracji")

    if story.period_voice:
        pv = story.period_voice
        known([pv.fact_id], "story.period_voice")
        fragment = fragments.get(pv.fragment_id)
        if fragment is None:
            report.errors.append(f"period_voice: nie ma fragmentu {pv.fragment_id}")
        else:
            if not quote_in_fragment(pv.quote, fragment.text):
                report.errors.append("period_voice: cytat nie jest dosłownie we fragmencie")
            source = sources[fragment.source_id]
            died = source.author_death_year
            if source.type != "official" and (died is None or died > PUBLIC_DOMAIN_DEATH_YEAR):
                report.errors.append(
                    f"period_voice: autor musi umrzeć najpóźniej w {PUBLIC_DOMAIN_DEATH_YEAR} r. (źródło {source.id})"
                )

    images = {i.id for i in material.images}
    for image_id in plan.image_ids:
        if image_id not in images:
            report.errors.append(f"image_ids: nie ma zdjęcia {image_id}")

    if story.status in ("ok", "area"):
        if not story.steps:
            report.errors.append("story.steps puste przy statusie ok/area")
        else:
            if story.steps[0].role != "anchor":
                report.warnings.append("pierwszy krok powinien być „anchor”")
            if story.steps[-1].role != "return":
                report.warnings.append("ostatni krok powinien być „return”")
        if story.bridge is None:
            report.errors.append("brak mostu (story.bridge) przy statusie ok/area")
        narration = narration_fact_ids(plan)
        if not 2 <= len(narration) <= 8:
            report.warnings.append(f"narracja używa {len(narration)} faktów (zwykle 3–6)")
        if len(text_fact_ids(plan)) < 3:
            report.warnings.append("tekst do czytania ma mniej niż 3 fakty")
        overlap = narration & text_fact_ids(plan)
        if len(overlap) > 3:
            report.warnings.append(f"tekst powtarza dużo faktów z narracji: {sorted(overlap)}")
    else:
        if story.steps:
            report.errors.append("status not_enough_material: steps muszą być puste")
        if not plan.gaps:
            report.errors.append("status not_enough_material: wpisz, czego brakuje (gaps)")
    return report


def _line_seconds(script: StoryScript) -> float:
    return sum(line.pause_after_s for line in script.lines)


def word_budget(script: StoryScript) -> int:
    speech = script.target_duration_s - _line_seconds(script) - (SOUND_LEAD_S if script.sounds else 1.0)
    return int(max(speech, 5) * WORDS_PER_SECOND)


def check_script(script: StoryScript, plan: StoryPlan, material: CollectedStop) -> Report:
    report = Report()
    if script.group_id != plan.group_id:
        report.errors.append("group_id różni się od planu")
    if script.target_duration_s != plan.target_duration_s:
        report.errors.append(f"target_duration_s ma być {plan.target_duration_s}")
    if script.tone != plan.story.tone:
        report.errors.append(f"ton ma być taki jak w planie: {plan.story.tone}")
    facts = {f.id: f for f in plan.facts}
    allowed_narration = narration_fact_ids(plan)
    fragments = {f.id: f for f in material.fragments}
    sources = {s.id: s for s in material.sources}

    line_ids = [line.id for line in script.lines]
    if len(set(line_ids)) != len(line_ids):
        report.errors.append("powtórzone id kwestii")
    voices = {line.voice for line in script.lines}
    expected = CAST_VOICES[script.cast]
    if voices != expected:
        report.errors.append(f"obsada „{script.cast}” wymaga głosów {sorted(expected)}, a są {sorted(voices)}")
    if script.lines[0].role != "anchor":
        report.warnings.append("pierwsza kwestia powinna być kotwicą (anchor)")
    if script.lines[-1].role != "return":
        report.warnings.append("ostatnia kwestia powinna wracać do miejsca (return)")

    narration_used = set()
    for line in script.lines:
        for fact_id in line.fact_ids:
            if fact_id not in facts:
                report.errors.append(f"{line.id}: nie ma faktu {fact_id} w planie")
            elif fact_id not in allowed_narration:
                report.warnings.append(f"{line.id}: {fact_id} nie był w planie narracji")
        narration_used |= set(line.fact_ids)
        if not line.fact_ids and line.role != "anchor":
            report.errors.append(f"{line.id}: zdanie bez faktów (dozwolone tylko w kotwicy)")
        if line.voice == "archive":
            if line.role != "quote":
                report.errors.append(f"{line.id}: głos archiwalny czyta tylko cytaty (role: quote)")
            ok = False
            for fact_id in line.fact_ids:
                for ev in facts[fact_id].evidence if fact_id in facts else []:
                    fragment = fragments.get(ev.fragment_id)
                    if fragment and quote_in_fragment(line.text, fragment.text):
                        source = sources[fragment.source_id]
                        died = source.author_death_year
                        if source.type == "official" or (died is not None and died <= PUBLIC_DOMAIN_DEATH_YEAR):
                            ok = True
            if not ok:
                report.errors.append(
                    f"{line.id}: cytat archiwalny musi być dosłownie we fragmencie z domeny publicznej "
                    "(autor zm. ≤ 1955 albo dokument urzędowy) i wskazany w fact_ids"
                )
            if len(words(line.text)) > 45:
                report.errors.append(f"{line.id}: cytat archiwalny za długi (maks. 45 słów)")
        elif line.role == "quote":
            report.errors.append(f"{line.id}: cytaty czyta tylko głos archive")

    total_words = sum(len(words(line.text)) for line in script.lines)
    budget = word_budget(script)
    if total_words > budget * 1.15:
        report.errors.append(f"narracja ma {total_words} słów, budżet ok. {budget} — skróć")
    elif total_words < budget * 0.6:
        report.warnings.append(f"narracja ma tylko {total_words} słów przy budżecie {budget}")

    if script.tone == "tragic":
        if script.cast != "solo":
            report.errors.append("ton tragiczny: jeden spokojny głos (cast: solo)")
        if script.sounds or script.music:
            report.errors.append("ton tragiczny: bez dźwięków i bez muzyki")

    sound_ids = [s.id for s in script.sounds]
    if len(set(sound_ids)) != len(sound_ids):
        report.errors.append("powtórzone id dźwięków")
    for sound in script.sounds:
        for fact_id in sound.fact_ids:
            if fact_id not in facts:
                report.errors.append(f"{sound.id}: nie ma faktu {fact_id}")
        for anchor in (sound.start, sound.end):
            if anchor and anchor.line_id not in line_ids:
                report.errors.append(f"{sound.id}: nie ma kwestii {anchor.line_id}")
        if (sound.kind == "spot") != (sound.shape == "spot"):
            report.errors.append(f"{sound.id}: kind „spot” idzie tylko z shape „spot”")
        if sound.shape == "spot" and sound.end is not None:
            report.errors.append(f"{sound.id}: dźwięk punktowy nie ma końca (end: null)")
        if sound.shape != "spot" and sound.end is None:
            report.errors.append(f"{sound.id}: tło i narastanie potrzebują końca (end)")
        if BANNED_SOUND_PL.search(sound.description):
            report.errors.append(f"{sound.id}: zakazany dźwięk (wojna, przemoc, cierpienie)")
    if script.music and len(script.sounds) > 2:
        report.warnings.append("muzyka i więcej niż 2 dźwięki — będzie tłoczno")

    text_ids = set()
    total_text_words = 0
    for s_i, section in enumerate(script.text):
        for p_i, paragraph in enumerate(section.paragraphs):
            for sentence in paragraph.sentences:
                total_text_words += len(words(sentence.text))
                where = f"text[{s_i}].paragraphs[{p_i}]"
                if not sentence.fact_ids:
                    report.errors.append(f"{where}: zdanie bez faktów: „{sentence.text[:60]}”")
                for fact_id in sentence.fact_ids:
                    if fact_id not in facts:
                        report.errors.append(f"{where}: nie ma faktu {fact_id}")
                text_ids |= set(sentence.fact_ids)
                if sentence.fact_ids and set(sentence.fact_ids) <= narration_used:
                    report.warnings.append(f"{where}: zdanie powtarza tylko fakty z narracji")
    if not 120 <= total_text_words <= 700:
        report.warnings.append(f"tekst do czytania ma {total_text_words} słów (zwykle 150–600)")
    images = {i.id for i in material.images}
    for image_id in script.image_ids:
        if image_id not in images:
            report.errors.append(f"image_ids: nie ma zdjęcia {image_id}")
    return report


def strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", TAG.sub(" ", text)).strip()


def check_voiced(voiced: VoicedScript, script: StoryScript) -> Report:
    report = Report()
    if voiced.group_id != script.group_id:
        report.errors.append("group_id różni się od scenariusza")
    pairs = list(zip(script.lines, voiced.lines, strict=False))
    if len(script.lines) != len(voiced.lines):
        report.errors.append(f"liczba kwestii {len(voiced.lines)} ≠ {len(script.lines)} w scenariuszu")
    allowed = TRAGIC_TAGS if script.tone == "tragic" else ALLOWED_TAGS
    for line, vline in pairs:
        if line.id != vline.id or line.voice != vline.voice:
            report.errors.append(f"{vline.id}: inna kolejność, id albo głos niż w scenariuszu ({line.id})")
            continue
        tags = [t.strip().lower() for t in TAG.findall(vline.tts_text)]
        for tag in tags:
            if tag not in allowed:
                report.errors.append(f"{vline.id}: niedozwolony znacznik [{tag}]")
        if len(tags) > 2:
            report.errors.append(f"{vline.id}: najwyżej 2 znaczniki na kwestię")
        if line.voice == "archive" and any(t != "reading" for t in tags):
            report.errors.append(f"{vline.id}: głos archiwalny tylko ze znacznikiem [reading] albo bez")
        spoken = strip_tags(vline.tts_text)
        if re.search(r"\d", spoken):
            report.errors.append(f"{vline.id}: cyfry — zapisz liczby słownie")
        if "<" in spoken or ">" in spoken:
            report.errors.append(f"{vline.id}: znaczniki SSML nie działają w eleven_v3")
        if match := ABBREVIATIONS.search(spoken):
            report.errors.append(f"{vline.id}: skrót „{match.group(0)}” — rozwiń")
        if match := ROMAN.search(spoken):
            report.errors.append(f"{vline.id}: liczba rzymska „{match.group(0)}” — zapisz słownie")
        before = [w.lower() for w in words(line.text) if not re.search(r"\d", w)]
        after = [w.lower() for w in words(spoken)]
        if before and SequenceMatcher(None, before, after).ratio() < 0.6:
            report.errors.append(f"{vline.id}: tekst za bardzo różni się od scenariusza — formater nie zmienia treści")
    script_sounds = {s.id for s in script.sounds}
    voiced_sounds = {s.id for s in voiced.sounds}
    if script_sounds != voiced_sounds:
        report.errors.append(f"dźwięki {sorted(voiced_sounds)} ≠ {sorted(script_sounds)} w scenariuszu")
    for sound in voiced.sounds:
        if BANNED_SOUND_EN.search(sound.prompt):
            report.errors.append(f"{sound.id}: zakazany dźwięk w prompcie")
    if bool(voiced.music) != bool(script.music):
        report.errors.append("muzyka musi być tam, gdzie w scenariuszu, i tylko tam")
    script_text = " ".join(line.text for line in script.lines).lower()
    for p in voiced.pronunciations:
        if p.word.lower() not in script_text:
            report.warnings.append(f"wymowa „{p.word}”: tego słowa nie ma w scenariuszu")
    chars = sum(len(v.tts_text) for v in voiced.lines)
    if chars > 2000:
        report.warnings.append(f"{chars} znaków — nagranie pójdzie w kilku częściach")
    return report
