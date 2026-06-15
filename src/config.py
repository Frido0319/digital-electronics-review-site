from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
COURSE_PAGES_DIR = ASSETS_DIR / "course_pages"
HOMEWORK_IMAGES_DIR = ASSETS_DIR / "homework_images"
SOURCE_TEXT_DIR = PROJECT_ROOT / "source_text"
EXTRACTED_TEXT_DIR = SOURCE_TEXT_DIR / "extracted_text"

INDEX_HTML = PROJECT_ROOT / "index.html"
OUTLINE_MD = PROJECT_ROOT / "outline.md"

EXCLUSIONS_JSON = DATA_DIR / "exclusions.json"
KNOWLEDGE_MAP_JSON = DATA_DIR / "knowledge_map.json"
QUESTION_BANK_JSON = DATA_DIR / "question_bank.json"
SOURCE_MANIFEST_JSON = DATA_DIR / "source_manifest.json"

# Placeholder hash for the MVP. Replace when the user confirms the final password.
DEFAULT_PASSWORD_SHA256 = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"

SOURCE_FILES = {
    "chapter_1": [
        SOURCE_ROOT / "第1章 半导体器件讲义" / "第1章-半导体器件1.pdf",
        SOURCE_ROOT / "第1章 半导体器件讲义" / "第1章-半导体器件2.pdf",
        SOURCE_ROOT / "第1章 半导体器件讲义" / "第1章-半导体器件34-.pdf",
    ],
    "chapter_2": sorted((SOURCE_ROOT / "第2章 基本放大电路").glob("*.pdf")),
    "chapter_3": sorted((SOURCE_ROOT / "第3章 集成运算放大电路").glob("*.pdf")),
    "chapter_4": [SOURCE_ROOT / "第4章  电子电路中的反馈.ppt"],
    "chapter_5": [SOURCE_ROOT / "第5章-直流稳压电源.pdf"],
    "chapter_7": sorted((SOURCE_ROOT / "第7章 门电路和组合逻辑电路").glob("*.pdf")),
}

HOMEWORK_FILES = sorted((SOURCE_ROOT / "课后作业").glob("*.docx"))
