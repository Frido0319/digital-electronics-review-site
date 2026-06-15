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
