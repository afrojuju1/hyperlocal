from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from hyperlocal.creative.contracts import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeGenerationOptions,
    CreativeRunRequest,
)
from hyperlocal.creative.image_generation import ImageGenerationService
from hyperlocal.creative.qc import (
    build_retry_negative_prompt,
    build_retry_prompt,
    evaluate_background_image,
)


class BackgroundQcTests(unittest.TestCase):
    def test_plain_background_passes_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.png"
            Image.new("RGB", (360, 540), "#eeeeee").save(path)

            result = evaluate_background_image(image_path=path, business_kind="smoothie")

            self.assertTrue(result.passed)
            self.assertEqual(result.reasons, [])

    def test_obvious_background_text_fails_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "text.png"
            image = Image.new("RGB", (360, 540), "#eeeeee")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 56)
            except OSError:
                font = ImageFont.load_default()
            draw.text((30, 120), "FOR SALE", fill="#111111", font=font)
            draw.text((45, 190), "123 MAIN", fill="#111111", font=font)
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="real_estate")

            self.assertFalse(result.passed)
            self.assertIn("possible_background_text", result.reasons)
            self.assertGreater(result.metrics["text_score"], result.metrics["text_score_threshold"])

    def test_fully_busy_background_fails_calm_zone_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "busy.png"
            image = Image.new("RGB", (360, 540), "#eeeeee")
            for y in range(0, 540, 8):
                color = "#111111" if (y // 8) % 2 else "#ffffff"
                for x in range(30, 330, 16):
                    image.paste(color, (x, y, x + 10, y + 6))
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="hvac")

            self.assertFalse(result.passed)
            self.assertIn("no_calm_typography_zone", result.reasons)
            self.assertGreater(
                result.metrics["best_calm_zone_score"],
                result.metrics["calm_zone_score_threshold"],
            )

    def test_retry_prompt_adds_vertical_and_reason_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "text.png"
            image = Image.new("RGB", (360, 540), "#eeeeee")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 56)
            except OSError:
                font = ImageFont.load_default()
            draw.text((30, 120), "FOR SALE", fill="#111111", font=font)
            draw.text((45, 190), "123 MAIN", fill="#111111", font=font)
            image.save(path)
            result = evaluate_background_image(image_path=path, business_kind="real_estate")

        retry_prompt = build_retry_prompt(
            prompt="Create a calm home interior.",
            business_kind="real_estate",
            qc_result=result,
        )
        retry_negative = build_retry_negative_prompt(
            negative_prompt="Avoid text.",
            business_kind="real_estate",
            qc_result=result,
        )

        self.assertIn("listing signs", retry_prompt)
        self.assertIn("Remove all text-like shapes", retry_prompt)
        self.assertIn("no for-sale signs", retry_negative)
        self.assertIn("No text-like strokes", retry_negative)

    def test_image_generation_retries_until_background_passes_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            output_path = run_dir / "generated_images" / "01__test__v01.png"
            request = CreativeRunRequest(
                business=CreativeBusinessInput(name="RapidKeys Home Buyers"),
                campaign=CreativeCampaignInput(
                    business_kind="real_estate",
                    product="We buy houses for cash",
                    offer="CLOSE IN AS LITTLE AS 7 DAYS",
                    cta="GET CASH OFFER",
                ),
                generation=CreativeGenerationOptions(
                    count=1,
                    images_per_prompt=1,
                    prompt_engine="template",
                    image_provider="comfyui_bg",
                    creative_mode="full_ad",
                ),
            )
            service = ImageGenerationService()

            def fake_render(*, output_path: Path, **_kwargs) -> None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if output_path.name.endswith("attempt01.png"):
                    image = Image.new("RGB", (360, 540), "#eeeeee")
                    draw = ImageDraw.Draw(image)
                    try:
                        font = ImageFont.truetype(
                            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                            56,
                        )
                    except OSError:
                        font = ImageFont.load_default()
                    draw.text((30, 120), "FOR SALE", fill="#111111", font=font)
                    draw.text((45, 190), "123 MAIN", fill="#111111", font=font)
                    image.save(output_path)
                else:
                    Image.new("RGB", (360, 540), "#eeeeee").save(output_path)

            with (
                patch.object(service, "_should_qc", return_value=True),
                patch.object(service, "_render_image", side_effect=fake_render),
                patch("hyperlocal.creative.image_generation.RUNTIME_CONFIG") as runtime_config,
            ):
                runtime_config.max_image_attempts = 3
                render = service._generate_with_qc(
                    request=request,
                    provider="comfyui_bg",
                    openai_client=None,
                    openai_model="unused",
                    prompt="Create a clean interior.",
                    negative_prompt="Avoid text.",
                    output_path=output_path,
                    seq=1,
                )

            self.assertEqual(render["attempts"], 2)
            self.assertTrue(render["qc"]["passed"])
            self.assertTrue(output_path.exists())
            self.assertTrue((run_dir / "qc" / "01__test__v01__attempt01.json").exists())
            self.assertTrue((run_dir / "qc" / "01__test__v01__attempt02.json").exists())
            self.assertIn("listing signs", render["prompt"])


if __name__ == "__main__":
    unittest.main()
