from seaminerator.core.flow import CardResult
from seaminerator.core.models import Sentence, WordBlock
from seaminerator.core.session import (
    apply_class_overrides,
    count_selected,
    default_selection,
    format_elapsed,
    selected_sentences,
    summarize,
)


def make_block(expression, n_sentences):
    return WordBlock(
        expression=expression,
        explanation="",
        translations=["x"],
        class_tag="noun",
        sentences=[
            Sentence(text=f"{expression} {i}.", highlight=expression)
            for i in range(n_sentences)
        ],
    )


def test_default_selection_picks_first_sentence_of_each_word():
    blocks = [make_block("give up", 5), make_block("overwhelming", 3)]
    assert default_selection(blocks) == {0: {0}, 1: {0}}


def test_default_selection_skips_words_without_sentences():
    blocks = [make_block("give up", 5), make_block("empty", 0)]
    assert default_selection(blocks) == {0: {0}}


def test_count_selected_sums_all_indices():
    assert count_selected({0: {0, 2}, 1: {1}}) == 3


def test_count_selected_is_zero_for_empty_selection():
    assert count_selected({0: set(), 1: set()}) == 0


def test_selected_sentences_returns_blocks_with_their_chosen_sentences():
    blocks = [make_block("give up", 12), make_block("overwhelming", 2)]
    # {3, 11} iterates as [11, 3] in CPython, so this only passes if
    # selected_sentences really sorts the indices.
    pairs = selected_sentences(blocks, {0: {3, 11}, 1: set()})

    assert len(pairs) == 1
    word, sentences = pairs[0]
    assert word.expression == "give up"
    assert [s.text for s in sentences] == ["give up 3.", "give up 11."]


def test_format_elapsed_uses_seconds_below_a_minute():
    assert format_elapsed(42.4) == "42s"


def test_format_elapsed_uses_minutes_and_seconds():
    assert format_elapsed(125.0) == "2m05s"


def test_summarize_counts_created_and_failed():
    results = [
        CardResult(expression="a", front="a", created=True, note_id=1),
        CardResult(
            expression="b", front="b", created=False, warning="card not created: boom"
        ),
        CardResult(
            expression="c", front="c", created=True, note_id=2, warning="highlight"
        ),
    ]

    summary = summarize(results, elapsed_seconds=65.0)

    assert summary.created == 2
    assert summary.failed == 1
    assert summary.warnings == ["card not created: boom", "highlight"]
    assert summary.elapsed == "1m05s"


def test_summarize_handles_empty_results():
    summary = summarize([], elapsed_seconds=0.0)
    assert summary.created == 0
    assert summary.failed == 0
    assert summary.warnings == []


def test_apply_class_overrides_without_overrides_returns_same_blocks():
    blocks = [make_block("give up", 1)]
    assert apply_class_overrides(blocks, {}) == blocks


def test_apply_class_overrides_replaces_the_class_of_the_chosen_word():
    blocks = [make_block("give up", 1), make_block("whale", 1)]

    result = apply_class_overrides(blocks, {0: "phrasal-verb"})

    assert result[0].class_tag == "phrasal-verb"
    assert result[0].sentences == blocks[0].sentences
    assert result[1].class_tag == "noun"


def test_apply_class_overrides_normalizes_typed_text():
    blocks = [make_block("must", 1)]
    assert apply_class_overrides(blocks, {0: " Modal Verb "})[0].class_tag == (
        "modal-verb"
    )


def test_apply_class_overrides_falls_back_when_text_is_blank():
    blocks = [make_block("whale", 1)]
    assert apply_class_overrides(blocks, {0: "   "})[0].class_tag == "noun"
