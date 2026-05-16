from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from hyperlocal.creative.contracts import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeCopyInput,
    CreativeRunRequest,
)
from hyperlocal.creative.image_generation import GeneratedCreative
from hyperlocal.creative.layout_rendering import LayoutRenderingService


class LayoutRenderingTests(unittest.TestCase):
    def test_fallback_renderer_writes_exact_typography_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            source_path = run_dir / "generated_images" / "source.png"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (360, 540), "#f7c45f").save(source_path)

            request = CreativeRunRequest(
                business=CreativeBusinessInput(name="Sunset Smoothie Co."),
                campaign=CreativeCampaignInput(
                    business_kind="smoothie",
                    product="Mango smoothie",
                    offer="BUY 1 GET 1 50% OFF",
                    cta="ORDER NOW",
                ),
            )
            copy = CreativeCopyInput(
                headline="Sunset Smoothie Co.",
                subhead="Mango smoothie",
                offer="BUY 1 GET 1 50% OFF",
                cta="",
            )
            source = GeneratedCreative(
                variant_index=1,
                prompt_index=1,
                image_variation=1,
                prompt_slug="mango_test",
                prompt_title="Mango Test",
                prompt="text-free mango smoothie scene",
                negative_prompt="avoid text",
                image_path=str(source_path),
            )

            results = LayoutRenderingService(enable_llm=False).render(
                request=request,
                run_dir=run_dir,
                source_images=[source],
                copies=[copy],
            )

            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.overlay_template, "ai_layout_typography")
            self.assertTrue(Path(result.final_image_url).exists())
            self.assertTrue(Path(result.layout_plan["plan_path"]).exists())
            self.assertEqual(result.layout_plan["elements"][0]["text"], "Sunset Smoothie Co.")
            self.assertEqual(result.layout_plan["elements"][1]["text"], "BUY 1 GET 1 50% OFF")

            original = Image.open(source_path).convert("RGB")
            rendered = Image.open(result.final_image_url).convert("RGB")
            self.assertEqual(rendered.size, original.size)
            self.assertIsNotNone(ImageChops.difference(original, rendered).getbbox())


if __name__ == "__main__":
    unittest.main()
