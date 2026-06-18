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


def test_seed_data_includes_homework_ids_visible_only_in_extracted_images():
    import json
    from src.seed_content import seed_content

    seed_content()
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))
    question_ids = {question["id"] for question in questions["questions"]}

    assert {"2.2.5", "2.3.4", "2.3.5", "3.2.21"} <= question_ids


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


def test_seed_data_attaches_official_answer_pages_for_matched_questions():
    import json
    from src.seed_content import seed_content

    seed_content()
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))["questions"]
    by_id = {question["id"]: question for question in questions}

    assert by_id["1.3.6"]["answer_source"] == "官方答案"
    assert by_id["1.3.6"]["official_answer_pages"][0]["image_path"] == "assets/official_answer_pages/official_answers_p001.png"
    assert "见本题下方官方参考答案截图" in by_id["1.3.6"]["subquestions"][0]["answer"]
    assert by_id["3.2.21"]["answer_source"] == "官方答案"
    assert [page["page"] for page in by_id["3.2.21"]["official_answer_pages"]] == [12]
    assert by_id["5.1.8"]["answer_source"] == "AI兜底答案"
    assert by_id["5.1.8"]["official_answer_pages"] == []


def test_source_manifest_includes_official_answer_pages():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    official_pages = manifest["official_answer_pages"]

    assert len(official_pages) == 15
    assert "assets/official_answer_pages/official_answers_p001.png" in official_pages
    assert "assets/official_answer_pages/official_answers_p015.png" in official_pages


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
    chapter_4 = next(source for source in gallery if source["file"] == "第4章  电子电路中的反馈.ppt")
    assert chapter_4["title"] == "第4章  电子电路中的反馈.ppt"
    assert len(chapter_4["pages"]) >= 60
    assert chapter_4["pages"][0]["image_path"] == "assets/course_pages/gallery_ppt_ch4_feedback_p001.png"


def test_seed_data_uses_ai_fallback_for_uncovered_homework_answers():
    import json
    from src.seed_content import seed_content

    seed_content()
    questions = json.loads(config.QUESTION_BANK_JSON.read_text(encoding="utf-8"))["questions"]
    by_id = {question["id"]: question for question in questions}
    fallback_ids = {"5.1.1", "5.1.8", "7.2.5", "7.3.1", "7.5.9", "7.5.13", "7.5.14", "7.6.17a", "7.6.17b"}

    assert all(by_id[question_id]["answer_source"] == "AI兜底答案" for question_id in fallback_ids)
    assert "待接入官方答案" not in "\n".join(
        subquestion["answer"]
        for question_id in fallback_ids
        for subquestion in by_id[question_id]["subquestions"]
    )
    assert "Y = AC + BC'" in by_id["7.2.5"]["subquestions"][0]["answer"]
    assert "YA = A" in by_id["7.6.17a"]["subquestions"][0]["answer"]
    assert "Y = B'C' + B'D' + BCD" in by_id["7.6.17b"]["subquestions"][0]["answer"]


def _source_key(path):
    return str(path.relative_to(config.SOURCE_ROOT)).replace("\\", "/")


def _expected_gallery_excluded_pages():
    excluded = {}
    for files in config.SOURCE_FILES.values():
        for path in files:
            if path.suffix.lower() != ".pdf":
                continue
            key = _source_key(path)
            excluded[key] = set()
            if key.endswith("第2章-基本放大电路9.pdf"):
                excluded[key].update(range(1, 25))
            if key.endswith("第2章-基本放大电路10.pdf"):
                excluded[key].update(range(21, 26))
            if key == "第5章-直流稳压电源.pdf":
                excluded[key].update(range(18, 23))
                excluded[key].update(range(33, 35))
                excluded[key].update(range(59, 63))
            if key.endswith("第7章 门电路和组合逻辑电路5.pdf"):
                excluded[key].update(range(61, 68))
    return excluded


