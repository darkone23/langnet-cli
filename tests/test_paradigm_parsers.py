from __future__ import annotations

from langnet.paradigm.diogenes import parse_diogenes_inflect_html
from langnet.paradigm.heritage import (
    parse_heritage_conjugation_html,
    parse_heritage_declension_html,
)

HERITAGE_PUTRA_DECLENSION = """
<html><body>
<table class="inflexion">
  <tr><th></th><th>Singular</th><th>Dual</th><th>Plural</th></tr>
  <tr>
    <td>Nominative</td>
    <td><span class="red">putraḥ</span></td>
    <td><span class="red">putrau</span></td>
    <td><span class="red">putrāḥ</span></td>
  </tr>
  <tr>
    <td>Genitive</td>
    <td><span class="red">putrasya</span></td>
    <td><span class="red">putrayoḥ</span></td>
    <td><span class="red">putrāṇām</span></td>
  </tr>
  <tr>
    <td>Locative</td>
    <td><span class="red">putre</span></td>
    <td><span class="red">putrayoḥ</span></td>
    <td><span class="red">putreṣu</span></td>
  </tr>
</table>
</body></html>
"""


DIOGENES_LATIN_AMO_INFLECT = """
<html><body>
<span class="form_span_visible" infl="pres ind act 1st sg">
  <input type="checkbox" value="amo" />amo: (pres ind act 1st sg)
</span>
<span class="form_span_visible" infl="perf ind act 1st sg">
  <input type="checkbox" value="amavi" />amavi: (perf ind act 1st sg)
</span>
</body></html>
"""


HERITAGE_GAM_CONJUGATION = """
<html><body>
<span class="b2">Present</span>
<table class="inflexion">
  <tr><th><span class="b3">Active</span></th><th>Singular</th><th>Dual</th><th>Plural</th></tr>
  <tr>
    <td>First</td>
    <td><span class="red">gacchāmi</span></td>
    <td><span class="red">gacchāvaḥ</span></td>
    <td><span class="red">gacchāmaḥ</span></td>
  </tr>
  <tr>
    <td>Second</td>
    <td><span class="red">gacchasi</span></td>
    <td><span class="red">gacchathaḥ</span></td>
    <td><span class="red">gacchatha</span></td>
  </tr>
</table>
</body></html>
"""


DIOGENES_GREEK_LOGOS_INFLECT = """
<html><body>
<span class="form_span_visible" infl="nom sg masc">
  <input type="checkbox" value="lo/gos" />λόγος: (nom sg masc)
</span>
<span class="form_span_visible" infl="gen sg masc">
  <input type="checkbox" value="lo/gou" />λόγου: (gen sg masc)
</span>
<span class="form_span_visible" infl="dat sg masc">
  <input type="checkbox" value="lo/gw|" />λόγῳ: (dat sg masc)
</span>
</body></html>
"""


def test_parse_heritage_declension_table_preserves_case_number_slots() -> None:
    payload = parse_heritage_declension_html(
        HERITAGE_PUTRA_DECLENSION,
        lemma="putra",
        gender="Mas",
        request_url="http://localhost:48080/cgi-bin/skt/sktdeclin?q=putra;g=Mas",
    )

    slots = {
        (slot.features["case"], slot.features["number"]): slot
        for block in payload.paradigms
        for slot in block.slots
    }

    assert payload.source == "heritage:sktdeclin"
    assert payload.kind == "declension"
    assert slots[("nominative", "singular")].forms[0].text == "putraḥ"
    assert slots[("genitive", "plural")].forms[0].text == "putrāṇām"
    assert slots[("locative", "singular")].forms[0].text == "putre"


def test_parse_diogenes_latin_inflect_preserves_verbal_features() -> None:
    payload = parse_diogenes_inflect_html(
        DIOGENES_LATIN_AMO_INFLECT,
        language="lat",
        lemma="amo",
        kind="conjugation",
        request_url="http://localhost:8888/Perseus.cgi?do=inflect&lang=lat&q=amo",
    )

    slots = [slot for block in payload.paradigms for slot in block.slots]

    assert payload.source == "diogenes:inflect"
    assert slots[0].forms[0].text == "amo"
    assert slots[0].features == {
        "tense": "present",
        "mood": "indicative",
        "voice": "active",
        "person": "1",
        "number": "singular",
    }
    assert slots[1].forms[0].text == "amavi"
    assert slots[1].features["tense"] == "perfect"


def test_parse_heritage_conjugation_table_preserves_person_number_slots() -> None:
    payload = parse_heritage_conjugation_html(
        HERITAGE_GAM_CONJUGATION,
        root="gam",
        present_class="1",
        request_url="http://localhost:48080/cgi-bin/skt/sktconjug?q=gam;c=1",
    )

    slots = {
        (slot.features["person"], slot.features["number"]): slot
        for block in payload.paradigms
        for slot in block.slots
    }

    assert payload.source == "heritage:sktconjug"
    assert payload.kind == "conjugation"
    assert payload.paradigms[0].label == "Present Active"
    assert slots[("1", "singular")].features["tense"] == "present"
    assert slots[("1", "singular")].features["voice"] == "active"
    assert slots[("1", "singular")].forms[0].text == "gacchāmi"
    assert slots[("2", "plural")].forms[0].text == "gacchatha"


def test_parse_diogenes_greek_inflect_preserves_unicode_and_betacode_key() -> None:
    payload = parse_diogenes_inflect_html(
        DIOGENES_GREEK_LOGOS_INFLECT,
        language="grc",
        lemma="lo/gos",
        kind="declension",
        request_url="http://localhost:8888/Perseus.cgi?do=inflect&lang=grk&q=lo/gos",
    )

    slots = {
        (slot.features["case"], slot.features["number"]): slot
        for block in payload.paradigms
        for slot in block.slots
    }

    assert slots[("dative", "singular")].forms[0].text == "λόγῳ"
    assert slots[("dative", "singular")].forms[0].source_key == "lo/gw|"
    assert slots[("genitive", "singular")].forms[0].text == "λόγου"


def test_parse_diogenes_marks_syncretic_case_labels_as_ambiguous() -> None:
    payload = parse_diogenes_inflect_html(
        """
        <span class="form_span_visible" infl="masc nom/voc pl">
          <input type="checkbox" value="lo/goi" />λόγοι: (masc nom/voc pl)
        </span>
        """,
        language="grc",
        lemma="lo/gos",
        kind="declension",
    )

    slot = payload.paradigms[0].slots[0]

    assert slot.features["case"] == "nominative"
    assert slot.features["case_alternates"] == "nominative/vocative"
    assert slot.is_ambiguous is True
