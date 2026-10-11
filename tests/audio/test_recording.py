from seaminerator.core.audio.base import AudioError, media_name
from seaminerator.core.audio.recording import (
    Recording,
    RecordingRun,
    failed_run,
    record_all,
    stopped_note,
)


class FakeRecorder:
    source = "google"
    voice = "us"

    def __init__(self, outcomes=None):
        self.outcomes = outcomes or {}
        self.calls = []

    def record(self, text):
        self.calls.append(text)
        outcome = self.outcomes.get(text, b"mp3:" + text.encode())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_record_all_records_each_text_once_in_order():
    recorder = FakeRecorder()

    run = record_all(recorder, ["A.", "B.", "A."])

    assert recorder.calls == ["A.", "B."]
    assert run.recordings == {
        "A.": Recording(media_name("google", "us", "A."), b"mp3:A."),
        "B.": Recording(media_name("google", "us", "B."), b"mp3:B."),
    }
    assert run.failures == {}
    assert run.stopped is None


def test_record_all_skips_blank_texts():
    recorder = FakeRecorder()

    run = record_all(recorder, ["", "A."])

    assert recorder.calls == ["A."]
    assert run.failures == {}


def test_record_all_reports_progress_for_each_attempt():
    seen = []

    record_all(
        FakeRecorder(), ["A.", "B."], lambda done, total: seen.append((done, total))
    )

    assert seen == [(1, 2), (2, 2)]


def test_a_per_card_failure_does_not_stop_the_run():
    recorder = FakeRecorder({"A.": AudioError("too long", source_down=False)})

    run = record_all(recorder, ["A.", "B."])

    assert run.failures == {"A.": "too long"}
    assert list(run.recordings) == ["B."]
    assert run.stopped is None


def test_a_source_failure_stops_the_run_and_marks_the_rest():
    down = "Google Translate is unavailable (HTTP 503)"
    recorder = FakeRecorder({"C.": AudioError(down, source_down=True)})

    run = record_all(recorder, ["A.", "B.", "C.", "D.", "E."])

    assert recorder.calls == ["A.", "B.", "C."]
    assert list(run.recordings) == ["A.", "B."]
    assert run.failures == {"C.": down, "D.": down, "E.": down}
    assert run.stopped == down


def test_an_unexpected_error_stops_the_run_instead_of_raising():
    recorder = FakeRecorder({"A.": RuntimeError("boom")})

    run = record_all(recorder, ["A.", "B."])

    assert run.stopped == "unexpected error: boom"
    assert run.failures == {
        "A.": "unexpected error: boom",
        "B.": "unexpected error: boom",
    }


def test_failed_run_marks_every_text_with_the_reason():
    run = failed_run(["A.", "", "A.", "B."], "no key")

    assert run == RecordingRun(
        failures={"A.": "no key", "B.": "no key"}, stopped="no key"
    )


def test_stopped_note_explains_a_stopped_run_only():
    assert stopped_note(None) is None
    assert stopped_note(RecordingRun()) is None
    assert stopped_note(RecordingRun(stopped="quota exceeded")) == (
        "Audio recording stopped: quota exceeded. "
        "Cards without a recording use the system voice."
    )
