from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "codex-personal-assistant-starter"
ASSETS = PLUGIN / "assets" / "starter-workspace"
BOOTSTRAP = PLUGIN / "scripts" / "bootstrap_personal_assistant.py"
GIT = shutil.which("git") or "/usr/bin/git"
TAR = shutil.which("tar") or "/usr/bin/tar"


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, env=env)


class PersonalAssistantV02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def bootstrap(self, target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(sys.executable, str(BOOTSTRAP), "--target", str(target), *extra)

    def test_asset_bundle_lints_and_indexes(self) -> None:
        target = self.root / "workspace"
        shutil.copytree(ASSETS, target)
        bundle = target / ".codex" / "tools" / "knowledge_bundle.py"
        self.assertEqual(run(sys.executable, str(bundle), "--root", str(target), "lint").returncode, 0)
        self.assertEqual(run(sys.executable, str(bundle), "--root", str(target), "index").returncode, 0)

    def test_new_nonempty_folder_stages_only_managed_files(self) -> None:
        target = self.root / "workspace"
        target.mkdir()
        (target / "private-notes.txt").write_text("do not stage", encoding="utf-8")
        result = self.bootstrap(target)
        self.assertEqual(result.returncode, 0, result.stderr)
        committed = run(GIT, "-C", str(target), "show", "--format=", "--name-only", "HEAD").stdout.splitlines()
        self.assertNotIn("private-notes.txt", committed)
        self.assertIn("?? private-notes.txt", run(GIT, "-C", str(target), "status", "--short").stdout)

    def test_parent_repository_is_refused(self) -> None:
        parent = self.root / "parent"
        parent.mkdir()
        self.assertEqual(run(GIT, "-C", str(parent), "init").returncode, 0)
        result = self.bootstrap(parent / "nested")
        self.assertEqual(result.returncode, 2)
        self.assertIn("parent repository", result.stderr)

    def test_checkpoint_rejects_unrelated_staged_file(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        (target / "unrelated.txt").write_text("not memory", encoding="utf-8")
        self.assertEqual(run(GIT, "-C", str(target), "add", "unrelated.txt").returncode, 0)
        checkpoint = target / ".codex" / "tools" / "checkpoint.py"
        result = run(sys.executable, str(checkpoint))
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrelated files", result.stderr)

    def test_checkpoint_commits_valid_knowledge_without_remote(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        concept = target / "knowledge" / "people" / "example.md"
        concept.parent.mkdir()
        concept.write_text(
            "---\n"
            "type: \"Person\"\n"
            "title: \"Example Person\"\n"
            "description: \"A test-only concept for checkpoint validation.\"\n"
            "status: \"active\"\n"
            "generated: {\"at\": \"2026-08-02T00:00:00Z\", \"by\": \"test\"}\n"
            "sources: [{\"resource\": \"test://fixture\"}]\n"
            "tags: [\"test\"]\n"
            "---\n# Example Person\n",
            encoding="utf-8",
        )
        bundle = target / ".codex" / "tools" / "knowledge_bundle.py"
        self.assertEqual(run(sys.executable, str(bundle), "--root", str(target), "index").returncode, 0)
        checkpoint = run(GIT, "-C", str(target), "pa-checkpoint")
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr)
        self.assertIn("Checkpoint committed locally", checkpoint.stdout)
        self.assertEqual(run(GIT, "-C", str(target), "remote").stdout, "")
        self.assertIn("knowledge/people/example.md", run(GIT, "-C", str(target), "show", "--format=", "--name-only", "HEAD").stdout)

    def test_upgrade_preserves_modified_file_and_writes_candidate(self) -> None:
        target = self.root / "workspace"
        target.mkdir()
        # Use the tracked 0.1 content as the starting point, then make one user edit.
        old = subprocess.run(
            [GIT, "archive", "HEAD:plugins/codex-personal-assistant-starter/assets/starter-workspace"], capture_output=True
        )
        self.assertEqual(old.returncode, 0)
        extract = subprocess.run([TAR, "-x", "-C", str(target)], input=old.stdout, capture_output=True)
        self.assertEqual(extract.returncode, 0)
        original = target / "AGENTS.md"
        original.write_text(original.read_text(encoding="utf-8") + "\nUser addition.\n", encoding="utf-8")
        result = self.bootstrap(target, "--upgrade")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("User addition.", original.read_text(encoding="utf-8"))
        self.assertTrue((target / "archive" / "upgrade-review" / "v0.2.0" / "AGENTS.md.incoming").exists())

    def test_missing_identity_leaves_initialized_workspace(self) -> None:
        target = self.root / "workspace"
        home = self.root / "empty-home"
        home.mkdir()
        env = os.environ.copy()
        env.update({"HOME": str(home), "XDG_CONFIG_HOME": str(home / "config"), "GIT_CONFIG_NOSYSTEM": "1"})
        result = run(sys.executable, str(BOOTSTRAP), "--target", str(target), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / ".git").exists())
        self.assertIn("Setup is incomplete", result.stdout)


if __name__ == "__main__":
    unittest.main()
