"""Failure-oriented tests; no access to the real server or its disks."""

import importlib.util
import io
from datetime import datetime, timezone
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
             patch.object(health, "check_failed_units", return_value=health.Result("PASS", "os/failed-units", "none")), \
             patch.object(health, "check_backup_timer", side_effect=health.Unavailable("missing timer")), \
             patch.object(health, "check_backup_run", side_effect=health.Unavailable("missing service")), \
             patch.object(health, "check_backup_freshness", side_effect=health.Unavailable("permission denied")):
            results = health.collect(15)
        self.assertEqual(len(results), 19)
        self.assertEqual(results[0].status, "UNKNOWN")
        self.assertEqual(results[12].status, "PASS")
        self.assertEqual(results[-1].status, "UNKNOWN")

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


class BackupTests(unittest.TestCase):
    now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)

    def test_timer_must_be_enabled_active_and_scheduled(self):
        base = dict(LoadState="loaded", ActiveState="active", UnitFileState="enabled",
                    NextElapseUSecRealtime="Mon 2026-10-26 15:00:00 CET")
        for changes, status in (({}, "PASS"), ({"LoadState": "not-found"}, "FAIL"),
                                ({"ActiveState": "inactive"}, "FAIL"),
                                ({"UnitFileState": "disabled"}, "FAIL"),
                                ({"NextElapseUSecRealtime": ""}, "FAIL"),
                                ({"NextElapseUSecRealtime": "n/a"}, "FAIL")):
            with self.subTest(changes=changes), patch.object(health, "backup_properties", return_value={**base, **changes}):
                self.assertEqual(health.check_backup_timer("mini-home").status, status)

    def test_completed_failed_running_and_unrecorded_runs(self):
        base = dict(LoadState="loaded", ActiveState="inactive", Result="success",
                    ExecMainStatus="0", ExecMainExitTimestamp="Mon 2026-10-26 03:00:46 CET")
        for changes, status in (({}, "PASS"), ({"Result": "exit-code", "ExecMainStatus": "2"}, "FAIL"),
                                ({"ExecMainStatus": "1"}, "FAIL"),
                                ({"ActiveState": "activating"}, "WARN"),
                                ({"LoadState": "not-found"}, "FAIL")):
            with self.subTest(changes=changes), patch.object(health, "backup_properties", return_value={**base, **changes}):
                self.assertEqual(health.check_backup_run("mini-home").status, status)
        with patch.object(health, "backup_properties", return_value={**base, "ExecMainExitTimestamp": ""}), \
             patch.object(health, "read_backup_history", side_effect=health.Unavailable("no history")):
            with self.assertRaises(health.Unavailable):
                health.check_backup_run("mini-home")

    def journal_run(self, completed="2026-10-26T03:00:46+01:00", invocation="run-1",
                    job="mini-home", success=True):
        stamp = int(datetime.fromisoformat(completed).timestamp() * 1_000_000)
        common = {"_SYSTEMD_UNIT": f"borgbackup-job-{job}.service",
                  "_SYSTEMD_INVOCATION_ID": invocation, "__REALTIME_TIMESTAMP": str(stamp - 1_000_000)}
        return [
            {**common, "MESSAGE": f"Archive name: {job}-2026-10-26.failed"},
            {**common, "MESSAGE": "Time (end): Mon, 2026-10-26 03:00:38"},
            {"UNIT": common["_SYSTEMD_UNIT"], "_PID": "1", "INVOCATION_ID": invocation,
             "__REALTIME_TIMESTAMP": str(stamp),
             "MESSAGE_ID": health.UNIT_SUCCESS if success else next(iter(health.UNIT_FAILURES)),
             "MESSAGE": "Deactivated successfully." if success else "Failed with result 'exit-code'."},
        ]

    def journal(self, entries=None):
        if entries is None:
            entries = self.journal_run()
        return response("\n".join(json.dumps(entry) for entry in entries))

    def test_fresh_stale_and_exact_boundary(self):
        for completed, status in (("2026-10-26T03:00:00+01:00", "PASS"),
                              ("2026-10-25T00:00:00+00:00", "PASS"),
                              ("2026-10-24T23:59:59+00:00", "WARN")):
            with self.subTest(completed=completed), patch.object(health, "run", return_value=self.journal(self.journal_run(completed))):
                result = health.check_backup_freshness("mini-home", 36, self.now)
                self.assertEqual(result.status, status)

    def test_custom_age_limit(self):
        with patch.object(health, "run", return_value=self.journal()):
            self.assertEqual(health.check_backup_freshness("mini-home", 8, self.now).status, "WARN")

    def test_missing_failed_incomplete_future_or_malformed_evidence_is_unknown(self):
        entries = self.journal_run()
        wrong_invocation = self.journal_run()
        wrong_invocation[-1]["INVOCATION_ID"] = "another-run"
        checkpoint = self.journal_run()
        checkpoint[0]["MESSAGE"] += ".checkpoint"
        for output in (self.journal([]), self.journal(entries[:-1]), self.journal(entries[1:]),
                       self.journal(wrong_invocation), self.journal(checkpoint),
                       self.journal(self.journal_run(success=False)),
                       self.journal(self.journal_run(job="mini-immich")),
                       self.journal(self.journal_run(completed="2026-10-27T03:00:00+01:00")),
                       response("not JSON"), response('{}'), response('[]')):
            with self.subTest(output=output.stdout), patch.object(health, "run", return_value=output):
                with self.assertRaises(health.Unavailable):
                    health.check_backup_freshness("mini-home", 36, self.now)

    def test_latest_success_survives_a_later_failure(self):
        entries = self.journal_run("2026-10-24T23:00:00+00:00", "old")
        entries += self.journal_run("2026-10-26T03:00:00+01:00", "recent")
        entries += self.journal_run("2026-10-26T10:00:00+01:00", "failed", success=False)
        # Newest successful completion wins, regardless of input ordering.
        with patch.object(health, "run", return_value=self.journal(list(reversed(entries)))):
            result = health.check_backup_freshness("mini-home", 36, self.now)
            self.assertEqual(result.status, "PASS")
            self.assertIn("age 10.0h", result.detail)

    def test_missing_runtime_record_uses_latest_journal_attempt(self):
        state = dict(LoadState="loaded", ActiveState="inactive", Result="success",
                     ExecMainStatus="0", ExecMainExitTimestamp="")
        old = self.journal_run("2026-10-25T00:00:00+00:00", "old")
        for success, expected in ((True, "PASS"), (False, "FAIL")):
            entries = old + self.journal_run("2026-10-26T03:00:00+01:00", "recent", success=success)
            with self.subTest(success=success), \
                 patch.object(health, "backup_properties", return_value=state), \
                 patch.object(health, "run", return_value=self.journal(list(reversed(entries)))):
                result = health.check_backup_run("mini-home", now=self.now)
                self.assertEqual(result.status, expected)
                self.assertIn("(journal)", result.detail)

    def test_later_failure_is_not_hidden_by_fresh_success_after_reboot(self):
        entries = self.journal_run("2026-10-26T03:00:00+01:00", "good")
        entries += self.journal_run("2026-10-26T10:00:00+01:00", "bad", success=False)
        state = dict(LoadState="loaded", ActiveState="inactive", Result="success",
                     ExecMainStatus="0", ExecMainExitTimestamp="")
        with patch.object(health, "run", return_value=self.journal(entries)):
            evidence = health.read_backup_history("mini-home")
        with patch.object(health, "backup_properties", return_value=state):
            self.assertEqual(health.check_backup_run("mini-home", history=lambda: evidence, now=self.now).status, "FAIL")
            self.assertEqual(health.check_backup_freshness("mini-home", 36, self.now, history=lambda: evidence).status, "PASS")

    def test_failure_before_borg_summary_or_invocation_is_still_a_failure(self):
        for event in health.UNIT_FAILURES:
            entry = self.journal_run(success=False)[-1]
            entry["MESSAGE_ID"] = event
            entry.pop("INVOCATION_ID")
            with self.subTest(event=event), patch.object(health, "run", return_value=self.journal([entry])):
                self.assertEqual(health.read_backup_history("mini-home")["latest_attempt"][1], "FAIL")

    def test_latest_incomplete_success_does_not_fall_back_to_older_success(self):
        entries = self.journal_run("2026-10-25T00:00:00+00:00", "old")
        entries += self.journal_run("2026-10-26T03:00:00+01:00", "incomplete")[-1:]
        state = dict(LoadState="loaded", ActiveState="inactive", Result="success",
                     ExecMainStatus="0", ExecMainExitTimestamp="")
        with patch.object(health, "backup_properties", return_value=state), \
             patch.object(health, "run", return_value=self.journal(entries)):
            with self.assertRaises(health.Unavailable):
                health.check_backup_run("mini-home", now=self.now)

    def test_current_failure_does_not_need_journal(self):
        state = dict(LoadState="loaded", ActiveState="failed", Result="exit-code",
                     ExecMainStatus="2", ExecMainExitTimestamp="")
        with patch.object(health, "backup_properties", return_value=state), \
             patch.object(health, "read_backup_history") as history:
            self.assertEqual(health.check_backup_run("mini-home").status, "FAIL")
            history.assert_not_called()

    def test_history_is_read_once_per_job_even_when_unavailable(self):
        state = dict(LoadState="loaded", ActiveState="inactive", Result="success",
                     ExecMainStatus="0", ExecMainExitTimestamp="")
        for unavailable in (False, True):
            with self.subTest(unavailable=unavailable), \
                 patch.object(health, "check_service"), patch.object(health, "check_immich"), \
                 patch.object(health, "check_storage"), patch.object(health, "check_failed_units"), \
                 patch.object(health, "check_backup_timer"), \
                 patch.object(health, "backup_properties", return_value=state), \
                 patch.object(health, "read_backup_history", return_value={
                     "latest_attempt": (self.now.timestamp(), "PASS"),
                     "latest_success": self.now.timestamp(), "lookback_hours": 168,
                 }, side_effect=health.Unavailable("unreadable") if unavailable else None) as history:
                health.collect(15)
                self.assertEqual(history.call_count, 2)

    def test_similar_text_without_structured_success_does_not_count(self):
        entries = self.journal_run()
        entries[-1].pop("MESSAGE_ID")
        with patch.object(health, "run", return_value=self.journal(entries)):
            with self.assertRaises(health.Unavailable):
                health.check_backup_freshness("mini-home", 36, self.now)

    def test_inaccessible_journal_is_unknown(self):
        with patch.object(health, "run", side_effect=health.Unavailable("Permission denied")):
            with self.assertRaises(health.Unavailable):
                health.check_backup_freshness("mini-home", 36, self.now)

    def test_uses_time_window_without_sudo_or_line_limit(self):
        with patch.object(health, "run", return_value=self.journal()) as run:
            health.check_backup_freshness("mini-home", 36, self.now)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "journalctl")
        self.assertIn("168 hours ago", command)
        self.assertIn("--output=json", command)
        self.assertNotIn("sudo", command)
        self.assertNotIn("-n", command)
        self.assertNotIn("--lines", command)

    def test_lookback_expands_for_custom_threshold(self):
        with patch.object(health, "run", return_value=self.journal()) as run:
            health.check_backup_freshness("mini-home", 240, self.now)
        self.assertIn("264 hours ago", run.call_args.args[0])

    def test_backup_unit_fields_are_required(self):
        with patch.object(health, "run", return_value=response("LoadState=loaded\n")):
            with self.assertRaises(health.Unavailable):
                health.check_backup_timer("mini-home")


if __name__ == "__main__":
    unittest.main()
