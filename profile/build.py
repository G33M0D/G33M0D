"""
Builds the GitHub profile card from public data and rewrites the README's featured-work list.

Reads only public sources: the xmodx.com JSON feed and homepage, and the GitHub public user API.
Writes dark_mode.svg, light_mode.svg and the block between the FEATURED markers in README.md.
Standard library only, so the workflow needs no installs.
"""
import datetime
import html
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://xmodx.com'
GITHUB_USER = 'G33M0D'

WIDTH, HEIGHT = 985, 500
TEXT_X, LINE_H, TOP = 400, 22, 34
COLS = 62  # characters per info line, dots included

THEMES = {
  'dark': {'bg': '#0e1012', 'panel': '#15181b', 'rule': '#262a2f', 'text': '#e6e9eb',
           'key': '#5dd6a1', 'value': '#c2c8cd', 'dots': '#3d444b', 'art': '#6b737b', 'accent': '#5dd6a1'},
  'light': {'bg': '#f3f4f5', 'panel': '#ffffff', 'rule': '#d5d9dd', 'text': '#101316',
            'key': '#0a6a47', 'value': '#343b42', 'dots': '#aab1b8', 'art': '#959da5', 'accent': '#0a6a47'},
}


def fetch(url, as_json=True):
  headers = {'User-Agent': 'G33M0D-profile-card'}
  if 'api.github.com' in url and os.environ.get('GITHUB_TOKEN'):
    headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
  with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
    body = r.read().decode('utf-8')
  return json.loads(body) if as_json else body


def plural(n, word):
  return f'{n} {word}' + ('' if n == 1 else 's')


def short_availability(text):
  """The site's availability sentence is too long for one card line."""
  t = text.rstrip('.')
  t = re.sub(r'\s*\(UTC[+-]\d+\)', '', t)
  t = t.replace('Currently engaged; open to', 'Engaged, open to').replace(' AI automation projects', ' projects')
  return t if len(t) <= 44 else t[:43] + '…'


def collect():
  profile = fetch(SITE + '/api/v1/profile.json')
  showcases = fetch(SITE + '/api/v1/showcases.json')
  index = fetch(SITE + '/api/v1/index.json')
  homepage = fetch(SITE + '/', as_json=False)
  user = fetch(f'https://api.github.com/users/{GITHUB_USER}')

  by_url = {s['url'].replace(SITE, ''): s for s in showcases}
  featured = []
  for path in re.findall(r'href="(/work/[a-z0-9-]+/)"', homepage):
    if path in by_url and by_url[path] not in featured:
      featured.append(by_url[path])

  avail = homepage_fact(homepage, 'Availability') or 'Open to select remote projects'
  location = homepage_fact(homepage, 'Location') or 'Philippines'
  since = datetime.date.fromisoformat(user['created_at'][:10])
  years = (datetime.date.today() - since).days // 365

  return {
    'headline': profile.get('headline', ''),
    'location': location + ' (UTC+8)',
    'availability': short_availability(avail),
    'showcases': len(showcases),
    'areas': len({s.get('section') for s in showcases}),
    'demos': sum(1 for s in showcases if s.get('demo')),
    'approvals': index.get('ledgerEntries', 0),
    'site_updated': index.get('builtAt', '')[:10],
    'github_since': f'{since.year} ({plural(years, "year")})',
    'public_repos': user.get('public_repos', 0),
    'featured': featured[:6],
  }


def homepage_fact(page, label):
  m = re.search(r'<dt[^>]*>\s*' + label + r'\s*</dt>\s*<dd[^>]*>(.*?)</dd>', page, re.S)
  return html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None


# ---------- SVG ----------

def ascii_logo():
  """Character art of the avatar emblem, made once by tools/make_art.py. Green cells use the accent."""
  with open(os.path.join(ROOT, 'profile', 'art.txt'), encoding='utf-8') as f:
    lines = f.read().rstrip('\n').split('\n')
  rows = []
  for chars, marks in zip(lines[0::2], lines[1::2]):
    row = []
    for ch, m in zip(chars, marks[1:]):
      cls = 'c' if m == 'g' else ('f' if ch in '%#@*+' else 'a')
      row.append((cls, ch))
    rows.append(row)
  return rows


def esc(s):
  return html.escape(str(s), quote=False)


def info_line(key, value):
  """'. Key: ........ value' padded with dots to COLS characters."""
  value = str(value)
  fill = COLS - len(key) - len(value) - 5
  if fill < 1:
    value = value[:max(1, len(value) + fill - 2)] + '…'
    fill = 1
  return ('<tspan class="d">. </tspan><tspan class="k">{}</tspan><tspan class="d">: {} </tspan>'
          '<tspan class="v">{}</tspan>').format(esc(key), '.' * fill, esc(value))


