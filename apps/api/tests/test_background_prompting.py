from __future__ import annotations

import unittest
from unittest.mock import patch

from hyperlocal.creative.contracts import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeGenerationOptions,
    CreativeRunRequest,
)
from hyperlocal.creative.image_generation import ImageGenerationService


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
            "hyperlocal.creative.image_generation.build_llm_prompts",
            side_effect=RuntimeError("llm offline"),
        ):
            specs = service._build_prompt_specs(request)

        self.assertEqual(len(specs), 1)
        self.assertIn("plain and unmarked", specs[0].prompt)

    def test_full_ad_prompt_specs_generate_text_free_source_image(self) -> None:
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
        self.assertIn("Portrait 6x9 vertical photographic background", specs[0].prompt)
        self.assertIn("plain and unmarked", specs[0].prompt)
        self.assertNotIn('Required visible text', specs[0].prompt)
        self.assertNotIn('"Sunset Smoothie Co."', specs[0].prompt)
        self.assertNotIn('"BUY 1 GET 1 50% OFF"', specs[0].prompt)
        self.assertNotIn("ORDER NOW", specs[0].prompt)
        self.assertIn("Avoid readable text", specs[0].negative_prompt)

    def test_runtime_meta_records_effective_text_mode(self) -> None:
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
                image_provider="comfyui_bg",
                creative_mode="full_ad",
            ),
        )

        meta = service.runtime_meta(request)

        self.assertEqual(meta["text_mode"], "overlay")
        self.assertEqual(meta["requested_text_mode"], "overlay")
        self.assertEqual(meta["final_typography"], "ai_layout")

    def test_full_ad_prompt_specs_include_user_creative_direction(self) -> None:
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
