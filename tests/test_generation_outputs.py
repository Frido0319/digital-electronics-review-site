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
