"""Tests for gettree CLI helpers."""

import pytest
import typer

from gettree.cli import save_output


def test_save_output_message_shows_bracket_path(tmp_path, capsys):
    target = tmp_path / "[bracket].md"
    # Forward slashes: a backslash before "[" would mask the bug,
    # rich treats "\[" as an escaped literal bracket.
    save_output("hello", target.as_posix())
    assert target.read_text(encoding="utf-8") == "hello"
    out = capsys.readouterr().out
    assert "[bracket].md" in out


def test_save_output_error_shows_full_path(tmp_path, capsys):
    target = tmp_path / "[nope]" / "x.md"
    with pytest.raises(typer.Exit):
        save_output("hello", str(target))
    out = capsys.readouterr().out
    assert "[nope]" in out