def header(title):
  rule = '—' * max(4, COLS - len(title) - 3)
  return f'<tspan class="t">{esc(title)}</tspan> <tspan class="d">-{rule}-</tspan>'


def card(data, theme):
  c = THEMES[theme]
  lines = [
    header('gee ~ xmodx.com'),
    info_line('Role', data['headline']),
    info_line('Location', data['location']),
    info_line('Status', data['availability']),
    info_line('Builds', 'AI agents with approval gates'),
    info_line('Also', 'MCP servers, Claude Code skills'),
    '',
    info_line('Stack.AI', 'Claude Code, Anthropic, OpenAI, Gemini'),
    info_line('Stack.Code', 'Python, TypeScript, SQL, Bash'),
    info_line('Stack.Cloud', 'Cloudflare Workers, Cloud Run, BigQuery'),
    '',
    header('- xmodx.com'),
    info_line('Showcases', f"{data['showcases']} across {data['areas']} areas"),
    info_line('Live demos', data['demos']),
    info_line('Signed approvals', f"{data['approvals']} (public record)"),
    info_line('Site updated', data['site_updated']),
    '',
    header('- GitHub'),
    info_line('Member since', data['github_since']),
    info_line('Public repos', f"{data['public_repos']} (most work is private)"),
  ]
  out = [f'<text x="{TEXT_X}" y="{TOP}">']
  for i, line in enumerate(lines):
    y = TOP + i * LINE_H
    out.append(f'<tspan x="{TEXT_X}" y="{y}">{line or " "}</tspan>')
  out.append('</text>')

  art = ['<text x="34" y="0" class="art">']
  for i, row in enumerate(ascii_logo()):
    y = 110 + i * 18
    spans, cur, buf = [], None, ''
    for cls, ch in row:
      if cls != cur and buf:
        spans.append(f'<tspan class="{cur}">{esc(buf)}</tspan>')
        buf = ''
      cur = cls
      buf += ch
    spans.append(f'<tspan class="{cur}">{esc(buf)}</tspan>')
    art.append(f'<tspan x="34" y="{y}">{"".join(spans)}</tspan>')
  art.append('</text>')

  foot_y = HEIGHT - 26
  return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Gee, {esc(data['headline'])}. Portfolio at xmodx.com">
<style>
text, tspan {{ white-space: pre; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 14px; }}
.t {{ fill: {c['text']}; font-weight: 700; }}
.k {{ fill: {c['key']}; }}
.v {{ fill: {c['value']}; }}
.d {{ fill: {c['dots']}; }}
.f {{ fill: {c['text']}; }}
.c {{ fill: {c['accent']}; }}
.a {{ fill: {c['art']}; }}
.art tspan {{ font-size: 15px; }}
.foot {{ fill: {c['dots']}; font-size: 12px; }}
</style>
<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="{c['panel']}" stroke="{c['rule']}"/>
<line x1="{TEXT_X - 22}" y1="24" x2="{TEXT_X - 22}" y2="{HEIGHT - 24}" stroke="{c['rule']}"/>
{chr(10).join(art)}
{chr(10).join(out)}
<text x="34" y="{foot_y}" class="foot">refreshed {datetime.date.today().isoformat()} from xmodx.com</text>
</svg>
'''


# ---------- README ----------

def featured_block(featured):
  lines = ['<!-- FEATURED:START (written by profile/build.py from the xmodx.com homepage) -->']
  for s in featured:
    summary = s.get('summary', '')
    first = re.split(r'(?<=\.)\s', summary, maxsplit=1)[0].rstrip('.')
    if len(first) > 160:
      first = first[:160].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    else:
      first += '.'
    lines.append(f"- **[{s['title']}]({s['url']})**  \n  {first}")
  lines.append('<!-- FEATURED:END -->')
  return '\n'.join(lines)


def main():
  data = collect()
  for theme in THEMES:
    with open(os.path.join(ROOT, f'{theme}_mode.svg'), 'w', encoding='utf-8') as f:
      f.write(card(data, theme))
  readme_path = os.path.join(ROOT, 'README.md')
  with open(readme_path, encoding='utf-8') as f:
    readme = f.read()
  readme = re.sub(r'<!-- FEATURED:START.*?<!-- FEATURED:END -->', lambda _: featured_block(data['featured']),
                  readme, flags=re.S)
  with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(readme)
  print(json.dumps({k: v for k, v in data.items() if k != 'featured'}, indent=1))
  print('featured:', [s['title'][:40] for s in data['featured']])


if __name__ == '__main__':
  main()
