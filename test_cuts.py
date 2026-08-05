#!/usr/bin/env python3
"""
Self-check for the logic touched by the ponytail audit cuts.

Covers the three refactors that carry real behaviour: the dice regex, the
wisdom recency weights, and the quests SQL after the connection pool removal.
Run with: python test_cuts.py

ponytail: asserts under __main__, no framework. Reach for pytest when there
are enough cases that naming and selecting them starts to matter.
"""

import os
import sys
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

FORMAT_ERROR = (
    "Necesito que me des los dados en un formato válido. "
    "Por ejemplo, `2d6`, `1d20` o `4df`."
)


def test_dice():
    from modules.dice import DiceModule

    d = DiceModule()
    cases = [
        # valid
        ("2d6", None),
        ("1d20", None),
        ("4df", None),
        ("100d6", None),
        ("1d2", None),
        ("1d9999", None),
        # out of range
        ("0d6", "¿Entonces... no tiro ningún dado?"),
        ("101d6", "Oye, no tengo tantos dados."),
        ("1d1", "¿De dónde quieres que saque un dado así?"),
        ("1d10000", "¿De dónde quieres que saque un dado así?"),
        # malformed
        ("abc", FORMAT_ERROR),
        ("2d", FORMAT_ERROR),
        ("d6", FORMAT_ERROR),
        ("2D6", FORMAT_ERROR),
        ("2d6d8", FORMAT_ERROR),
        ("2df6", FORMAT_ERROR),
        (" 2d6", FORMAT_ERROR),
        ("", FORMAT_ERROR),
    ]
    for dice, expected in cases:
        got = d.validate_dice(dice)
        assert got == expected, f"validate_dice({dice!r}): {got!r} != {expected!r}"

    assert len(d.roll_dice("5d6")) == 5
    assert all(1 <= r <= 6 for r in d.roll_dice("20d6"))
    assert set(d.roll_dice("10df")) <= {"-", "·", "+"}
    assert d.calculate_total([1, 2, 3]) == 6
    assert d.calculate_total(["-", "·", "+", "+"]) == 1
    print(f"dice: {len(cases)} validation cases + rolls OK")


def test_wisdom():
    from modules.wisdom import WisdomModule

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "wisdoms.json")
        old = (datetime.now() - timedelta(days=1)).isoformat()
        seed = [
            {"text": "unseen", "added_by": "a", "last_shown": ""},
            {"text": "recent", "added_by": "a", "last_shown": datetime.now().isoformat()},
            {"text": "stale", "added_by": "b", "last_shown": old},
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(seed, f)

        m = WisdomModule(path)
        assert len(m._wisdoms) == 3

        unseen, recent, stale = m._weights()
        assert unseen == 2_592_000, unseen  # 30 days for never-shown
        assert recent < stale < unseen, (recent, stale, unseen)

        total = sum(m._calculate_probability(w["text"]) for w in seed)
        assert abs(total - 100.0) < 1e-9, total
        assert m._calculate_probability("nope") == 0.0

        # add -> persisted, and probability reflects the new entry
        prob = m.add("nueva", "c")
        assert prob > 0
        assert json.loads(open(path, encoding="utf-8").read())[-1]["text"] == "nueva"

        # get_random stamps last_shown and writes through
        chosen = m.get_random()
        assert chosen in {"unseen", "recent", "stale", "nueva"}
        on_disk = json.loads(open(path, encoding="utf-8").read())
        assert any(w["text"] == chosen and w["last_shown"] for w in on_disk)

        # delete only removes the caller's own wisdom
        assert m.delete("nueva", "b") is False
        assert m.delete("nueva", "c") is True
        assert all(w["text"] != "nueva" for w in json.loads(open(path, encoding="utf-8").read()))

        # a missing file is not an error
        assert WisdomModule(os.path.join(tmp, "absent.json"))._wisdoms == []
        print("wisdom: weights, probabilities, add/get/delete round-trip OK")


def test_quests():
    from utils.config import config

    with tempfile.TemporaryDirectory() as tmp:
        config.QUEST_DB_PATH = os.path.join(tmp, "quests.db")
        from modules.quests import QuestsModule

        q = QuestsModule()

        quest_id = q.create_request("ringo")
        assert quest_id > 0, quest_id
        assert q.create_request("ringo") == -1  # duplicate pending request
        assert q.get_users_with_pending_requests() == ["ringo"]
        assert q.get_user_request_id("ringo") == quest_id
        assert q.get_user_active_quests("ringo") == []

        assert q.update_request("ringo", "matar al dragón", "100 monedas") is True
        active = q.get_user_active_quests("ringo")
        assert len(active) == 1 and active[0][2] == "matar al dragón", active
        assert q.get_users_with_pending_requests() == []
        assert q.update_request("ringo", "otra", "nada") is False  # nothing pending

        assert q.get_quest_options_for_player("ringo") == [
            f"{quest_id}: matar al dragón"
        ]

        # the write actually committed, not just cached on the connection
        with sqlite3.connect(config.QUEST_DB_PATH) as check:
            rows = check.execute("SELECT description FROM quests").fetchall()
        assert rows == [("matar al dragón",)], rows
        print("quests: create/update/read round-trip committed OK")


if __name__ == "__main__":
    test_dice()
    test_wisdom()
    test_quests()
    print("\nall checks passed")
