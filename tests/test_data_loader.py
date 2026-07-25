import app.data_loader as data_loader


def _write_note(directory, name, text):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def test_reads_classic_knowledge_bank_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "zips" / "46202", "rental_policy_notes.md", "ZIP note")
    _write_note(tmp_path / "states" / "IN", "landlord_tenant_notes.txt", "State note")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    names = [doc["name"] for doc in context["documents"]]
    assert "rental_policy_notes.md" in names
    assert "landlord_tenant_notes.txt" in names


def test_reads_policy_research_skill_output_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "tx-78704", "policy-notes.md", "Austin STR rules")

    context = data_loader.load_knowledge_bank_context(
        "2100 S Congress Ave", "Austin", "TX", "78704"
    )

    assert [doc["name"] for doc in context["documents"]] == ["policy-notes.md"]
    assert context["documents"][0]["excerpt"] == "Austin STR rules"


def test_readme_files_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "global", "README.md", "instructions")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    assert context["documents"] == []
