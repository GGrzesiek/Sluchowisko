from html.parser import HTMLParser

SKIPPED_TAGS = {"script", "style", "figure", "aside", "table", "sup", "noscript", "nav", "header", "footer", "form"}
SKIPPED_CLASSES = {"toc", "wikia-gallery", "reference", "references", "mw-editsection", "navbox", "printfooter"}
SKIPPED_IDS = {"disambig", "toc"}
BLOCKS = {"p", "li", "dd", "dt", "blockquote", "div", "br", "ul", "ol", "section", "article", "main"}
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
HEADINGS = {"h2": 2, "h3": 3, "h4": 4}
CONTENT = ("article", "main")


class _PlainText(HTMLParser):
    def __init__(self, content_tag: str | None) -> None:
        super().__init__(convert_charrefs=True)
        self.content_tag = content_tag
        self.content_depth = 0 if content_tag else 1
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.skipped_depth = 0
        self.heading_level = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self.in_title = True
        if self.content_tag and tag == self.content_tag:
            self.content_depth += 1
        if self.skipped_depth:
            self.skipped_depth += tag not in VOID
            return
        found = dict(attrs)
        classes = set((found.get("class") or "").split())
        if tag in SKIPPED_TAGS or classes & SKIPPED_CLASSES or found.get("id") in SKIPPED_IDS:
            self.skipped_depth = int(tag not in VOID)
        elif tag in HEADINGS:
            self.heading_level = HEADINGS[tag]
            self._add("\n" + "=" * self.heading_level + " ")
        elif tag in BLOCKS:
            self._add("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if self.skipped_depth:
            self.skipped_depth -= tag not in VOID
        elif tag in HEADINGS and self.heading_level:
            self._add(" " + "=" * self.heading_level + "\n")
            self.heading_level = 0
        elif tag in BLOCKS:
            self._add("\n")
        if self.content_tag and tag == self.content_tag:
            self.content_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        elif not self.skipped_depth:
            self._add(data.replace("\n", " ") if self.heading_level else data)

    def _add(self, text: str) -> None:
        if self.content_depth > 0:
            self.parts.append(text)


def to_text(html: str) -> tuple[str, str]:
    content_tag = next((tag for tag in CONTENT if f"<{tag}" in html), None)
    parser = _PlainText(content_tag)
    parser.feed(html)
    parser.close()
    return " ".join("".join(parser.title_parts).split()), "".join(parser.parts)
