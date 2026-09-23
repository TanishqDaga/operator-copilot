"""Priority engine tests — product formula, worker wins the five-pack."""
from __future__ import annotations

import unittest

import priority


def snap(**kw):
    base = {
        "safety": {"level": "SAFE", "reasons": [], "details": []},
        "person": {"detected": False, "distance_m": None, "ttc_s": None, "source": "slider"},
        "speed_kmh": 0.0,
        "seatbelt": True,
        "weather": "clear",
        "anomaly": {"flag": False},
        "eta": {"changed_by": 0, "reason": None},
        "has_task": True,
    }
    base.update(kw)
    return base


def five_pack():
    return snap(
        safety={"level": "CRITICAL", "reasons": ["person_close", "ttc_low"], "details": ["", ""]},
        person={"detected": True, "distance_m": 2.0, "ttc_s": 1.4, "source": "slider"},
        seatbelt=False,
        anomaly={"flag": True, "type": "excess_idle", "label": "Idle duration",
                 "current": 15, "baseline": 4, "unit": "min", "score": -0.4, "threshold": -0.2},
        eta={"changed_by": 15, "reason": "Machine idle 15 min — no material moved", "task_id": "T1"},
    )


class RankTests(unittest.TestCase):
    def test_all_clear(self):
        r = priority.rank(snap())
        self.assertTrue(r["empty"])
        self.assertIsNone(r["headline"])
        self.assertEqual(r["quiet_count"], 0)

    def test_five_pack_worker_headline(self):
        r = priority.rank(five_pack())
        ids = [i["id"] for i in r["items"]]
        self.assertEqual(set(ids), {"prox", "seatbelt", "anomaly", "eta", "train_prox"})
        self.assertEqual(r["headline"]["id"], "prox")
        self.assertEqual(r["headline"]["title"], priority.HEADLINE_PROX)
        self.assertEqual(r["quiet_count"], 4)
        self.assertEqual(r["quiet"], "4 other items logged, not urgent.")

    def test_product_is_four_factors(self):
        r = priority.rank(five_pack())
        f = r["headline"]["facts"]
        self.assertAlmostEqual(f["product"], f["severity"] * f["time_to_harm"] * f["confidence"] * f["context"], places=5)

    def test_training_below_proximity_due_to_context(self):
        r = priority.rank(five_pack())
        prox = next(i for i in r["items"] if i["id"] == "prox")
        train = next(i for i in r["items"] if i["id"] == "train_prox")
        self.assertLess(train["facts"]["context"], prox["facts"]["context"])
        self.assertLess(train["score"], prox["score"])

    def test_eta_not_deduped_with_idle(self):
        r = priority.rank(five_pack())
        self.assertIn("eta", [i["id"] for i in r["items"]])
        self.assertIn("anomaly", [i["id"] for i in r["items"]])

    def test_closer_ttc_raises_product(self):
        far = priority.collect(snap(
            safety={"level": "CRITICAL", "reasons": ["person_close"], "details": [""]},
            person={"detected": True, "distance_m": 3.5, "ttc_s": 8.0, "source": "slider"},
        ))[0]
        near = priority.collect(snap(
            safety={"level": "CRITICAL", "reasons": ["person_close"], "details": [""]},
            person={"detected": True, "distance_m": 1.0, "ttc_s": 0.8, "source": "slider"},
        ))[0]
        self.assertGreater(near["score"], far["score"])


if __name__ == "__main__":
    unittest.main()
