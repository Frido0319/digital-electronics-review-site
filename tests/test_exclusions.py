import json

from src import config


def test_blackboard_exclusions_are_recorded():
    data = json.loads(config.EXCLUSIONS_JSON.read_text(encoding="utf-8"))
    sections = {item["section"] for item in data["excluded_sections"]}

    assert {"2.6", "2.8", "3.3.1", "3.3.2", "3.4", "5.1.3", "5.2.2", "5.2.3", "5.3.4", "7.12"} <= sections
    assert data["policy"].startswith("完全不做")


def test_homework_policy_uses_content_judgment():
    data = json.loads(config.EXCLUSIONS_JSON.read_text(encoding="utf-8"))

    assert "逐题按内容判断" in data["homework_policy"]
