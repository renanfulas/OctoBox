"""Static checks that versioned HostGator timers are classified in the F2 runbook."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYSTEMD_DIR = ROOT / "infra" / "hostgator-vps" / "systemd"
RUNBOOK = ROOT / "docs" / "rollout" / "restore-and-rollback-drill.md"


class TenantRestoreTimerInventoryTests(unittest.TestCase):
    def test_every_versioned_timer_is_paused_or_explicitly_exempted(self):
        runbook = RUNBOOK.read_text(encoding="utf-8")
        stop_start = runbook.index("systemctl stop octobox-nightly-lead-imports.timer")
        stop_end = runbook.index("systemctl list-timers --all", stop_start)
        stop_commands = runbook[stop_start:stop_end]
        paused = set(re.findall(r"octobox-[a-z0-9-]+\.timer", stop_commands))
        exempted = {"octobox-env-backup.timer"}
        versioned = {path.name for path in SYSTEMD_DIR.glob("*.timer")}

        self.assertIn("octobox-env-backup.timer", runbook)
        # The restore branch may carry a newer runbook than the staged code
        # stack (some tenant writers arrive in P01/P07). Every unit versioned
        # by this branch must be classified, while the runbook can also name
        # additional units already installed by a later deployment.
        self.assertLessEqual(versioned, paused | exempted)

    def test_application_jobs_and_healthcheck_use_application_identity(self):
        services = {
            "octobox-nightly-lead-imports.service",
            "octobox-public-workout-metrics.service",
            "octobox-public-workout-notices.service",
            "octobox-public-workout-operations.service",
            "octobox-public-workout-outbox.service",
            "octobox-runtime-check.service",
            "octobox-signal-mesh-retries.service",
        }
        for name in sorted(services):
            with self.subTest(service=name):
                service = (SYSTEMD_DIR / name).read_text(encoding="utf-8")
                self.assertRegex(service, r"(?m)^User=octobox$")
                self.assertRegex(service, r"(?m)^Group=octobox$")
                self.assertRegex(service, r"(?m)^UMask=0077$")

    def test_runtime_check_script_does_not_require_root(self):
        script = (ROOT / "scripts" / "linux" / "check_octobox_runtime.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Execute como root.", script)

    def test_backup_status_file_umask_allows_runtime_check_read(self):
        service = (SYSTEMD_DIR / "octobox-backup.service").read_text(encoding="utf-8")
        self.assertRegex(service, r"(?m)^User=root$")
        self.assertRegex(service, r"(?m)^Group=octobox$")
        self.assertRegex(service, r"(?m)^UMask=0027$")


if __name__ == "__main__":
    unittest.main()
