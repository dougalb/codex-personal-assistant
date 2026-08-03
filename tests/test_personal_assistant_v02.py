from __future__ import annotations

import os
import json
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


class PersonalAssistantV03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def bootstrap(self, target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(sys.executable, str(BOOTSTRAP), "--target", str(target), *extra)

    def bundle(self, target: Path) -> Path:
        return target / ".codex" / "tools" / "knowledge_bundle.py"

    def write_concept(self, target: Path, name: str = "example", memory: dict | None = None, extra: str = "") -> Path:
        concept = target / "knowledge" / "people" / f"{name}.md"
        concept.parent.mkdir(parents=True, exist_ok=True)
        memory = memory or {
            "subject": {"kind": "third_party", "id": "example-person"},
            "class": "role_fact",
            "purpose": ["meeting_prep"],
            "evidence_kind": "direct_source",
            "confidence": "high",
            "sensitivity": "standard",
            "retention": {"review_at": "2027-02-01", "expires_at": "2027-02-01"},
            "approval": {"status": "not_required"},
        }
        concept.write_text(
            "---\n"
            "type: \"Person\"\n"
            "title: \"Example Person\"\n"
            "description: \"A test-only concept for checkpoint validation.\"\n"
            "status: \"active\"\n"
            "generated: {\"at\": \"2026-08-02T00:00:00Z\", \"by\": \"test\"}\n"
            "sources: [{\"resource\": \"test://fixture\"}]\n"
            f"memory: {json.dumps(memory, sort_keys=True)}\n"
            "tags: [\"test\"]\n"
            "---\n# Example Person\n"
            + extra,
            encoding="utf-8",
        )
        return concept

    def test_asset_bundle_lints_and_indexes(self) -> None:
        target = self.root / "workspace"
        shutil.copytree(ASSETS, target)
        bundle = self.bundle(target)
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
        self.write_concept(target)
        bundle = self.bundle(target)
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
        self.assertTrue((target / "archive" / "upgrade-review" / "v0.3.0" / "AGENTS.md.incoming").exists())
        self.assertTrue((target / "context" / "data-policy.md").exists())

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

    def test_missing_memory_is_rejected(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        concept = self.write_concept(target)
        text = concept.read_text(encoding="utf-8")
        concept.write_text(text.replace('memory: {"approval"', 'legacy_memory: {"approval"'), encoding="utf-8")
        result = run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required `memory` object", result.stdout)

    def test_behavioral_inference_requires_direct_source(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        memory = {
            "subject": {"kind": "third_party", "id": "example-person"},
            "class": "behavioral_inference",
            "purpose": ["relationship_context"],
            "evidence_kind": "user_statement",
            "confidence": "medium",
            "sensitivity": "standard",
            "retention": {"review_at": "2027-02-01", "expires_at": "2027-02-01"},
            "approval": {"status": "not_required"},
        }
        self.write_concept(target, memory=memory)
        result = run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("behavioral inferences require", result.stdout)

    def test_sensitive_memory_requires_human_approval(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        memory = {
            "subject": {"kind": "third_party", "id": "example-person"},
            "class": "sensitive_fact",
            "purpose": ["relationship_context"],
            "evidence_kind": "direct_source",
            "confidence": "high",
            "sensitivity": "sensitive",
            "retention": {"review_at": "2026-09-01", "expires_at": "2026-09-01"},
            "approval": {"status": "pending", "proposal_id": "proposal-1"},
        }
        self.write_concept(target, memory=memory)
        result = run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive memory requires", result.stdout)

    def test_sensitive_memory_approval_must_match_ledger(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        memory = {
            "subject": {"kind": "third_party", "id": "example-person"},
            "class": "sensitive_fact",
            "purpose": ["relationship_context"],
            "evidence_kind": "direct_source",
            "confidence": "high",
            "sensitivity": "sensitive",
            "retention": {"review_at": "2026-09-01", "expires_at": "2026-09-01"},
            "approval": {"status": "approved", "proposal_id": "proposal-1", "by": "human:test", "at": "2026-08-02T00:00:00Z"},
        }
        self.write_concept(target, memory=memory)
        result = run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("matching record", result.stdout)
        (target / "state" / "memory-approvals.json").write_text(json.dumps({"schema_version": "0.3", "approvals": [{"proposal_id": "proposal-1", "status": "approved", "by": "human:test", "at": "2026-08-02T00:00:00Z"}]}) + "\n", encoding="utf-8")
        self.assertEqual(run(sys.executable, str(self.bundle(target)), "--root", str(target), "index").returncode, 0)
        self.assertEqual(run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint").returncode, 0)

    def test_attention_rollup_enforces_cold_start_and_guardrails(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        bundle = self.bundle(target)
        for _ in range(2):
            result = run(sys.executable, str(bundle), "--root", str(target), "record-attention", "--memory-id", "knowledge/example", "--action", "surface", "--importance", "important", "--outcome", "accepted")
            self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((target / "state" / "attention-calibration.json").read_text(encoding="utf-8"))
        self.assertFalse(state["metrics"]["tuning_eligible"])
        self.assertEqual(state["metrics"]["interruptions"], 2)

    def test_v02_migration_quarantines_unclassified_concepts(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        checkpoint = target / "state" / "knowledge-checkpoint.json"
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        state["schema_version"] = "0.2"
        state.pop("memory_schema_version", None)
        checkpoint.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        concept = self.write_concept(target)
        text = concept.read_text(encoding="utf-8")
        start = text.index("memory: ")
        end = text.index("\ntags:", start)
        concept.write_text(text[:start] + text[end + 1 :], encoding="utf-8")
        result = run(sys.executable, str(self.bundle(target)), "--root", str(target), "migrate", "--from", "0.2")
        self.assertEqual(result.returncode, 0, result.stderr)
        migrated = concept.read_text(encoding="utf-8")
        self.assertIn('"class": "unclassified"', migrated)
        self.assertIn('status: "draft"', migrated)
        # The migrated concept is valid but excluded from normal retrieval until reviewed.
        lint = run(sys.executable, str(self.bundle(target)), "--root", str(target), "lint")
        self.assertEqual(lint.returncode, 0, lint.stdout)

    def test_expire_removes_active_copy_but_keeps_git_history(self) -> None:
        target = self.root / "workspace"
        self.assertEqual(self.bootstrap(target).returncode, 0)
        memory = {
            "subject": {"kind": "third_party", "id": "example-person"},
            "class": "commitment",
            "purpose": ["briefing"],
            "evidence_kind": "direct_source",
            "confidence": "high",
            "sensitivity": "standard",
            "retention": {"review_at": "2026-08-01", "expires_at": "2026-08-01"},
            "approval": {"status": "not_required"},
        }
        concept = self.write_concept(target, memory=memory)
        bundle = self.bundle(target)
        self.assertEqual(run(sys.executable, str(bundle), "--root", str(target), "index").returncode, 0)
        self.assertEqual(run(GIT, "-C", str(target), "pa-checkpoint").returncode, 0)
        result = run(sys.executable, str(bundle), "--root", str(target), "expire", "--as-of", "2026-08-02")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(concept.exists())
        self.assertNotIn("Example Person", (target / "knowledge" / "log.md").read_text(encoding="utf-8"))
        historical = run(GIT, "-C", str(target), "show", f"HEAD:{concept.relative_to(target)}")
        self.assertEqual(historical.returncode, 0)


if __name__ == "__main__":
    unittest.main()
