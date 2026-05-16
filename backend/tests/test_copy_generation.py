from __future__ import annotations

import unittest

from hyperlocal.contracts.creative_runs import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeCopyInput,
    CreativeOverlayOptions,
    CreativeRunRequest,
)
from hyperlocal.services.copy_generation import CopyGenerationService


def make_request(copy_mode: str = "auto", provided_copy: CreativeCopyInput | None = None) -> CreativeRunRequest:
    return CreativeRunRequest(
        business=CreativeBusinessInput(name="Sunset Smoothie Co."),
        campaign=CreativeCampaignInput(
            business_kind="smoothie",
            product="Mango smoothie",
            offer="BUY 1 GET 1 50% OFF",
            cta="ORDER NOW",
        ),
        overlay=CreativeOverlayOptions(copy_mode=copy_mode),
        copy=provided_copy,
    )


class CopyGenerationTests(unittest.TestCase):
    def test_provided_copy_mode_reuses_input(self) -> None:
        provided = CreativeCopyInput(
            headline="Sunset Smoothie Co.",
            subhead="MANGO SMOOTHIES",
            offer="BUY 1 GET 1 50% OFF",
            cta="ORDER NOW",
            footer="Limited time",
        )
        service = object.__new__(CopyGenerationService)
        request = make_request(copy_mode="provided", provided_copy=provided)
        blocks = service.generate(request, 2)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].headline, "Sunset Smoothie Co.")
        self.assertEqual(blocks[1].cta, "ORDER NOW")

    def test_auto_mode_falls_back_when_llm_empty(self) -> None:
        service = object.__new__(CopyGenerationService)
        service._generate_with_llm = lambda request, target: []
        request = make_request(copy_mode="auto")
        blocks = service.generate(request, 1)
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].headline)
        self.assertTrue(blocks[0].offer)

    def test_normalize_applies_word_limits(self) -> None:
        service = object.__new__(CopyGenerationService)
        request = make_request(copy_mode="auto")
        raw = CreativeCopyInput(
            headline="One Two Three Four Five Six Seven Eight Nine",
            subhead="one two three four five six seven eight nine",
            offer="one two three four five six seven eight nine ten",
            cta="one two three four five six",
            footer="one two three four five six seven eight nine",
        )
        normalized = service._normalize(raw, request)
        self.assertLessEqual(len(normalized.headline.split()), 7)
        self.assertLessEqual(len(normalized.offer.split()), 9)
        self.assertLessEqual(len(normalized.cta.split()), 4)

    def test_normalize_keeps_offer_mechanics_out_of_other_fields(self) -> None:
        service = object.__new__(CopyGenerationService)
        request = make_request(copy_mode="auto")
        raw = CreativeCopyInput(
            headline="Sweet Deals, Sunny Flavors!",
            subhead="Fresh mango with big savings",
            offer="something else",
            cta="ORDER NOW",
            footer="50% off today only",
        )

        normalized = service._normalize(raw, request)

        self.assertEqual(normalized.headline, "Mango smoothie made fresh")
        self.assertEqual(normalized.subhead, "Fresh flavor, ready today")
        self.assertEqual(normalized.offer, "BUY 1 GET 1 50% OFF")
        self.assertEqual(normalized.footer, "Sunset Smoothie Co.")

    def test_normalize_keeps_clean_headline_prefix_before_offer_language(self) -> None:
        service = object.__new__(CopyGenerationService)
        request = make_request(copy_mode="auto")
        raw = CreativeCopyInput(
            headline="Mango Smoothie: Buy 1 Get 1 50%",
            subhead="Fresh mango, summer-style",
            offer="something else",
            cta="ORDER NOW",
            footer="Sunset Smoothie Co.",
        )

        normalized = service._normalize(raw, request)

        self.assertEqual(normalized.headline, "Mango Smoothie")


if __name__ == "__main__":
    unittest.main()
