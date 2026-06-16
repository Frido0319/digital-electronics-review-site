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
    assert 'rel="icon"' in html
    assert 'id="image-modal"' in html
    assert "openImageModal" in html


def test_render_site_includes_beginner_route_and_current_location():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "初学者学习路线" in html
    assert 'id="current-location"' in html
    assert 'aria-current' in html


def test_render_site_populates_methods_and_checklist_from_seed_data():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "本区由知识点公式自动汇总" not in html
    assert "桥式整流" in html
    assert "虚短虚断" in html
    assert "考前清单" in html
    assert "有效值和平均值" in html


def test_render_site_uses_display_math_blocks_for_formulas_and_calculations():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="math-block"' in html
    assert 'class="math-line"' in html
    assert 'data-raw="UO = 0.9U2"' in html
    assert "U<sub>O</sub> = 0.9U<sub>2</sub>" in html
    assert 'data-raw="u+ = u-"' in html
    assert "u<sup>+</sup> = u<sup>-</sup>" in html
    assert 'data-raw="IO / 2 = 1 A"' in html
    assert '<span class="frac"><span>I<sub>O</sub></span><span>2</span></span> = 1 A' in html
    assert "桥式整流：UO = 0.9U2" not in html
    assert "虚短虚断：u+ = u-" not in html
    assert "<p>、</p>" not in html


def test_render_site_exposes_answer_status_summary():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "答案状态" in html
    assert "官方答案" in html
    assert "待核对" in html
    assert "推导答案" in html
    assert "已接入的参考答案 PDF 覆盖" in html


def test_render_site_shows_clickable_official_answer_pages():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "官方参考答案页截图" in html
    assert "电子技术部分章节作业参考答案to中德.pdf" in html
    assert "assets/official_answer_pages/official_answers_p001.png" in html
    assert "1.3.6 官方参考答案 p.1" in html
    assert 'class="official-answer-page"' in html


def test_render_site_includes_expanded_lecture_gallery():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert "原讲义 PDF 截图库" in html
    assert 'id="lecture-gallery"' in html
    assert 'class="lecture-page"' in html
    assert html.count('<figure class="lecture-page') >= 550
    assert "第2章-基本放大电路7.pdf" in html
    assert "第7章 门电路和组合逻辑电路4.pdf" in html


def test_render_site_marks_key_gallery_pages_with_red_border_and_modal():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="lecture-page is-key-page"' in html
    assert "题目/知识点直接来源页" in html
    assert "题目相关相邻讲解页" in html
    assert ".lecture-page.is-key-page button" in html
    assert "#dc2626" in html
    gallery_html = html.split('id="lecture-gallery"', 1)[1].split('id="answer-status"', 1)[0]
    assert gallery_html.count('<figure class="lecture-page') == gallery_html.count("data-modal-src=")


def test_render_site_marks_focus_gallery_pages_with_double_red_border():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="lecture-page is-key-page is-super-key-page"' in html
    assert "重点中的重点截图命中" in html
    assert "10.jpg" in html
    assert ".lecture-page.is-super-key-page button" in html
    assert 'class="super-key-page-badge"' in html
    assert "4px double #b91c1c" in html


def test_render_site_uses_safe_modal_button_attributes():
    from html.parser import HTMLParser

    class ButtonParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.modal_buttons = []

        def handle_starttag(self, tag, attrs):
            if tag != "button":
                return
            attrs_dict = dict(attrs)
            onclick = attrs_dict.get("onclick", "")
            if "openImageModal" in onclick:
                self.modal_buttons.append(attrs_dict)

    seed_content()
    render_site()
    parser = ButtonParser()
    parser.feed(config.INDEX_HTML.read_text(encoding="utf-8"))

    assert parser.modal_buttons
    assert all(button["onclick"] == "openImageModal(this.dataset.modalSrc, this.dataset.modalCaption)" for button in parser.modal_buttons)
    assert all(button.get("data-modal-src", "").startswith("assets/") for button in parser.modal_buttons)
    assert all(button.get("data-modal-caption") for button in parser.modal_buttons)


def test_image_modal_has_previous_and_next_navigation_controls():
    seed_content()
    render_site()
    html = config.INDEX_HTML.read_text(encoding="utf-8")

    assert 'class="modal-nav modal-prev"' in html
    assert 'class="modal-nav modal-next"' in html
    assert 'aria-label="上一张图片"' in html
    assert 'aria-label="下一张图片"' in html
    assert "showAdjacentImage(-1)" in html
    assert "showAdjacentImage(1)" in html
    assert 'event.key === "ArrowLeft"' in html
    assert 'event.key === "ArrowRight"' in html


def test_render_site_writes_shareable_outline():
    seed_content()
    render_site()
    outline = config.OUTLINE_MD.read_text(encoding="utf-8")

    assert "# 数电复习网站目录" in outline
    assert "## 第5章" in outline
    assert "- 5.1.8 单相桥式整流参数计算" in outline
    assert "官方答案状态" in outline
