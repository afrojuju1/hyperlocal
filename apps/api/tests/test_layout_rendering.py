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
from hyperlocal.creative.layout_rendering import (
    CreativeLayoutPlan,
    LayoutRenderingService,
    LayoutTextElement,
)


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
            self.assertEqual(result.layout_plan["elements"][0]["color"], "auto")

    def test_image_safety_pass_moves_offer_from_busy_center(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "busy.png"
            image = Image.new("RGB", (360, 540), "#eeeeee")
            for y in range(160, 250, 8):
                color = "#111111" if (y // 8) % 2 else "#ffffff"
                for x in range(30, 330, 16):
                    image.paste(color, (x, y, x + 10, y + 6))
            image.save(image_path)

            plan = CreativeLayoutPlan(
                name="test",
                elements=[
                    LayoutTextElement(
                        role="headline",
                        text="Northside Plumbing & HVAC",
                        x=0.08,
                        y=0.06,
                        width=0.84,
                        height=0.18,
                    ),
                    LayoutTextElement(
                        role="offer",
                        text="$79 SERVICE CALL",
                        x=0.08,
                        y=0.30,
                        width=0.84,
                        height=0.12,
                        font_role="offer",
                    ),
                ],
            )

            refined = LayoutRenderingService(enable_llm=False)._refine_plan_for_image(
                input_image_path=image_path,
                plan=plan,
            )

            offer = next(element for element in refined.elements if element.role == "offer")
            self.assertNotEqual(offer.y, 0.30)

    def test_hvac_brand_defaults_use_service_colors(self) -> None:
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="Northside Plumbing & HVAC"),
            campaign=CreativeCampaignInput(
                business_kind="hvac",
                product="AC repair",
                offer="$79 SERVICE CALL",
                cta="CALL 24/7",
            ),
        )
        plan = CreativeLayoutPlan(
            name="test",
            elements=[
                LayoutTextElement(role="headline", text="Northside Plumbing & HVAC", x=0.08, y=0.06, width=0.84, height=0.18),
                LayoutTextElement(role="offer", text="$79 SERVICE CALL", x=0.08, y=0.24, width=0.84, height=0.12),
            ],
        )

        themed = LayoutRenderingService(enable_llm=False)._apply_brand_defaults(
            request=request,
            plan=plan,
        )

        self.assertEqual(themed.elements[0].color, "#0B3A82")
        self.assertEqual(themed.elements[1].color, "#B91C1C")
        self.assertEqual(themed.elements[1].stroke_color, "#FFFFFF")

    def test_real_estate_brand_defaults_use_property_colors(self) -> None:
        request = CreativeRunRequest(
            business=CreativeBusinessInput(name="RapidKeys Home Buyers"),
            campaign=CreativeCampaignInput(
                business_kind="real_estate",
                product="We buy houses for cash",
                offer="CLOSE IN AS LITTLE AS 7 DAYS",
                cta="GET CASH OFFER",
            ),
        )
        plan = CreativeLayoutPlan(
            name="test",
            elements=[
                LayoutTextElement(role="headline", text="RapidKeys Home Buyers", x=0.08, y=0.06, width=0.84, height=0.18),
                LayoutTextElement(role="offer", text="CLOSE IN AS LITTLE AS 7 DAYS", x=0.08, y=0.24, width=0.84, height=0.12),
            ],
        )

        themed = LayoutRenderingService(enable_llm=False)._apply_brand_defaults(
            request=request,
            plan=plan,
        )

        self.assertEqual(themed.elements[0].color, "#102A43")
        self.assertEqual(themed.elements[1].color, "#B7791F")


if __name__ == "__main__":
    unittest.main()
