"""Conservative adapter for explicitly permitted web image URLs."""
from __future__ import annotations

import time
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import Iterator

from .base import Image, read_manifest


class PermittedWebSourceAdapter:
    def __init__(self, manifest: Path, permitted_hosts: set[str], user_agent: str, rate_limit_seconds: float = 2.0) -> None:
        self.manifest = manifest
        self.permitted_hosts = {host.lower() for host in permitted_hosts}
        self.user_agent = user_agent
        self.rate_limit_seconds = max(0.0, rate_limit_seconds)
        self._last_request = 0.0
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _allowed(self, uri: str) -> bool:
        parsed = urllib.parse.urlparse(uri)
        if parsed.scheme != "https" or parsed.hostname is None or parsed.hostname.lower() not in self.permitted_hosts:
            return False
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = self._robots.get(robots_url)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser(robots_url)
            parser.read()
            self._robots[robots_url] = parser
        return parser.can_fetch(self.user_agent, uri)

    def items(self) -> Iterator[Image]:
        for item in read_manifest(self.manifest):
            if not self._allowed(item.uri):
                raise PermissionError(f"URL is not explicitly permitted or robots.txt disallows it: {item.uri}")
            wait = self.rate_limit_seconds - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            yield item
