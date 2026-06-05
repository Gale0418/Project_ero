import base64
import json
import unittest
from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image
from requests.exceptions import ReadTimeout

from core.client import SDClient
from core.utils import save_image
from main import get_next_draft_batch, wait_for_futures


class SDClientTests(unittest.TestCase):
    def test_http_errors_stop_after_configured_attempts(self):
        response = Mock(status_code=500, text="bad request")
        client = SDClient(max_retries=2, retry_delay=0)

        with patch("core.client.requests.post", return_value=response) as post:
            with patch("core.client.OtakuSpinner", side_effect=lambda *_: nullcontext()):
                with self.assertRaisesRegex(RuntimeError, "after 2 attempts"):
                    client._post_with_retry("http://example.invalid", {})

        self.assertEqual(post.call_count, 2)

    def test_read_timeout_is_not_retried(self):
        client = SDClient(max_retries=3, retry_delay=0)

        with patch("core.client.requests.post", side_effect=ReadTimeout) as post:
            with self.assertRaisesRegex(RuntimeError, "may still be running"):
                client._post_with_retry("http://example.invalid", {})

        self.assertEqual(post.call_count, 1)

    def test_connection_check_requires_success_response(self):
        client = SDClient()

        with patch("core.client.requests.get", return_value=Mock(ok=False)):
            self.assertFalse(client.check_connection())

    def test_missing_controlnet_model_stops_before_generation(self):
        client = SDClient()

        with patch.object(client, "find_controlnet_model", return_value=None):
            with patch.object(client, "_post_with_retry") as post:
                with self.assertRaisesRegex(ValueError, "ControlNet model not found"):
                    client.img2img("image", "prompt", controlnet_name="missing")

        post.assert_not_called()

    def test_txt2img_controlnet_uses_pose_without_img2img_init_image(self):
        client = SDClient()

        with patch.object(client, "find_controlnet_model", return_value="xinsir-openpose"):
            with patch.object(client, "_post_with_retry", return_value={"images": []}) as post:
                client.txt2img("prompt", controlnet_name="xinsir", controlnet_img="pose-image")

        url, payload = post.call_args.args
        self.assertTrue(url.endswith("/txt2img"))
        self.assertNotIn("init_images", payload)
        self.assertEqual(payload["alwayson_scripts"]["ControlNet"]["args"][0]["image"], "pose-image")

    def test_model_switch_has_timeout(self):
        response = Mock()
        response.raise_for_status.return_value = None
        client = SDClient(model_timeout=0)

        with patch.object(client, "get_options", return_value={"sd_model_checkpoint": "old"}):
            with patch("core.client.requests.post", return_value=response):
                self.assertFalse(client.set_model("new"))


class SaveSynchronizationTests(unittest.TestCase):
    def test_wait_for_futures_observes_each_save(self):
        first = Mock()
        second = Mock()

        wait_for_futures([first, second])

        first.result.assert_called_once_with()
        second.result.assert_called_once_with()

    def test_resume_generates_missing_draft_before_existing_file(self):
        draft_root = Path("draft")
        with patch.object(Path, "exists", autospec=True, side_effect=lambda path: path.name == "scene_002.png"):
            self.assertEqual(get_next_draft_batch(draft_root, "scene", 0, 3, 3), 1)
            self.assertEqual(get_next_draft_batch(draft_root, "scene", 1, 3, 3), 0)

    def test_saved_png_keeps_generation_parameters(self):
        source = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(source, format="PNG")
        image_b64 = base64.b64encode(source.getvalue()).decode()

        output_path = Path.cwd() / "outputs" / "metadata-test.png"
        try:
            save_image(image_b64, output_path, "Steps: 20, Seed: 123456")

            with Image.open(output_path) as image:
                self.assertEqual(image.info["parameters"], "Steps: 20, Seed: 123456")
        finally:
            output_path.unlink(missing_ok=True)

    def test_save_failure_is_not_silently_ignored(self):
        output_path = Path.cwd() / "outputs" / "invalid-image.png"

        with self.assertRaises(Exception):
            save_image("not-base64", output_path)


class StoryConfigurationTests(unittest.TestCase):
    def test_paid_release_baseline_avoids_unverified_models_and_loras(self):
        story_path = Path(__file__).resolve().parent.parent / "data" / "story.json"
        story = json.loads(story_path.read_text(encoding="utf-8"))
        final_model = story["models"]["final_model"].lower()

        self.assertNotIn("noob", final_model)
        self.assertNotIn("pony", final_model)
        self.assertEqual(story["story_refine_mode"], "controlnet_txt2img")
        self.assertEqual(story["draft_loras"], [])
        self.assertEqual(story["final_loras"], [])
        self.assertEqual(story["generation_settings"]["draft_cfg"], 5.0)
        self.assertEqual(story["generation_settings"]["final_cfg"], 5.0)


if __name__ == "__main__":
    unittest.main()
