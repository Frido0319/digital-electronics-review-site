from src import config
from src.render_html import render_site
from src.seed_content import seed_content


def test_render_site_creates_password_gate_and_indexes():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="password-screen"' in html
    assert 'id="course-app"' in html
    assert "章节知识主线" in html
    assert "作业题号索引" in html
    assert "前置知识" in html
    assert "正弦交流电有效值与峰值" in html
    assert "5.1.8" in html
    assert "单相桥式整流" in html
    assert "三相桥式整流" not in html


def test_render_site_includes_search_and_image_modal():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'aria-label="搜索题号或知识点"' in html
    assert 'id="image-modal"' in html
    assert "openImageModal" in html


def test_render_site_includes_beginner_route_and_current_location():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "初学者学习路线" in html
    assert 'id="current-location"' in html
    assert 'aria-current' in html
