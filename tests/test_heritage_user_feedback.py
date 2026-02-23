from __future__ import annotations

from langnet.heritage.user_feedback import parse_user_feedback


def test_parse_user_feedback_extracts_guesses() -> None:
    html = """
    <html><body>
    <form><input type="radio" name="guess" value="{vi.s.nu},{n.}">
    <a class="navy" href="/skt/MW/245.html#vi.s.nu"><i>viṣṇu</i></a></form>
    </body></html>
    """
    matches = parse_user_feedback(html)
    assert matches
    assert matches[0].canonical == "vi.s.nu"
    assert matches[0].display in {"viṣṇu", "vi.s.nu"}
    assert matches[0].analysis
    if matches[0].entry_url:
        assert matches[0].entry_url.endswith("#vi.s.nu")
