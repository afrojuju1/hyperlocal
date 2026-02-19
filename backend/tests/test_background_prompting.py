from __future__ import annotations

import unittest

from hyperlocal.contracts.creative_runs import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeGenerationOptions,
    CreativeRunRequest,
)
from hyperlocal.services.background_generation import BackgroundGenerationService


class BackgroundPromptingTests(unittest.TestCase):
    def test_template_prompt_specs_are_overlay_safe(self) -> None:
        service = BackgroundGenerationService()
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="Sunset Smoothie Co."),
            campaign=CreativeCampaignInput(
                business_kind="smoothie",
                product="Mango smoothie",
                offer="BUY 1 GET 1 50% OFF",
                cta="ORDER NOW",
            ),
            generation=CreativeGenerationOptions(
                count=2,
                images_per_prompt=1,
                prompt_engine="template",
                background_provider="ollama",
            ),
        )

        specs = service._build_prompt_specs(request)

        self.assertEqual(len(specs), 2)
        for spec in specs:
            self.assertIn("No text of any kind", spec.prompt)
            self.assertTrue(spec.negative_prompt)


if __name__ == "__main__":
    unittest.main()
