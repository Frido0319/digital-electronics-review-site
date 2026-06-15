from src import config


def test_source_root_points_to_course_folder():
    assert (config.SOURCE_ROOT / "课后作业").is_dir()
    assert (config.SOURCE_ROOT / "第5章-直流稳压电源.pdf").is_file()


def test_expected_output_paths_are_inside_project():
    root = config.PROJECT_ROOT.resolve()
    for path in [
        config.INDEX_HTML,
        config.KNOWLEDGE_MAP_JSON,
        config.QUESTION_BANK_JSON,
        config.SOURCE_MANIFEST_JSON,
    ]:
        resolved = path.resolve()
        assert root in resolved.parents or resolved == root


def test_exclusion_policy_file_exists():
    assert config.EXCLUSIONS_JSON.is_file()


def test_extraction_helpers_normalize_text_and_paths():
    from src.extract_sources import clean_text, relative_asset_path

    assert clean_text("  第5章\n\n直流   稳压电源 ") == "第5章 直流 稳压电源"
    path = config.PROJECT_ROOT / "assets" / "course_pages" / "ch5_p001.png"
    assert relative_asset_path(path) == "assets/course_pages/ch5_p001.png"


def test_seed_data_contains_chapter_first_structure():
    import json
    from src.seed_content import seed_content

    seed_content()

    knowledge = json.loads(config.KNOWLEDGE_MAP_JSON.read_text(encoding="utf-8"))
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))

    chapters = {point["chapter"] for point in knowledge["knowledge_points"]}
    question_ids = {question["id"] for question in questions["questions"]}

    assert {"1", "2", "3", "4", "5", "7"} <= chapters
    assert {"5.1.8", "7.5.14"} <= question_ids


def test_seed_data_excludes_blackboard_sections_from_knowledge_titles():
    import json
    from src.seed_content import seed_content

    seed_content()
    knowledge = json.loads(config.KNOWLEDGE_MAP_JSON.read_text(encoding="utf-8"))
    titles = " ".join(point["title"] for point in knowledge["knowledge_points"])

    assert "三相桥式整流" not in titles
    assert "场效应晶体管放大电路" not in titles
    assert "频率特性" not in titles


def test_validator_reports_missing_placeholder_assets():
    from src.render_html import render_site
    from src.seed_content import seed_content
    from src.validate_site import validate_site

    seed_content()
    render_site()
    report = validate_site(strict_assets=False)

    assert report["question_count"] >= 5
    assert report["knowledge_count"] >= 8
    assert report["missing_assets"]


def test_source_page_manifest_paths_are_unique():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    pages = manifest["course_pages"]

    assert len(pages) == len(set(pages))
    assert all(path.startswith("assets/course_pages/") for path in pages)
