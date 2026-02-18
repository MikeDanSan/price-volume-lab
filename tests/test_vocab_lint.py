"""Tests for the VPA vocabulary lint script."""

import textwrap
from pathlib import Path

import pytest

from scripts.vpa_vocab_lint import scan


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


class TestRepoClean:
    """The repo itself must have zero vocabulary violations."""

    def test_zero_violations(self) -> None:
        violations = scan(_repo_root())
        if violations:
            msg_lines = [f"  {fp}:{ln}  [{term}]" for fp, ln, term, _ in violations]
            pytest.fail(
                f"Vocabulary lint found {len(violations)} violation(s):\n"
                + "\n".join(msg_lines)
            )


class TestScanLogic:
    """Unit tests for scan behavior with synthetic files."""

    def test_detects_blacklist_term(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("wyckoff\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("")
        (tmp_path / "bad.md").write_text("This uses Wyckoff methods.\n")

        violations = scan(tmp_path)
        assert len(violations) == 1
        assert violations[0][2] == "wyckoff"

    def test_exception_file_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("wyckoff\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("safe.md\n")
        (tmp_path / "safe.md").write_text("This uses Wyckoff methods.\n")

        violations = scan(tmp_path)
        assert len(violations) == 0

    def test_exception_matching_is_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("wyckoff\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("MY_DOC.md\n")
        (tmp_path / "my_doc.md").write_text("Wyckoff reference here.\n")

        violations = scan(tmp_path)
        assert len(violations) == 0

    def test_word_boundary_prevents_false_positive(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("ict\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("")
        (tmp_path / "code.py").write_text("result = dict(a=1)\npredict(x)\n")

        violations = scan(tmp_path)
        assert len(violations) == 0

    def test_multiword_term_detected(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("smart money concepts\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("")
        (tmp_path / "notes.md").write_text("We follow Smart Money Concepts here.\n")

        violations = scan(tmp_path)
        assert len(violations) == 1
        assert violations[0][2] == "smart money concepts"

    def test_non_scanned_extensions_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("wyckoff\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("")
        (tmp_path / "data.json").write_text('{"method": "wyckoff"}\n')

        violations = scan(tmp_path)
        assert len(violations) == 0

    def test_venv_directory_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "vpa").mkdir(parents=True)
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_BLACKLIST.txt").write_text("wyckoff\n")
        (tmp_path / "docs" / "vpa" / "VPA_VOCAB_EXCEPTIONS.txt").write_text("")
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "something.py").write_text("wyckoff = True\n")

        violations = scan(tmp_path)
        assert len(violations) == 0
