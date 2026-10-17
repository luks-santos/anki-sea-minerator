from seaminerator.core.audio.base import AudioError, media_name
from seaminerator.core.audio.recording import (
    Recording,
    RecordingRun,
    failed_run,
    record_all,
    run_notes,
)

GEMINI_DOWN = "Gemini quota or rate limit exceeded (HTTP 429)"
GOOGLE_DOWN = "Google Translate is unavailable (HTTP 503)"


class FakeRecorder:
    def __init__(self, source="google", name="Google Translate", outcomes=None):
        self.source = source
        self.voice = "us"
        self.name = name
        self.outcomes = outcomes or {}
        self.calls = []
        self.closed = False

    def record(self, text):
        self.calls.append(text)
        outcome = self.outcomes.get(text, f"{self.source}:{text}".encode())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self):
        self.closed = True


def gemini(outcomes=None):
    return FakeRecorder("gemini", "Gemini", outcomes)


def test_record_all_records_each_text_once_in_order():
    recorder = FakeRecorder()

    run = record_all([recorder], ["A.", "B.", "A."])

    assert recorder.calls == ["A.", "B."]
    assert run.recordings == {
        "A.": Recording(media_name("google", "us", "A."), b"google:A."),
        "B.": Recording(media_name("google", "us", "B."), b"google:B."),
    }
    assert run.failures == {}
    assert run.stopped is None
    assert run_notes(run) == []


def test_record_all_skips_blank_texts():
    recorder = FakeRecorder()

    run = record_all([recorder], ["", "A."])

    assert recorder.calls == ["A."]
    assert run.failures == {}


def test_record_all_reports_progress_for_each_text():
    seen = []

    record_all(
        [FakeRecorder()], ["A.", "B."], lambda done, total: seen.append((done, total))
    )

    assert seen == [(1, 2), (2, 2)]


def test_a_per_card_failure_does_not_stop_the_run():
    recorder = FakeRecorder(outcomes={"A.": AudioError("too long", source_down=False)})

    run = record_all([recorder], ["A.", "B."])

    assert run.failures == {"A.": "too long"}
    assert list(run.recordings) == ["B."]
    assert run.stopped is None


def test_a_source_failure_stops_the_run_and_marks_the_rest():
    recorder = FakeRecorder(outcomes={"C.": AudioError(GOOGLE_DOWN, source_down=True)})

    run = record_all([recorder], ["A.", "B.", "C.", "D.", "E."])

    assert recorder.calls == ["A.", "B.", "C."]
    assert list(run.recordings) == ["A.", "B."]
    assert run.failures == {"C.": GOOGLE_DOWN, "D.": GOOGLE_DOWN, "E.": GOOGLE_DOWN}
    assert run.stopped == GOOGLE_DOWN
    assert run_notes(run) == [
        f"Audio recording stopped: {GOOGLE_DOWN}. "
        "Cards without a recording use the system voice."
    ]


def test_an_unexpected_error_stops_the_run_instead_of_raising():
    recorder = FakeRecorder(outcomes={"A.": RuntimeError("boom")})

    run = record_all([recorder], ["A.", "B."])

    assert run.stopped == "unexpected error: boom"
    assert run.failures == {
        "A.": "unexpected error: boom",
        "B.": "unexpected error: boom",
    }


def test_the_backup_records_a_sentence_the_first_source_could_not():
    first = gemini({"B.": AudioError("Gemini returned no audio", source_down=False)})
    backup = FakeRecorder()

    run = record_all([first, backup], ["A.", "B."])

    assert backup.calls == ["B."]
    assert run.recordings["A."] == Recording(
        media_name("gemini", "us", "A."), b"gemini:A."
    )
    assert run.recordings["B."] == Recording(
        media_name("google", "us", "B."), b"google:B."
    )
    assert run.failures == {}
    assert run_notes(run) == []


def test_when_the_first_source_stops_the_backup_takes_the_rest():
    first = gemini({"B.": AudioError(GEMINI_DOWN, source_down=True)})
    backup = FakeRecorder()

    run = record_all([first, backup], ["A.", "B.", "C."])

    assert first.calls == ["A.", "B."]
    assert backup.calls == ["B.", "C."]
    assert set(run.recordings) == {"A.", "B.", "C."}
    assert run.stopped is None
    assert run_notes(run) == [
        f"{GEMINI_DOWN}; later sentences were recorded with Google Translate."
    ]


def test_when_every_source_stops_the_cards_use_the_system_voice():
    first = gemini({"A.": AudioError(GEMINI_DOWN, source_down=True)})
    backup = FakeRecorder(outcomes={"B.": AudioError(GOOGLE_DOWN, source_down=True)})

    run = record_all([first, backup], ["A.", "B.", "C."])

    both = f"{GEMINI_DOWN}; {GOOGLE_DOWN}"
    assert list(run.recordings) == ["A."]
    assert run.failures == {"B.": both, "C.": both}
    assert run.stopped == both
    assert run_notes(run) == [
        f"Audio recording stopped: {both}. "
        "Cards without a recording use the system voice."
    ]


def test_a_sentence_both_sources_fail_on_keeps_both_reasons():
    first = gemini({"A.": AudioError("Gemini returned no audio", source_down=False)})
    backup = FakeRecorder(outcomes={"A.": AudioError("too long", source_down=False)})

    run = record_all([first, backup], ["A."])

    assert run.failures == {"A.": "Gemini returned no audio; too long"}
    assert run.stopped is None


def test_the_run_closes_every_recorder_when_it_ends():
    first = gemini({"A.": AudioError(GEMINI_DOWN, source_down=True)})
    backup = FakeRecorder()

    record_all([first, backup], ["A."])

    assert (first.closed, backup.closed) == (True, True)


def test_failed_run_marks_every_text_with_the_reason():
    run = failed_run(["A.", "", "A.", "B."], "no key")

    assert run == RecordingRun(
        failures={"A.": "no key", "B.": "no key"}, stopped="no key"
    )


def test_the_stop_note_does_not_double_the_reason_s_period():
    run = failed_run(["A."], "Gemini audio needs a key (set it in settings).")

    assert run_notes(run) == [
        "Audio recording stopped: Gemini audio needs a key (set it in settings). "
        "Cards without a recording use the system voice."
    ]


def test_run_notes_are_empty_without_a_run():
    assert run_notes(None) == []
    assert run_notes(RecordingRun()) == []
