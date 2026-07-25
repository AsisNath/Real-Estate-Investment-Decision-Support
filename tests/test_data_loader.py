import app.data_loader as data_loader


def test_policy_context_merges_city_and_state_levels():
    context = data_loader.load_policy_context("46202", "IN")

    assert context["match_level"] == "zip"
    assert context["jurisdiction_levels"] == [
        "Indianapolis / Marion County sample",
        "Indiana state-level fallback",
    ]
    jurisdictions = {link["jurisdiction"] for link in context["links"]}
    assert "City of Indianapolis / Marion County" in jurisdictions
    assert "State of Indiana" in jurisdictions
    # The state record's "local rules unresolved" warning must NOT appear,
    # because the ZIP-level record already resolved the city/county rules.
    assert all(
        flag["title"] != "City/county STR rules not resolved"
        for flag in context["restriction_flags"]
    )


def test_state_fallback_hides_other_city_example_links():
    # Saint Charles, MO (ZIP 63301) is not St. Louis, so the state fallback
    # must not surface the City of St. Louis STR example link.
    context = data_loader.load_policy_context("63301", "MO", "Saint Charles")

    assert context["match_level"] == "state"
    labels = [link["label"] for link in context["links"]]
    assert "St. Louis STR permits example" not in labels
    assert "Missouri Attorney General landlord-tenant law" in labels


def test_state_fallback_keeps_matching_city_example_links():
    # A St. Louis property with an unlisted ZIP should still get the city link,
    # whether the user types "Saint Louis" or "St. Louis".
    for spelling in ("Saint Louis", "St. Louis", "st louis"):
        context = data_loader.load_policy_context("63110", "MO", spelling)
        labels = [link["label"] for link in context["links"]]
        assert "St. Louis STR permits example" in labels, spelling


def test_city_normalization():
    assert data_loader._normalize_city("Saint Charles") == "st charles"
    assert data_loader._normalize_city("St. Louis") == "st louis"
    assert data_loader._normalize_city("SAINT LOUIS") == "st louis"
    assert data_loader._normalize_city("Indianapolis") == "indianapolis"


def test_state_fallback_keeps_unresolved_local_warning():
    context = data_loader.load_policy_context("47401", "IN")

    assert context["match_level"] == "state"
    assert any(
        flag["title"] == "City/county STR rules not resolved"
        for flag in context["restriction_flags"]
    )


def test_policy_context_deduplicates_repeated_links():
    context = data_loader.load_policy_context("46202", "IN")

    keys = [(link["url"], link["category"]) for link in context["links"]]
    assert len(keys) == len(set(keys))


def test_policy_context_every_item_has_jurisdiction():
    for zip_code, state in (("46202", "IN"), ("63109", "MO"), ("78704", "TX")):
        context = data_loader.load_policy_context(zip_code, state)
        assert all("jurisdiction" in flag for flag in context["restriction_flags"])
        assert all("jurisdiction" in link for link in context["links"])


def test_policy_context_state_fallback():
    context = data_loader.load_policy_context("99999", "FL")

    assert context["match_level"] == "state"
    assert context["missing_data_flags"]
    assert context["jurisdiction_levels"] == ["Florida state-level fallback"]


def test_state_fallback_message_names_the_city():
    context = data_loader.load_policy_context("63301", "MO", "Saint Charles")

    message = context["missing_data_flags"][0]
    assert "Saint Charles, MO" in message
    assert "state-level only" in message


def test_policy_context_national_fallback():
    context = data_loader.load_policy_context("99999", "ZZ")

    assert context["match_level"] == "national"
    assert context["jurisdiction_levels"] == ["Generic policy fallback"]
    assert context["restriction_flags"][0]["jurisdiction"] == "Unknown jurisdiction"


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
