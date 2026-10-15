"""Repository contracts, not security certification or real-network validation."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repository_checks", ROOT / "check.py")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class RepositoryChecks(unittest.TestCase):
    def test_source_syntax(self):
        self.assertEqual(checks.check_sources(), [])

    def test_local_documentation_links(self):
        self.assertEqual(checks.check_links(), [])

    def test_link_checker_reports_missing_and_outside_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text(
                "[bad](missing.md) [escape](../outside.md)", encoding="utf-8"
            )
            self.assertEqual(len(checks.check_links(root)), 2)

    def test_link_checker_skips_external_links_and_anchors(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text(
                "[web](https://example.invalid/page) [heading](#local)", encoding="utf-8"
            )
            self.assertEqual(checks.check_links(root), [])

    def test_syntax_checker_detects_invalid_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "check.py").write_text("def broken(\n", encoding="utf-8")
            self.assertEqual(len(checks.check_sources(root)), 1)

    def test_stage12_import_boundary_ast(self):
        # Narrow regression alarm. Does not prove non-execution or prevent all bypasses.
        allowed = {"json", "math", "re", "dataclasses", "typing", "telemetry"}
        for name in ("tcstats.py", "dryrun.py"):
            tree = ast.parse((ROOT / "src" / "leanbridge" / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [(node.module or "").split(".")[0]]
                else:
                    continue
                self.assertTrue(set(modules) <= allowed, (name, modules))

    def test_stage12_no_direct_execution_builtins(self):
        forbidden = {"eval", "exec", "compile", "__import__", "open"}
        for name in ("tcstats.py", "dryrun.py"):
            tree = ast.parse((ROOT / "src" / "leanbridge" / name).read_text())
            calls = {n.func.id for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertFalse(calls & forbidden, (name, calls & forbidden))

    def test_historical_evidence_bytes_unchanged(self):
        # Changes to these records require an explicit evidence/provenance review.
        expected = EVIDENCE_HASHES
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest,
                             relative)


EVIDENCE_HASHES = {'docs/FINDINGS.md': '03726f03746790f7a4ac44adca22e0fdbcbb699ba439e939eaec07d2c9a58d39', 'docs/MANIFEST_v0.3.json': 'cf0a465d0380d44fb37a29d2483fc0c54c8416cf09e768e89e447e7b2ddd6b8f', 'docs/results_v0.3.json': '16d71458e3e741bd001fe24652a140b7eb98722c9bbcdc84c79bbd6a03a7b429'}
