from __future__ import annotations

import random
import unittest

from hyperlocal.creative.deterministic_overlay import TemplateVariant
from hyperlocal.creative.overlay_rendering import OverlayRenderingService


class OverlayTemplateSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = OverlayRenderingService()
        self.templates = [
            TemplateVariant(name="a", fonts={}, colors={}, layout={}),
            TemplateVariant(name="b", fonts={}, colors={}, layout={}),
            TemplateVariant(name="c", fonts={}, colors={}, layout={}),
        ]

    def test_static_mode_uses_first_template(self) -> None:
        selected = self.service._select_template(
            mode="static",
            templates=self.templates,
            index=3,
            rng=random.Random(1),
            forced_name=None,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "a")

    def test_cycle_mode_rotates_templates(self) -> None:
        picks = [
            self.service._select_template(
                mode="cycle",
                templates=self.templates,
                index=i,
                rng=random.Random(1),
                forced_name=None,
            ).name
            for i in [1, 2, 3, 4]
        ]
        self.assertEqual(picks, ["a", "b", "c", "a"])

    def test_random_mode_is_seeded(self) -> None:
        rng = random.Random(42)
        picks = [
            self.service._select_template(
                mode="random",
                templates=self.templates,
                index=i,
                rng=rng,
                forced_name=None,
            ).name
            for i in range(1, 4)
        ]
        self.assertEqual(picks, ["c", "a", "a"])

    def test_forced_template_name_wins(self) -> None:
        selected = self.service._select_template(
            mode="cycle",
            templates=self.templates,
            index=1,
            rng=random.Random(1),
            forced_name="b",
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "b")


if __name__ == "__main__":
    unittest.main()
