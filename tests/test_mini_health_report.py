"""Heartbeat policy, credential handling, and loopback HTTP contract tests."""

from contextlib import redirect_stdout
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "mini_health_report", Path(__file__).resolve().parents[1] / "scripts" / "mini-health-report.py",
)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
URL = "https://hc-ping.com/11111111-2222-4333-8444-555555555555"


class ReporterTests(unittest.TestCase):
    def run_report(self, exit_code=0, credential=URL):
        with tempfile.TemporaryDirectory() as directory:
            if credential is not None:
                (Path(directory) / "healthchecks-url").write_text(credential)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": directory}), \
                 patch.object(report.subprocess, "run", return_value=subprocess.CompletedProcess([], exit_code)), \
                 patch.object(report, "send_heartbeat", return_value=True) as send, \
                 redirect_stdout(io.StringIO()) as output:
                result = report.run_and_report("/checker")
                return result, output.getvalue(), send.call_args_list

    def test_only_passing_checks_send_a_heartbeat(self):
        for status in (1, 2, -15):
            with self.subTest(status=status):
                result, output, calls = self.run_report(status)
                self.assertNotEqual(result, 0)
                self.assertEqual(calls, [])
                self.assertNotIn(URL, output)
        result, output, calls = self.run_report()
        self.assertEqual(result, 0)
        self.assertEqual(calls[0].args, (URL,))
        self.assertNotIn(URL, output)

    def test_disabled_or_empty_default_keeps_local_checks_working(self):
        for value in ("disabled", ""):
            with self.subTest(value=value):
                result, output, calls = self.run_report(credential=value)
                self.assertEqual(result, 0)
                self.assertIn("not configured", output)
                self.assertEqual(calls, [])

    def test_missing_or_invalid_credential_fails_without_disclosure(self):
        for value in (None, URL + "/fail", "private-invalid-secret"):
            with self.subTest(value=value):
                result, output, calls = self.run_report(credential=value)
                self.assertEqual(result, 1)
                self.assertEqual(calls, [])
                self.assertNotIn(URL, output)
                self.assertNotIn("private-invalid-secret", output)

    def test_only_success_uuid_urls_are_accepted(self):
        self.assertTrue(report.valid_ping_url(URL))
        for value in (URL.replace("https:", "http:"), URL + "/start", URL + "/0",
                      URL + "?data=secret", URL + "#secret", URL.replace("hc-ping.com", "example.org"),
                      URL.replace("hc-ping.com", "user:secret@hc-ping.com")):
            with self.subTest(value=value):
                self.assertFalse(report.valid_ping_url(value))

    def test_delivery_failure_is_redacted_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "healthchecks-url").write_text(URL)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": directory}), \
                 patch.object(report.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                 patch.object(report, "send_heartbeat", return_value=False), \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(report.run_and_report("/checker"), 1)
                self.assertIn("delivery failed", output.getvalue())
                self.assertNotIn(URL, output.getvalue())

    def test_checker_cannot_start(self):
        with patch.object(report.subprocess, "run", side_effect=FileNotFoundError()), \
             patch.object(report, "send_heartbeat") as send, redirect_stdout(io.StringIO()):
            self.assertEqual(report.run_and_report("/missing-checker"), 2)
            send.assert_not_called()

    def test_network_errors_are_bounded_and_redacted(self):
        with patch.object(report.urllib.request, "build_opener") as build, \
             patch.object(report.time, "sleep") as sleep, redirect_stdout(io.StringIO()) as output:
            build.return_value.open.side_effect = report.urllib.error.URLError(URL)
            self.assertFalse(report.send_heartbeat(URL))
            self.assertEqual(build.return_value.open.call_count, 2)
            self.assertEqual(build.return_value.open.call_args.kwargs["timeout"], 5)
            sleep.assert_called_once_with(1)
            self.assertNotIn(URL, output.getvalue())

    def test_empty_post_retry_and_no_redirect_using_loopback(self):
        for statuses, expected in (((200,), True), ((503, 200), True), ((302, 302), False)):
            requests = []
            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    requests.append((self.command, self.path, self.rfile.read(int(self.headers["Content-Length"]))))
                    self.send_response(statuses[min(len(requests) - 1, len(statuses) - 1)])
                    self.send_header("Location", "http://127.0.0.1:1/must-not-follow")
                    self.end_headers()

                def log_message(self, *args):
                    pass

            with self.subTest(statuses=statuses), ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    with patch.object(report.time, "sleep"):
                        # Exercise transport locally; the production caller
                        # separately enforces HTTPS and the hosted UUID URL.
                        self.assertEqual(report.send_heartbeat(f"http://127.0.0.1:{server.server_port}/token"), expected)
                    self.assertEqual(len(requests), len(statuses))
                    self.assertTrue(all(item == ("POST", "/token", b"") for item in requests))
                finally:
                    server.shutdown()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
