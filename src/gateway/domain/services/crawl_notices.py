"""Removal of "🌐 Crawling site ..." progress lines that the legacy chat API may emit.

Works on a stream: text is only held back while the current line could still be a notice.
"""

CRAWL_PREFIX = "\U0001f310 Crawling site"


class CrawlNoticeFilter:
    def __init__(self) -> None:
        self._pending = ""
        self._at_line_start = True

    def feed(self, chunk: str) -> str:
        output: list[str] = []
        for char in chunk:
            if self._pending:
                self._pending += char
                if self._pending.startswith(CRAWL_PREFIX):
                    if char == "\n":  # a complete notice line: drop it
                        self._pending = ""
                        self._at_line_start = True
                    continue
                if CRAWL_PREFIX.startswith(self._pending):
                    continue
                output.append(self._pending)
                self._pending = ""
                self._at_line_start = char == "\n"
            elif self._at_line_start and char == CRAWL_PREFIX[0]:
                self._pending = char
            else:
                output.append(char)
                self._at_line_start = char == "\n"
        return "".join(output)

    def flush(self) -> str:
        pending, self._pending = self._pending, ""
        return "" if pending.startswith(CRAWL_PREFIX) else pending


def strip_crawl_notices(text: str) -> str:
    notice_filter = CrawlNoticeFilter()
    return notice_filter.feed(text) + notice_filter.flush()
