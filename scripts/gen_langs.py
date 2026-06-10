#!/usr/bin/env python3
"""Generate a most-used-languages SVG across ALL repos the token can see
(own + private + org), weighting each repo equally so a few huge generated
codebases (e.g. Flutter) don't drown out everything else."""
import json
import os
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ["GH_TOKEN"]

IGNORE = {
    "HTML", "CSS", "SCSS", "Jupyter Notebook", "Makefile", "Dockerfile",
    "CMake", "Batchfile", "PowerShell", "Objective-C", "Swift", "Ruby",
    "Roff", "TeX",
}

COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Dart": "#00B4AB", "Java": "#b07219", "Rust": "#dea584",
    "C++": "#f34b7d", "C": "#555555", "Go": "#00ADD8", "Kotlin": "#A97BFF",
    "Vue": "#41b883", "Solidity": "#AA6746", "Shell": "#89e051",
    "PLpgSQL": "#336790", "Jinja": "#a52a22", "TSX": "#3178c6",
}
FALLBACK_COLOR = "#8b949e"

QUERY = """
query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor,
                 ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
      pageInfo { hasNextPage endCursor }
      nodes { languages(first: 10) { edges { size node { name } } } }
    }
  }
}
"""


def gql(cursor):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"cursor": cursor}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    body = json.loads(urllib.request.urlopen(req).read())
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["viewer"]["repositories"]


agg, cursor, repo_count = {}, None, 0
while True:
    page = gql(cursor)
    for repo in page["nodes"]:
        edges = [e for e in (repo["languages"]["edges"] or [])
                 if e["node"]["name"] not in IGNORE]
        total = sum(e["size"] for e in edges)
        if not total:
            continue
        repo_count += 1
        for e in edges:
            name = e["node"]["name"]
            agg[name] = agg.get(name, 0) + e["size"] / total
    if not page["pageInfo"]["hasNextPage"]:
        break
    cursor = page["pageInfo"]["endCursor"]

grand_total = sum(agg.values())
top = sorted(agg.items(), key=lambda kv: -kv[1])[:8]

WIDTH, BAR_W, BAR_X = 480, 430, 25
rows = (len(top) + 1) // 2
height = 110 + rows * 24

now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
    f'viewBox="0 0 {WIDTH} {height}" fill="none" role="img">',
    f'<rect width="{WIDTH}" height="{height}" rx="6" fill="#0d1117"/>',
    '<text x="25" y="32" font-family="Segoe UI, Ubuntu, sans-serif" '
    'font-weight="600" font-size="17" fill="#70a5fd">Most Used Languages</text>',
    f'<text x="25" y="52" font-family="Segoe UI, Ubuntu, sans-serif" '
    f'font-size="11.5" fill="#8b949e">{repo_count} repos · private &amp; org '
    f'included · each repo weighted equally · {now}</text>',
]

# stacked bar
x = BAR_X
parts.append(f'<defs><clipPath id="bar"><rect x="{BAR_X}" y="66" width="{BAR_W}" '
             'height="10" rx="5"/></clipPath></defs><g clip-path="url(#bar)">')
for name, share in top:
    w = share / grand_total * BAR_W
    parts.append(f'<rect x="{x:.1f}" y="66" width="{w + 1.5:.1f}" height="10" '
                 f'fill="{COLORS.get(name, FALLBACK_COLOR)}"/>')
    x += w
parts.append("</g>")

# legend, two columns
for i, (name, share) in enumerate(top):
    cx = 25 if i % 2 == 0 else 255
    cy = 100 + (i // 2) * 24
    pct = share / grand_total * 100
    parts.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" '
                 f'fill="{COLORS.get(name, FALLBACK_COLOR)}"/>')
    parts.append(f'<text x="{cx + 18}" y="{cy}" font-family="Segoe UI, Ubuntu, '
                 f'sans-serif" font-size="13" fill="#c9d1d9">{name} '
                 f'<tspan fill="#8b949e">{pct:.1f}%</tspan></text>')

parts.append("</svg>")
print("\n".join(parts))
