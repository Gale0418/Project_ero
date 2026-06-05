import re
import unittest
from pathlib import Path

from webui.job_history import normalize_loaded_job


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEBUI_ROOT = PROJECT_ROOT / "webui"
STATIC_ROOT = WEBUI_ROOT / "static"


class WebUIHardeningTests(unittest.TestCase):
    def read_text(self, path):
        return path.read_text(encoding="utf-8")

    def test_backend_and_frontend_versions_match_v21(self):
        app_py = self.read_text(WEBUI_ROOT / "app.py")
        index_html = self.read_text(STATIC_ROOT / "index.html")

        self.assertIn('APP_VERSION = "v2.1"', app_py)
        self.assertIn("Project Ero - WebUI v2.1", index_html)
        self.assertIn("PROJECT ERO WEBUI v2.1", index_html)

    def test_job_card_dynamic_content_is_escaped_before_inner_html(self):
        main_js = self.read_text(STATIC_ROOT / "js" / "main.js")

        self.assertIn("function escapeHtml", main_js)
        self.assertIn("function jsArg", main_js)
        self.assertRegex(main_js, r"const safeTaskName\s*=\s*escapeHtml\(taskName\)")
        self.assertRegex(main_js, r"const safePromptText\s*=\s*escapeHtml\(promptText\)")
        self.assertRegex(main_js, r"const safeError\s*=\s*escapeHtml\(")
        self.assertIn('onclick="deleteJob(${jobArg})"', main_js)
        self.assertIn('onclick="openModal(${urlArg})"', main_js)
        self.assertNotIn("${taskName} #${job.id}", main_js)
        self.assertNotIn('title="${promptText}">${promptText}', main_js)

    def test_launchers_bind_localhost_by_default_with_env_override(self):
        app_py = self.read_text(WEBUI_ROOT / "app.py")
        start_ps1 = self.read_text(PROJECT_ROOT / "start_webui.ps1")
        start_bat = self.read_text(PROJECT_ROOT / "start_webui.bat")

        self.assertIn('os.getenv("PROJECT_ERO_HOST", "127.0.0.1")', app_py)
        self.assertIn('"127.0.0.1"', start_ps1)
        self.assertIn("PROJECT_ERO_HOST=127.0.0.1", start_bat)

    def test_danger_color_alias_is_defined_for_action_buttons(self):
        style_css = self.read_text(STATIC_ROOT / "css" / "style.css")

        self.assertRegex(style_css, r"--danger-color:\s*var\(--error-color\);")

    def test_interrupted_history_jobs_are_marked_failed_on_load(self):
        for status in ("Pending", "Running", "Canceling"):
            with self.subTest(status=status):
                job, changed = normalize_loaded_job({
                    "id": "abc123",
                    "status": status,
                    "phase_text": "old phase",
                    "error": None,
                })

                self.assertTrue(changed)
                self.assertEqual(job["status"], "Failed")
                self.assertEqual(job["phase_text"], "")
                self.assertEqual(job["error"], "Server restarted before completion")

        completed, changed = normalize_loaded_job({
            "id": "done123",
            "status": "Completed",
            "phase_text": "",
            "error": None,
        })

        self.assertFalse(changed)
        self.assertEqual(completed["status"], "Completed")


if __name__ == "__main__":
    unittest.main()
