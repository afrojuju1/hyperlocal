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

    def test_red_wall_text_fails_color_text_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "red_text.png"
            image = Image.new("RGB", (360, 540), "#f4f1ea")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 54)
            except OSError:
                font = ImageFont.load_default()
            draw.text((95, 180), "HOME", fill="#cc0000", font=font)
            draw.text((80, 242), "COMFORT", fill="#cc0000", font=font)
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="hvac")

            self.assertFalse(result.passed)
            self.assertIn("possible_background_text", result.reasons)
            self.assertGreater(
                result.metrics["color_text_score"],
                result.metrics["color_text_score_threshold"],
            )

    def test_orange_product_color_does_not_fail_color_text_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "orange_product.png"
            image = Image.new("RGB", (360, 540), "#f4f1ea")
            draw = ImageDraw.Draw(image)
            draw.ellipse((75, 170, 285, 380), fill="#f58220")
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="smoothie")

            self.assertTrue(result.passed)

    def test_thai_red_ingredients_do_not_fail_food_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thai_food.png"
            image = Image.new("RGB", (360, 540), "#ead8ba")
            draw = ImageDraw.Draw(image)
            draw.ellipse((70, 250, 290, 470), fill="#d98628")
            for x in range(90, 260, 28):
                draw.ellipse((x, 290, x + 18, 320), fill="#c52020")
                draw.line((x, 330, x + 70, 390), fill="#efc77d", width=6)
            draw.ellipse((120, 245, 160, 285), fill="#2c7a2c")
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="thai")

            self.assertTrue(result.passed)

    def test_large_blue_signage_fails_color_text_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blue_sign.png"
            image = Image.new("RGB", (360, 540), "#f4f1ea")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 76)
            except OSError:
                font = ImageFont.load_default()
            draw.text((20, 80), "HOME", fill="#062a63", font=font)
            draw.text((20, 155), "SELLERS", fill="#062a63", font=font)
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="real_estate")

            self.assertFalse(result.passed)
            self.assertIn("possible_background_text", result.reasons)
            self.assertGreater(
                result.metrics["blue_text_score"],
                result.metrics["blue_text_score_threshold"],
            )

    def test_dark_wing_wall_text_fails_dark_text_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dark_wing_text.png"
            image = Image.new("RGB", (360, 540), "#dfd2bf")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 72)
            except OSError:
                font = ImageFont.load_default()
            draw.text((40, 120), "JUICY", fill="#111111", font=font)
            draw.text((30, 205), "WINGS", fill="#111111", font=font)
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="wings")

            self.assertFalse(result.passed)
            self.assertIn("possible_background_text", result.reasons)
            self.assertGreater(
                result.metrics["dark_text_score"],
                result.metrics["dark_text_score_threshold"],
            )

    def test_lower_blue_cabinets_do_not_fail_real_estate_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blue_cabinets.png"
            image = Image.new("RGB", (360, 540), "#f4f1ea")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 340, 360, 540), fill="#16324f")
            draw.rectangle((25, 375, 150, 500), outline="#0a2038", width=6)
            draw.rectangle((195, 375, 320, 500), outline="#0a2038", width=6)
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="real_estate")

            self.assertTrue(result.passed)

    def test_small_real_estate_wall_sign_fails_sign_block_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wall_sign.png"
            image = Image.new("RGB", (360, 540), "#f4f1ea")
            draw = ImageDraw.Draw(image)
            draw.rectangle((145, 120, 220, 138), fill="#0b2d66")
            draw.rectangle((145, 142, 220, 174), fill="#b81f1f")
            image.save(path)

            result = evaluate_background_image(image_path=path, business_kind="real_estate")

            self.assertFalse(result.passed)
            self.assertIn("possible_background_text", result.reasons)
            self.assertGreater(
                result.metrics["sign_block_score"],
                result.metrics["sign_block_score_threshold"],
            )

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
