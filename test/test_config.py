# Copyright (c) 2026, Arm Limited.
# SPDX-License-Identifier: MIT

import textwrap

from shrinkwrap.utils import config as cfg
from shrinkwrap.utils import workspace


def _sync_script_for_revision(tmp_path, monkeypatch, revision):
    monkeypatch.setattr(workspace, "package", str(tmp_path / "package"))
    monkeypatch.setattr(workspace, "build", str(tmp_path / "build"))

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        textwrap.dedent(
            f"""\
            %YAML 1.2
            ---
            concrete: true
            build:
              rmm:
                repo:
                  remote: https://example.com/tf-rmm.git
                  revision: {revision}
            """
        ),
        encoding="utf-8",
    )

    resolved = cfg.resolveb(cfg.load(str(config_path)))
    graph = cfg.build_graph([resolved], echo=False, nosync=[], force_sync=[])

    for script in graph:
        if script.summary == "Syncing git repo":
            return script.commands(False)

    raise AssertionError("missing sync script")


def test_short_git_sha_detection():
    assert cfg._looks_like_abbreviated_git_sha("d54026d")
    assert cfg._looks_like_abbreviated_git_sha(
        "d54026d18ccd305d179636e0d680278740f63086"
    )

    assert not cfg._looks_like_abbreviated_git_sha("20260408")
    assert not cfg._looks_like_abbreviated_git_sha("main")
    assert not cfg._looks_like_abbreviated_git_sha("refs/changes/12/1234/5")


def test_build_graph_fetches_all_refs_for_short_git_sha(tmp_path, monkeypatch):
    script = _sync_script_for_revision(tmp_path, monkeypatch, "d54026d")

    assert "git fetch --quiet  --tags origin d54026d" not in script
    assert "git fetch --quiet --prune --tags origin d54026d" not in script
    assert "git fetch --quiet  --tags origin\n" in script
    assert "git fetch --quiet --prune --tags origin &&" in script


def test_build_graph_fetches_named_revision_directly(tmp_path, monkeypatch):
    script = _sync_script_for_revision(tmp_path, monkeypatch, "main")

    assert "git fetch --quiet  --tags origin main" in script
    assert "git fetch --quiet --prune --tags origin main &&" in script
