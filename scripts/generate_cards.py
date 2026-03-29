#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

API_ROOT = "https://api.github.com"
CARD_WIDTH = 640
CARD_HEIGHT = 210

FEATURED_REPOS: list[tuple[str, str]] = [
    ("unity-helpers", "Treasure chest of Unity developer tools"),
    ("DxMessaging", "Engine-agnostic robust messaging solution"),
    ("DxCommandTerminal", "Unity command terminal: in-game console"),
]


def github_get(path: str, token: str | None = None, params: dict[str, Any] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{API_ROOT}{path}{query}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "wallstop-card-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all_repos(owner: str, token: str | None = None) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        chunk = github_get(
            f"/users/{owner}/repos",
            token=token,
            params={"per_page": 100, "page": page, "sort": "updated", "direction": "desc"},
        )
        if not chunk:
            break
        repos.extend(chunk)
        page += 1
    return repos


def stat_chip(x: int, y: int, label: str, value: str, chip_color: str, width: int | None = None) -> str:
    text = f"{escape(label)}: {escape(value)}"
    rendered_width = width if width is not None else (14 * len(text) + 28)
    return (
        f'<rect x="{x}" y="{y}" width="{rendered_width}" height="34" rx="17" fill="{chip_color}" fill-opacity="0.20" '
        f'stroke="{chip_color}" />\n'
        f'<text x="{x + 14}" y="{y + 23}" fill="#C9D1D9" font-size="17" '
        f'font-family="Segoe UI, Ubuntu, sans-serif">{text}</text>'
    )


def make_repo_card(repo: dict[str, Any], description: str) -> str:
    name = repo["name"]
    language = repo.get("language") or "Mixed"
    stars = str(repo.get("stargazers_count", 0))
    forks = str(repo.get("forks_count", 0))
    issues = str(repo.get("open_issues_count", 0))
    pushed_at = repo.get("pushed_at", "")
    updated = "Unknown"
    if pushed_at:
        updated = dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")

    chips = [
        stat_chip(24, 148, "Stars", stars, "#238636", width=188),
        stat_chip(224, 148, "Forks", forks, "#8250DF", width=188),
        stat_chip(424, 148, "Issues", issues, "#DA3633", width=188),
    ]

    return f'''<svg width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{escape(name)}</title>
  <desc id="desc">{escape(description)}</desc>
  <rect x="1" y="1" width="{CARD_WIDTH - 2}" height="{CARD_HEIGHT - 2}" rx="18" fill="#0D1117" stroke="#30363D" stroke-width="2"/>
  <text x="24" y="50" fill="#58A6FF" font-size="34" font-weight="700" font-family="Segoe UI, Ubuntu, sans-serif">{escape(name)}</text>
  <text x="24" y="88" fill="#C9D1D9" font-size="22" font-family="Segoe UI, Ubuntu, sans-serif">{escape(description)}</text>
  <text x="24" y="118" fill="#8B949E" font-size="17" font-family="Segoe UI, Ubuntu, sans-serif">Language: {escape(language)} • Last updated: {updated}</text>
  {chips[0]}
  {chips[1]}
  {chips[2]}
</svg>
'''


def make_all_repos_card(owner: str, user: dict[str, Any], repos: list[dict[str, Any]]) -> str:
    public_repos = str(user.get("public_repos", 0))
    followers = str(user.get("followers", 0))
    following = str(user.get("following", 0))
    total_stars = str(sum(int(repo.get("stargazers_count", 0)) for repo in repos))

    chips = [
        stat_chip(24, 116, "Public repos", public_repos, "#1F6FEB", width=288),
        stat_chip(328, 116, "Followers", followers, "#238636", width=288),
        stat_chip(24, 158, "Following", following, "#8250DF", width=288),
        stat_chip(328, 158, "Total stars", total_stars, "#DA3633", width=288),
    ]

    return f'''<svg width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">All Repositories</title>
  <desc id="desc">Explore all of {escape(owner)}'s GitHub projects</desc>
  <rect x="1" y="1" width="{CARD_WIDTH - 2}" height="{CARD_HEIGHT - 2}" rx="18" fill="#0D1117" stroke="#30363D" stroke-width="2"/>
  <text x="24" y="50" fill="#58A6FF" font-size="34" font-weight="700" font-family="Segoe UI, Ubuntu, sans-serif">All Repositories</text>
  <text x="24" y="88" fill="#C9D1D9" font-size="22" font-family="Segoe UI, Ubuntu, sans-serif">Explore all of {escape(owner)}'s GitHub projects</text>
  {chips[0]}
  {chips[1]}
  {chips[2]}
  {chips[3]}
</svg>
'''


def write_cards(owner: str, out_dir: Path, token: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    repos_by_name = {
        repo["name"]: repo for repo in fetch_all_repos(owner=owner, token=token)
    }
    user = github_get(f"/users/{owner}", token=token)

    for name, description in FEATURED_REPOS:
        repo = repos_by_name.get(name)
        if not repo:
            continue
        card = make_repo_card(repo=repo, description=description)
        (out_dir / f"{name}.svg").write_text(card, encoding="utf-8")

    all_repos_card = make_all_repos_card(owner=owner, user=user, repos=list(repos_by_name.values()))
    (out_dir / "all-repos.svg").write_text(all_repos_card, encoding="utf-8")


def write_cards_from_data(owner: str, out_dir: Path, user: dict[str, Any], repos: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    repos_by_name = {repo["name"]: repo for repo in repos}

    for name, description in FEATURED_REPOS:
        repo = repos_by_name.get(name)
        if not repo:
            continue
        card = make_repo_card(repo=repo, description=description)
        (out_dir / f"{name}.svg").write_text(card, encoding="utf-8")

    all_repos_card = make_all_repos_card(owner=owner, user=user, repos=repos)
    (out_dir / "all-repos.svg").write_text(all_repos_card, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate profile SVG cards with live GitHub stats.")
    parser.add_argument("--owner", default="wallstop", help="GitHub username/organization.")
    parser.add_argument("--out-dir", default="assets/cards", help="Directory for generated SVG files.")
    parser.add_argument(
        "--data-file",
        default="",
        help="Optional JSON file with pre-fetched GitHub data: {'user': {...}, 'repos': [{...}]}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN")
    if args.data_file:
        payload = json.loads(Path(args.data_file).read_text(encoding="utf-8"))
        write_cards_from_data(
            owner=args.owner,
            out_dir=Path(args.out_dir),
            user=payload["user"],
            repos=payload["repos"],
        )
        return

    write_cards(owner=args.owner, out_dir=Path(args.out_dir), token=token)


if __name__ == "__main__":
    main()
