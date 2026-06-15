from __future__ import annotations

import json
from pathlib import Path

from . import config


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _asset_exists(relative_path: str) -> bool:
    return (config.PROJECT_ROOT / relative_path).is_file()


def validate_site(strict_assets: bool = True) -> dict:
    knowledge = _load(config.KNOWLEDGE_MAP_JSON)["knowledge_points"]
    questions = _load(config.QUESTION_BANK_JSON)["questions"]

    missing_assets = []
    for point in knowledge:
        if not point["source_pages"]:
            raise AssertionError(f"知识点缺少来源页: {point['id']}")
        for page in point["source_pages"]:
            if not _asset_exists(page["image_path"]):
                missing_assets.append(page["image_path"])

    for question in questions:
        if not question["image_paths"]:
            raise AssertionError(f"题目缺少原题图: {question['id']}")
        if not question["subquestions"]:
            raise AssertionError(f"题目缺少子题解析: {question['id']}")
        for subquestion in question["subquestions"]:
            if not subquestion["answer"]:
                raise AssertionError(f"子题缺少答案: {subquestion['id']}")
        for image_path in question["image_paths"]:
            if not _asset_exists(image_path):
                missing_assets.append(image_path)
        for page in question["source_pages"]:
            if not _asset_exists(page["image_path"]):
                missing_assets.append(page["image_path"])

    if "三相桥式整流" in config.INDEX_HTML.read_text(encoding="utf-8"):
        raise AssertionError("不考内容出现在学生页面: 三相桥式整流")

    if strict_assets and missing_assets:
        raise AssertionError(f"缺少 {len(missing_assets)} 个图片资源")

    return {
        "knowledge_count": len(knowledge),
        "question_count": len(questions),
        "missing_assets": sorted(set(missing_assets)),
    }
