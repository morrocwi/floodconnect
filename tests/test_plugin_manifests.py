"""v0.1.6 packaging: validate every plugin/marketplace/extension manifest this repo
ships is syntactically valid JSON and that every file path it points at (directly,
or via a documented placeholder like ${extensionPath}) actually exists in this repo.

Does not call any CLI (claude/codex/gemini) -- that is covered by separate, manual
isolated install tests run with HOME/CODEX_HOME/CLAUDE_CONFIG_DIR pointed at a
throwaway scratch config dir (see README.md §4a), never by this test suite,
which must run with no network and no external binary.
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

MANIFEST_PATHS = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "gemini-extension.json",
    ".mcp.json",
]


@pytest.mark.parametrize("rel_path", MANIFEST_PATHS)
def test_manifest_is_valid_json(rel_path):
    path = REPO_ROOT / rel_path
    assert path.is_file(), f"missing manifest: {rel_path}"
    json.loads(path.read_text(encoding="utf-8"))


def _load(rel_path):
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def test_claude_plugin_json_required_fields():
    data = _load(".claude-plugin/plugin.json")
    assert data["name"] == "floodconnect"
    assert data["version"] == "0.1.6"
    assert data["license"] == "MIT"
    assert data["homepage"] == "https://github.com/morrocwi/floodconnect"
    assert data["author"]["name"] == "morrocwi"


def test_codex_plugin_json_required_fields():
    data = _load(".codex-plugin/plugin.json")
    assert data["name"] == "floodconnect"
    assert data["version"] == "0.1.6"
    assert "description" in data and data["description"]


def test_gemini_extension_json_required_fields():
    data = _load("gemini-extension.json")
    assert data["name"] == "floodconnect"
    assert data["version"] == "0.1.6"


def test_mcp_json_server_args_path_exists():
    # .mcp.json is the single shared MCP source for both Claude Code (plugin +
    # project config) and Codex (its only MCP source -- it does not read any
    # Codex-specific manifest). Its command/args use ${CLAUDE_PLUGIN_ROOT},
    # the documented Claude Code stdio-server variable; strip it to get the
    # in-repo relative path this manifest actually points at.
    data = _load(".mcp.json")
    server = data["mcpServers"]["floodconnect"]
    assert server["command"] == "${CLAUDE_PLUGIN_ROOT}/.venv/bin/python"
    for arg in server["args"]:
        rel = arg.replace("${CLAUDE_PLUGIN_ROOT}/", "")
        assert (REPO_ROOT / rel).is_file(), f".mcp.json references missing path: {rel}"


def test_gemini_extension_mcp_server_args_path_exists():
    data = _load("gemini-extension.json")
    server = data["mcpServers"]["floodconnect"]
    for arg in server["args"]:
        # Gemini's own ${extensionPath}${/}... placeholder resolves to this
        # extension's own install root at runtime; strip it to get the
        # in-repo relative path this manifest actually points at.
        rel = arg.replace("${extensionPath}${/}", "").replace("${/}", "/")
        assert (REPO_ROOT / rel).is_file(), f"gemini-extension.json references missing path: {rel}"


def test_claude_marketplace_plugin_source_resolves():
    data = _load(".claude-plugin/marketplace.json")
    assert data["name"]
    assert data["owner"]["name"] == "morrocwi"
    for plugin in data["plugins"]:
        source = plugin["source"].rstrip("/") or "."
        assert (REPO_ROOT / source).is_dir()
        assert (REPO_ROOT / source / ".claude-plugin" / "plugin.json").is_file()


def test_codex_marketplace_plugin_source_resolves():
    data = _load(".agents/plugins/marketplace.json")
    for plugin in data["plugins"]:
        source = plugin["source"]
        assert (REPO_ROOT / source).is_dir()
        assert (REPO_ROOT / source / ".codex-plugin" / "plugin.json").is_file()


@pytest.mark.parametrize(
    "skill_path",
    [
        "skills/floodconnect/SKILL.md",
        "skills/floodconnect-method/SKILL.md",
    ],
)
def test_canonical_skill_files_exist(skill_path):
    path = REPO_ROOT / skill_path
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{skill_path} missing YAML frontmatter"
    assert "name:" in text.splitlines()[1:6][0] or "name:" in text[:400]
    assert "description:" in text[:800]


def test_old_skill_directory_removed():
    """v0.1.6 consolidation: the pre-v0.1.6 `skill/` directory must not come back
    as a duplicate copy alongside the canonical `skills/` tree."""
    assert not (REPO_ROOT / "skill").exists()


def test_gemini_context_file_is_thin_pointer():
    text = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")
    # Thin pointer only: must point at the canonical skills, never restate their content.
    assert "skills/floodconnect/SKILL.md" in text
    assert "skills/floodconnect-method/SKILL.md" in text
    assert len(text) < 2000


def test_version_consistent_across_the_four_canonical_places():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.6"' in pyproject

    caps = _load("system_capabilities.json")
    assert caps["pyproject_version"] == "0.1.6"

    skill_md = (REPO_ROOT / "skills/floodconnect-method/SKILL.md").read_text(encoding="utf-8")
    assert "version: 0.1.6" in skill_md

    mcp_server_src = (REPO_ROOT / "tools/mcp/floodconnect_mcp.py").read_text(encoding="utf-8")
    assert '"version": "0.1.6"' in mcp_server_src

    # And every plugin manifest agrees with the same version.
    for rel_path in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "gemini-extension.json"):
        assert _load(rel_path)["version"] == "0.1.6"
