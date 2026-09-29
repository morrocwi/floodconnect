from pathlib import Path

import yaml

import agent_claims as ac


def write_yaml(path: Path, doc):
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def minimal_rkg(tmp_path: Path):
    path = tmp_path / "rkg.yaml"
    write_yaml(path, {"nodes": {"SOCL": {}, "ORCG": {}, "GOVERNANCE": {}}})
    return path


def claim(claim_id, node, writer="agent-a", status="ACTIVE"):
    return {
        "claim_id": claim_id,
        "status": status,
        "writer": writer,
        "branch": f"agent/{writer}/task",
        "base_sha": "a" * 40,
        "nodes": [node],
        "artifacts": ["x.py"],
        "intent": "test",
        "created_at": "2026-09-29T15:40:00+07:00",
        "expires_at": None,
        "reviewers": [],
    }


def test_empty_claim_directory_is_valid(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    assert ac.validate_claims(claims, minimal_rkg(tmp_path)) == []


def test_one_active_writer_per_node_is_valid(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    doc = claim("20260929-agent-a-socl", "SOCL")
    write_yaml(claims / "20260929-agent-a-socl.yaml", doc)
    assert ac.validate_claims(claims, minimal_rkg(tmp_path)) == []


def test_two_active_writers_same_node_fail_even_when_artifacts_differ(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()

    a = claim("20260929-agent-a-socl", "SOCL", writer="agent-a")
    a["artifacts"] = ["shelter_operation_ladder.py"]
    b = claim("20260929-agent-b-socl-doc", "SOCL", writer="agent-b")
    b["artifacts"] = ["docs/SHELTER_OPERATION_CAPABILITY_LADDER.md"]

    write_yaml(claims / "20260929-agent-a-socl.yaml", a)
    write_yaml(claims / "20260929-agent-b-socl-doc.yaml", b)

    errors = ac.validate_claims(claims, minimal_rkg(tmp_path))
    assert any("multiple ACTIVE writers" in x for x in errors)


def test_released_claim_does_not_block_new_writer(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()

    old = claim("20260928-agent-a-socl", "SOCL", writer="agent-a", status="RELEASED")
    new = claim("20260929-agent-b-socl", "SOCL", writer="agent-b")
    write_yaml(claims / "20260928-agent-a-socl.yaml", old)
    write_yaml(claims / "20260929-agent-b-socl.yaml", new)

    assert ac.validate_claims(claims, minimal_rkg(tmp_path)) == []


def test_unknown_rkg_node_fails(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    doc = claim("20260929-agent-a-unknown", "NOT_A_NODE")
    write_yaml(claims / "20260929-agent-a-unknown.yaml", doc)

    errors = ac.validate_claims(claims, minimal_rkg(tmp_path))
    assert any("unknown canonical RKG node" in x for x in errors)


def test_filename_must_match_claim_id(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    doc = claim("20260929-agent-a-socl", "SOCL")
    write_yaml(claims / "wrong-name.yaml", doc)

    errors = ac.validate_claims(claims, minimal_rkg(tmp_path))
    assert any("filename stem must equal claim_id" in x for x in errors)


def test_branch_must_be_agent_namespace(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    doc = claim("20260929-agent-a-socl", "SOCL")
    doc["branch"] = "feature/random"
    write_yaml(claims / "20260929-agent-a-socl.yaml", doc)

    errors = ac.validate_claims(claims, minimal_rkg(tmp_path))
    assert any("branch must match" in x for x in errors)


def test_template_files_are_ignored(tmp_path):
    claims = tmp_path / "claims"
    claims.mkdir()
    write_yaml(claims / "_template.yaml", {"bad": "shape"})
    assert ac.validate_claims(claims, minimal_rkg(tmp_path)) == []
