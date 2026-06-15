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


def test_validator_accepts_complete_mvp_assets():
    from src.render_html import render_site
    from src.seed_content import seed_content
    from src.validate_site import validate_site

    seed_content()
    render_site()
    report = validate_site(strict_assets=True)

    assert report["question_count"] >= 5
    assert report["knowledge_count"] >= 8
    assert report["missing_assets"] == []


def test_source_page_manifest_paths_are_unique():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    pages = manifest["course_pages"]

    assert len(pages) == len(set(pages))
    assert all(path.startswith("assets/course_pages/") for path in pages)


def test_source_page_manifest_covers_question_source_pages():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))["questions"]
    manifest_pages = set(manifest["course_pages"])
    question_pages = {page["image_path"] for question in questions for page in question["source_pages"]}

    assert question_pages <= manifest_pages


def test_source_page_manifest_includes_expanded_lecture_gallery():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    gallery = manifest["lecture_gallery"]
    gallery_paths = {
        page["image_path"]
        for source in gallery
        for page in source["pages"]
    }

    assert len(gallery) >= 10
    assert len(gallery_paths) >= 70
    assert gallery_paths <= set(manifest["course_pages"])
    assert all(path.startswith("assets/course_pages/") for path in gallery_paths)


def test_lecture_gallery_omits_blackboard_excluded_topics():
    import fitz
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    text_chunks = []
    for source in manifest["lecture_gallery"]:
        source_path = config.SOURCE_ROOT / source["file"]
        doc = fitz.open(str(source_path))
        for page in source["pages"]:
            text_chunks.append(doc[page["page"] - 1].get_text("text"))
        doc.close()
    gallery_text = "\n".join(text_chunks)

    assert "场效应晶体管放大电路" not in gallery_text
    assert "频率特性" not in gallery_text
    assert "三相桥式整流" not in gallery_text
    assert "电感电容滤波器" not in gallery_text


def test_generated_html_references_existing_images():
    from html.parser import HTMLParser

    class ImgParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = []

        def handle_starttag(self, tag, attrs):
            if tag != "img":
                return
            attrs_dict = dict(attrs)
            if attrs_dict.get("src"):
                self.sources.append(attrs_dict["src"])

    parser = ImgParser()
    parser.feed(config.INDEX_HTML.read_text(encoding="utf-8"))
    missing = [source for source in parser.sources if not (config.PROJECT_ROOT / source).is_file()]

    assert parser.sources
    assert missing == []


def test_seed_questions_do_not_use_placeholder_images_for_mapped_homework():
    import json
    from src.seed_content import seed_content

    seed_content()
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))["questions"]
    mapped_ids = {"2.4.5", "3.2.13", "4.2.12", "5.1.8", "7.5.14"}

    for question in questions:
        if question["id"] in mapped_ids:
            assert question["image_paths"]
            assert all("placeholder" not in path for path in question["image_paths"])
            assert all((config.PROJECT_ROOT / path).is_file() for path in question["image_paths"] if not path.endswith(".emf"))


def test_seed_questions_cover_all_text_extracted_homework_ids():
    import json
    from src.seed_content import seed_content

    seed_content()
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))["questions"]
    question_ids = {question["id"] for question in questions}
    expected = {
        "1.3.6",
        "1.3.9",
        "1.4.3",
        "1.5.8",
        "1.5.9",
        "2.4.5",
        "2.4.6",
        "2.4.7",
        "2.6.2",
        "2.6.3",
        "2.6.4",
        "3.1.2",
        "3.2.8",
        "3.2.13",
        "3.2.16",
        "3.3.4",
        "4.2.6",
        "4.2.12",
        "5.1.1",
        "5.1.8",
        "7.2.5",
        "7.3.1",
        "7.5.9",
        "7.5.13",
        "7.5.14",
        "7.6.17a",
        "7.6.17b",
    }

    assert expected <= question_ids


def test_office_ascii_stem_produces_safe_filename():
    from src.extract_sources import ascii_stem

    assert ascii_stem("第4章  电子电路中的反馈.ppt").startswith("office_")
    assert ascii_stem("5 直流稳压电源作业.docx").endswith("_docx")
