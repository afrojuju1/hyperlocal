from __future__ import annotations

import unittest
from unittest.mock import patch

from hyperlocal.contracts.creative_runs import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeGenerationOptions,
    CreativeRunRequest,
)
from hyperlocal.services.image_generation import ImageGenerationService


class BackgroundPromptingTests(unittest.TestCase):
    def test_template_prompt_specs_are_overlay_safe(self) -> None:
        service = ImageGenerationService()
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
                background_provider="comfyui_bg",
                text_mode="overlay",
            ),
        )

        specs = service._build_prompt_specs(request)

        self.assertEqual(len(specs), 2)
        for spec in specs:
            self.assertIn("plain and unmarked", spec.prompt)
            self.assertIn("one open, calm area", spec.prompt)
            self.assertTrue(spec.negative_prompt)

    def test_llm_prompt_specs_fall_back_to_templates(self) -> None:
        service = ImageGenerationService()
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="Sunset Smoothie Co."),
            campaign=CreativeCampaignInput(
                business_kind="smoothie",
                product="Mango smoothie",
                offer="BUY 1 GET 1 50% OFF",
                cta="ORDER NOW",
            ),
            generation=CreativeGenerationOptions(
                count=1,
                images_per_prompt=1,
                prompt_engine="llm",
                background_provider="comfyui_bg",
                text_mode="overlay",
            ),
        )

        with patch(
            "hyperlocal.services.image_generation.build_llm_prompts",
            side_effect=RuntimeError("llm offline"),
        ):
            specs = service._build_prompt_specs(request)

        self.assertEqual(len(specs), 1)
        self.assertIn("plain and unmarked", specs[0].prompt)

    def test_in_image_prompt_specs_ask_model_for_finished_ad(self) -> None:
        service = ImageGenerationService()
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="Sunset Smoothie Co."),
            campaign=CreativeCampaignInput(
                business_kind="smoothie",
                product="Mango smoothie",
                offer="BUY 1 GET 1 50% OFF",
                cta="ORDER NOW",
            ),
            generation=CreativeGenerationOptions(
                count=1,
                images_per_prompt=1,
                prompt_engine="template",
                background_provider="comfyui_bg",
                text_mode="in_image",
            ),
        )

        specs = service._build_prompt_specs(request)

        self.assertEqual(len(specs), 1)
        self.assertIn("finished vertical 6x9 ad creative", specs[0].prompt)
        self.assertIn('"Sunset Smoothie Co."', specs[0].prompt)
        self.assertIn('"BUY 1 GET 1 50% OFF"', specs[0].prompt)
        self.assertNotIn("ORDER NOW", specs[0].prompt)
        self.assertIn("No other readable words should appear.", specs[0].prompt)
        self.assertIn("do not put text inside boxes", specs[0].prompt)

    def test_in_image_prompt_specs_include_user_creative_direction(self) -> None:
        service = ImageGenerationService()
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="Sunset Smoothie Co."),
            campaign=CreativeCampaignInput(
                business_kind="smoothie",
                product="Mango smoothie",
                offer="BUY 1 GET 1 50% OFF",
                cta="ORDER NOW",
                audience="college students near campus",
                tone="playful but premium",
                constraints=["avoid plastic straws"],
                brand_colors=["mango orange", "deep green"],
                style_keywords=["editorial", "sunlit"],
            ),
            generation=CreativeGenerationOptions(
                count=1,
                images_per_prompt=1,
                prompt_engine="template",
                image_provider="comfyui_bg",
                creative_mode="full_ad",
            ),
        )

        spec = service._build_prompt_specs(request)[0]

        self.assertIn("Tone: playful but premium.", spec.prompt)
        self.assertIn("Audience: college students near campus.", spec.prompt)
        self.assertIn("User constraints: avoid plastic straws.", spec.prompt)
        self.assertIn("Brand color direction: mango orange, deep green.", spec.prompt)
        self.assertIn("Style keywords: editorial, sunlit.", spec.prompt)


if __name__ == "__main__":
    unittest.main()
