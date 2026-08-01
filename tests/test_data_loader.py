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


def test_location_check_passes_for_matching_address():
    check = data_loader.check_location_consistency("St. Charles", "MO", "63301")

    assert check["status"] == "ok"
    assert check["warnings"] == []
    assert check["expected_county"] == "Saint Charles"


def test_location_check_covers_zips_never_added_by_hand():
    """The bundled dataset covers every US ZIP, not a hand-maintained handful."""
    for city, state, zip_code in (
        ("Maryland Heights", "MO", "63043"),
        ("Beverly Hills", "CA", "90210"),
        ("Bloomington", "IN", "47401"),
        ("Cheyenne", "WY", "82001"),
    ):
        check = data_loader.check_location_consistency(city, state, zip_code)
        assert check["status"] == "ok", f"{city} {zip_code} -> {check}"


def test_location_check_accepts_saint_spelling():
    check = data_loader.check_location_consistency("Saint Charles", "MO", "63301")

    assert check["status"] == "ok"


def test_location_check_flags_wrong_city():
    check = data_loader.check_location_consistency("Saint Louis", "MO", "63301")

    assert check["status"] == "warning"
    assert "63301 is Saint Charles" in check["warnings"][0]


def test_location_check_flags_wrong_state():
    check = data_loader.check_location_consistency("Austin", "TX", "63301")

    assert check["status"] == "warning"
    assert "belongs to MO" in check["warnings"][0]


def test_location_check_flags_malformed_zip():
    check = data_loader.check_location_consistency("Austin", "TX", "787")

    assert check["status"] == "warning"
    assert "not a five-digit" in check["warnings"][0]


def test_location_check_reports_unassigned_zip_as_unverified():
    # 42900 is not an assigned US ZIP, so neither the city nor the state can be
    # confirmed - and the app says so rather than guessing.
    check = data_loader.check_location_consistency("Nowhere", "KY", "42900")

    assert check["status"] == "unverified"
    assert check["warnings"] == []
    assert any("not in the built-in location directory" in u for u in check["unverified"])


def test_state_for_zip_prefix_ranges():
    assert data_loader.state_for_zip("63301") == "MO"
    assert data_loader.state_for_zip("78704") == "TX"
    assert data_loader.state_for_zip("46202") == "IN"
    assert data_loader.state_for_zip("33602") == "FL"
    assert data_loader.state_for_zip("99801") == "AK"
    # 429 is not an assigned prefix, so no state is claimed and no warning fires.
    assert data_loader.state_for_zip("42900") is None


def _write_note(directory, name, text):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def test_reads_classic_knowledge_bank_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "user" / "zips" / "46202", "rental_policy_notes.md", "ZIP note")
    _write_note(tmp_path / "user" / "states" / "IN", "landlord_tenant_notes.txt", "State note")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    names = [doc["name"] for doc in context["documents"]]
    assert "rental_policy_notes.md" in names
    assert "landlord_tenant_notes.txt" in names


def test_reads_researched_and_user_roots_and_tags_source(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "researched" / "zips" / "46202", "policy-notes.md", "Skill note")
    _write_note(tmp_path / "user" / "zips" / "46202", "hoa.md", "User note")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    sources = {doc["name"]: doc["source"] for doc in context["documents"]}
    assert sources["policy-notes.md"] == "researched"
    assert sources["hoa.md"] == "user"


def test_reads_legacy_flat_skill_output_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "tx-78704", "policy-notes.md", "Austin STR rules")

    context = data_loader.load_knowledge_bank_context(
        "2100 S Congress Ave", "Austin", "TX", "78704"
    )

    assert [doc["name"] for doc in context["documents"]] == ["policy-notes.md"]
    assert context["documents"][0]["excerpt"] == "Austin STR rules"
    assert context["documents"][0]["source"] == "legacy"


def test_readme_files_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "user" / "global", "README.md", "instructions")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    assert context["documents"] == []


def test_unprefixed_folder_without_legacy_shape_is_not_searched(tmp_path, monkeypatch):
    # A note dropped directly at knowledge_bank/zips/<zip> (no researched/ or
    # user/ prefix, and not the legacy state-zip shape) predates neither
    # convention this app now understands, so it is not picked up.
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    _write_note(tmp_path / "zips" / "46202", "orphaned.md", "not searched")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    assert context["documents"] == []


def test_pdf_notes_are_read_not_silently_ignored(tmp_path, monkeypatch):
    """A PDF the user filed must never be skipped without saying so.

    HOA declarations and leases arrive as PDFs. Before this, they were dropped
    silently - the user reasonably assumed the document was being used.
    """
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    folder = tmp_path / "user" / "zips" / "46202"
    folder.mkdir(parents=True)
    # A structurally valid single-page PDF carrying real extractable text.
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with (folder / "hoa-declaration.pdf").open("wb") as handle:
        writer.write(handle)

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    names = [doc["name"] for doc in context["documents"]]
    assert "hoa-declaration.pdf" in names
    doc = next(d for d in context["documents"] if d["name"] == "hoa-declaration.pdf")
    assert doc["source"] == "user"
    # A text-free PDF is surfaced with an explanation rather than an empty body.
    assert "no extractable text" in doc["excerpt"]


def test_unreadable_pdf_explains_itself_rather_than_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loader, "KNOWLEDGE_BANK_DIR", tmp_path)
    folder = tmp_path / "user" / "zips" / "46202"
    folder.mkdir(parents=True)
    (folder / "corrupt.pdf").write_bytes(b"this is not a PDF at all")

    context = data_loader.load_knowledge_bank_context(
        "725 N Delaware St", "Indianapolis", "IN", "46202"
    )

    doc = next(d for d in context["documents"] if d["name"] == "corrupt.pdf")
    assert "could not be read as a PDF" in doc["excerpt"]
