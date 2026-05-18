from langnet.reader.display import decorate_segment_display


def test_decorate_segment_display_labels_english_source_text() -> None:
    segment = decorate_segment_display(
        {"text": "Of man's first disobedience"},
        language="eng",
    )

    assert segment["language"] == "eng"
    assert segment["display"]["script"] == "English"
    assert segment["available_layers"] == ["source"]


def test_decorate_segment_display_labels_hebrew_and_coptic_source_text() -> None:
    hebrew = decorate_segment_display({"text": "בראשית ברא"}, language="heb")
    coptic = decorate_segment_display({"text": "ⲡⲉϫⲉ"}, language="cop")

    assert hebrew["display"]["script"] == "Hebrew"
    assert hebrew["available_layers"] == ["source"]
    assert coptic["display"]["script"] == "Coptic"
    assert coptic["available_layers"] == ["source"]
