from pathlib import Path

from rag.loaders import SUPPORTED_EXTENSIONS, load_document


def test_supported_extensions_include_structured_formats():
    for suffix in (".json", ".jsonl", ".yaml", ".yml", ".xml"):
        assert suffix in SUPPORTED_EXTENSIONS


def test_json_loader_flattens_fields(tmp_path: Path):
    path = tmp_path / "sample.json"
    path.write_text('{"title":"Plan","meta":{"lang":"fr"},"items":[1,2]}', encoding="utf-8")

    docs = load_document(path)

    assert len(docs) == 1
    assert "title: Plan" in docs[0].text
    assert "meta.lang: fr" in docs[0].text
    assert "items[0]: 1" in docs[0].text


def test_yaml_loader_flattens_fields(tmp_path: Path):
    path = tmp_path / "sample.yml"
    path.write_text("name: project\nsettings:\n  env: dev\n", encoding="utf-8")

    docs = load_document(path)

    assert len(docs) == 1
    assert "name: project" in docs[0].text
    assert "settings.env: dev" in docs[0].text


def test_xml_loader_extracts_text(tmp_path: Path):
    path = tmp_path / "sample.xml"
    path.write_text("<root><title>Alpha</title><body>Hello world</body></root>", encoding="utf-8")

    docs = load_document(path)

    assert len(docs) == 1
    assert "Alpha" in docs[0].text
    assert "Hello world" in docs[0].text


def test_markdown_loader_keeps_raw_and_rendered_text(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# Title\n\n- item-a\n- item-b\n", encoding="utf-8")

    docs = load_document(path)

    assert len(docs) == 1
    assert "# Title" in docs[0].text
    assert "Rendered text:" in docs[0].text
