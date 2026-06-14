from pathlib import Path


def test_shell_scripts_are_marked_lf_in_git_attributes() -> None:
    attributes = Path(".gitattributes").read_text(encoding="utf-8")

    assert "*.sh text eol=lf" in attributes


def test_dockerfile_strips_crlf_from_entrypoint_before_chmod() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    normalize = "sed -i 's/\\r$//' ./docker/entrypoint.sh"
    chmod = "chmod +x ./docker/entrypoint.sh"

    assert normalize in dockerfile
    assert dockerfile.index(normalize) < dockerfile.index(chmod)
