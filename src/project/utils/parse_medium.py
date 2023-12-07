import time
from html.parser import HTMLParser

import feedparser


class HTMLtoDictParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = {}
        self.current_path = []
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_path.append(tag)
        self.current_tag = {
            "tag": tag,
            "attrs": dict(attrs),
            "text": "",
            "children": [],
        }

        if not self.current_path:
            self.result = self.current_tag
        else:
            parent = self.get_parent()
            parent.setdefault("children", []).append(self.current_tag)

    def handle_data(self, data):
        if self.current_tag and data.strip():
            self.current_tag["text"] += data

    def get_parent(self):
        parent = self.result
        for _ in self.current_path[:-1]:
            if "children" not in parent:
                parent["children"] = []
            parent = parent["children"][-1]
        return parent

    def handle_endtag(self, tag):
        if self.current_path[-1] == tag:
            self.current_path.pop()

    def get_result(self):
        return self.result


def parse_medium_html() -> list:
    feed = feedparser.parse("https://blog.globalify.xyz/feed")
    posts = []

    def get_img(summary):
        new_summary = summary.split('src="')[1]
        img = new_summary.split('"')[0]
        return img

    for entry in feed.entries:
        parser = HTMLtoDictParser()
        parser.feed(entry.summary)

        parsed = parser.get_result().get("children")
        print(parsed)
        print("\n\n")

        subtitle = "Continue reading on Globalify »"
        if parsed:
            if parsed[0].get("tag") in ["h3", "h2"]:
                for index, child in enumerate(parsed):
                    if child.get("tag") == "p":
                        subtitle = child.get("text")
                        if len(subtitle) < 150 and parsed[index + 1].get("tag") == "p":
                            subtitle = f"{subtitle} {parsed[index + 1].get("text")}"
                        break
            elif parsed[0].get("tag") == "div":
                subtitle = parsed[0].get("children")[1].get("text")

        posts.append(
            {
                "title": entry.title,
                "subtitle": subtitle,
                "image": get_img(entry.summary),
                "author": entry.author,
                "published": time.strftime("%b %d, %Y", entry.published_parsed),
                "link": entry.link,
            }
        )

    return posts
