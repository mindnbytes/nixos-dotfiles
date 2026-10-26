"""Failure-oriented tests; no access to the real server or its disks."""

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "mini_health", Path(__file__).resolve().parents[1] / "scripts" / "mini-health.py",
)
health = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = health
spec.loader.exec_module(health)


def response(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class HealthTests(unittest.TestCase):
    def test_inactive_and_missing_services_fail(self):
        for load, active, sub in (("loaded", "inactive", "dead"),
                                  ("not-found", "inactive", "dead"),
                                  ("loaded", "activating", "start")):
            with self.subTest(load=load, active=active), patch.object(
                health, "run", return_value=response(
                    f"LoadState={load}\nActiveState={active}\nSubState={sub}\n"),
            ):
                self.assertEqual(health.check_service("caddy").status, "FAIL")

    def test_incomplete_service_evidence_is_unknown(self):
        with patch.object(health, "run", return_value=response("ActiveState=active\n")):
            with self.assertRaises(health.Unavailable):
                health.check_service("caddy")

    def test_http_requires_pong_and_status_200(self):
        for output, expected in (( '{"res":"pong"}\n200', "PASS"),
                                 ('<html>login</html>\n200', "FAIL"),
                                 ('{"res":"pong"}\n502', "FAIL"),
                                 ('{}\n200', "FAIL")):
            with self.subTest(output=output), patch.object(health, "run", return_value=response(output)) as run:
                self.assertEqual(health.check_immich().status, expected)
                command = run.call_args.args[0]
                self.assertIn("Host: immich.home.arpa", command)
                self.assertIn("http://127.0.0.1/api/server/ping", command)

    def test_http_connection_failure(self):
        with patch.object(health, "run", return_value=response(returncode=7, stderr="connection refused")):
            self.assertEqual(health.check_immich().status, "FAIL")

    def storage(self, source="/dev/sdb1", actual="/dev/sdb1", free=20,
                options="rw,relatime", automount=False):
        mounts = [{"target": "/mnt/backup", "source": source, "fstype": "ext4", "options": options}]
        if automount:
            mounts.insert(0, {"target": "/mnt/backup", "source": "systemd-1", "fstype": "autofs"})
        return [response(f"{free} 100 4096"), response(json.dumps({"filesystems": mounts})),
                response("/dev/sdb1\n"), response(actual + "\n")]

    def test_wrong_disk_fails_even_with_plenty_of_space(self):
        with patch.object(health, "run", side_effect=self.storage(actual="/dev/sdc1")):
            result = health.check_storage("/mnt/backup", "backup-hdd", 15)
            self.assertEqual(result.status, "FAIL")
            self.assertIn("expected disk labeled backup-hdd", result.detail)

    def test_automount_and_low_space(self):
        with patch.object(health, "run", side_effect=self.storage(free=10, automount=True)) as run:
            self.assertEqual(health.check_storage("/mnt/backup", "backup-hdd", 15).status, "WARN")
            self.assertEqual(run.call_args_list[0].kwargs["timeout"], 70)

    def test_read_only_disk_fails(self):
        with patch.object(health, "run", side_effect=self.storage(options="ro,relatime")):
            self.assertEqual(health.check_storage("/mnt/backup", "backup-hdd", 15).status, "FAIL")

    def test_missing_exact_mount_fails(self):
        with patch.object(health, "run", side_effect=[response("20 100 4096"), response(returncode=1)]):
            self.assertEqual(health.check_storage("/srv", "services", 15).status, "FAIL")

    def test_failed_units_are_reported(self):
        with patch.object(health, "run", return_value=response("broken.service loaded failed failed Broken\n")):
            result = health.check_failed_units()
            self.assertEqual(result.status, "FAIL")
            self.assertIn("broken.service", result.detail)

    def test_missing_command_and_timeout_are_unavailable(self):
        for error in (FileNotFoundError("missing command"), subprocess.TimeoutExpired(["stat"], 10)):
            with self.subTest(error=error), patch.object(health.subprocess, "run", side_effect=error):
                with self.assertRaises(health.Unavailable):
                    health.run(["stat"])

    def test_unknown_check_does_not_prevent_other_checks(self):
        with patch.object(health, "check_service", side_effect=health.Unavailable("timed out")), \
             patch.object(health, "check_immich", return_value=health.Result("PASS", "http/immich", "pong")), \
             patch.object(health, "check_storage", side_effect=health.Unavailable("missing tool")), \
             patch.object(health, "check_failed_units", return_value=health.Result("PASS", "os/failed-units", "none")):
            results = health.collect(15)
        self.assertEqual(len(results), 13)
        self.assertEqual(results[0].status, "UNKNOWN")
        self.assertEqual(results[-1].status, "PASS")

    def test_json_report_and_exit_status(self):
        for status, exit_code in (("PASS", 0), ("WARN", 1), ("FAIL", 1), ("UNKNOWN", 1)):
            with self.subTest(status=status), \
                 patch.object(sys, "argv", ["mini-health", "--json"]), \
                 patch.object(health.platform, "system", return_value="Linux"), \
                 patch.object(health, "collect", return_value=[health.Result(status, "example", "evidence")]), \
                 patch.object(sys, "stdout", new_callable=io.StringIO) as output:
                self.assertEqual(health.main(), exit_code)
                report = json.loads(output.getvalue())
                self.assertEqual(report["healthy"], status == "PASS")
                self.assertEqual(report["results"][0]["status"], status)

    def test_non_linux_does_not_run_checks(self):
        with patch.object(sys, "argv", ["mini-health"]), \
             patch.object(health.platform, "system", return_value="Darwin"), \
             patch.object(health, "collect") as collect, \
             patch.object(sys, "stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as error:
                health.main()
            self.assertEqual(error.exception.code, 2)
            collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