def test_lecture_gallery_covers_every_non_excluded_pdf_page():
    import fitz
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    excluded = _expected_gallery_excluded_pages()
    gallery_pages = {
        source["file"]: {page["page"] for page in source["pages"]}
        for source in manifest["lecture_gallery"]
    }
    expected_total = 0
    for source in manifest["lecture_gallery"]:
        if source["file"] in excluded:
            assert not (gallery_pages[source["file"]] & excluded[source["file"]])

    for files in config.SOURCE_FILES.values():
        for path in files:
            if path.suffix.lower() != ".pdf":
                continue
            key = _source_key(path)
            doc = fitz.open(str(path))
            expected_pages = set(range(1, doc.page_count + 1)) - excluded[key]
            doc.close()
            expected_total += len(expected_pages)
            assert gallery_pages.get(key, set()) == expected_pages

    actual_total = sum(len(source["pages"]) for source in manifest["lecture_gallery"])
    assert actual_total >= expected_total
    assert actual_total >= 600


def test_lecture_gallery_marks_homework_and_knowledge_source_pages_as_key_pages():
    import json
    from src.seed_content import build_knowledge_points, build_questions, seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    excluded = _expected_gallery_excluded_pages()
    gallery_lookup = {
        (source["file"], page["page"]): page
        for source in manifest["lecture_gallery"]
        for page in source["pages"]
    }
    expected_key_pages = {
        (page.file, page.page)
        for point in build_knowledge_points()
        for page in point.source_pages
        if page.file in excluded and page.page not in excluded[page.file]
    } | {
        (page.file, page.page)
        for question in build_questions()
        for page in question.source_pages
        if page.file in excluded and page.page not in excluded[page.file]
    }

    assert expected_key_pages
    assert expected_key_pages <= set(gallery_lookup)
    assert all(gallery_lookup[key].get("is_key_page") is True for key in expected_key_pages)


def test_lecture_gallery_expands_key_marking_beyond_single_source_pages():
    import json
    from src.seed_content import seed_content

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    key_pages_by_source = {
        source["file"]: [page for page in source["pages"] if page.get("is_key_page")]
        for source in manifest["lecture_gallery"]
    }
    all_key_pages = [page for pages in key_pages_by_source.values() for page in pages]

    assert len(all_key_pages) >= 55
    assert any(page.get("key_reason") == "题目/知识点直接来源页" for page in all_key_pages)
    assert any(page.get("key_reason") == "题目相关相邻讲解页" for page in all_key_pages)
    assert sum(1 for page in key_pages_by_source["第5章-直流稳压电源.pdf"] if page.get("is_key_page")) >= 5


def test_lecture_gallery_marks_focus_images_as_double_red_box_pages():
    import json
    from src.seed_content import seed_content, super_key_image_names

    seed_content()
    manifest = json.loads(config.SOURCE_MANIFEST_JSON.read_text(encoding="utf-8"))
    gallery_lookup = {
        (source["file"], page["page"]): page
        for source in manifest["lecture_gallery"]
        for page in source["pages"]
    }
    super_pages = [page for source in manifest["lecture_gallery"] for page in source["pages"] if page.get("is_super_key_page")]
    target_file = "第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路5.pdf"

    assert set(super_key_image_names()) >= {"1.jpg", "2.jpg", "10.jpg", "9b3303554c659be093baf22ab61de8e0.jpg"}
    assert len(super_pages) >= 200
    assert gallery_lookup[(target_file, 114)]["is_super_key_page"] is True
    assert "10.jpg" in gallery_lookup[(target_file, 114)]["super_key_reason"]
    assert gallery_lookup[(target_file, 118)]["is_super_key_page"] is True
    assert any("2.jpg" in page.get("super_key_reason", "") for page in super_pages if page["page"] in {1, 2, 3, 4, 9, 11})
    assert all(page.get("is_key_page") is True for page in super_pages)


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
