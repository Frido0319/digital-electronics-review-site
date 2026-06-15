from __future__ import annotations

from src.extract_sources import extract_all_sources
from src.render_html import render_site
from src.seed_content import render_required_source_pages, seed_content
from src.validate_site import validate_site


def main() -> None:
    extract_all_sources()
    seed_content()
    render_required_source_pages()
    render_site()
    report = validate_site(strict_assets=False)
    print(
        f"Generated site with {report['knowledge_count']} knowledge points, "
        f"{report['question_count']} questions, "
        f"{len(report['missing_assets'])} missing image assets."
    )


if __name__ == "__main__":
    main()
