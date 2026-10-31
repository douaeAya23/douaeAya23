import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape

PROFILE_URL = "https://github.com/douaeAya23"
USERNAME = os.environ.get("GITHUB_USERNAME") or PROFILE_URL.rstrip("/").split("/")[-1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = "assets/generated/github-stats.svg"

# Palette
GOLD = "#C9A24D"         
GOLD_LIGHT = "#F0D98C"    
GOLD_DARK = "#B8893A"    
PLUM = "#3F2A6B"       
VIOLET = "#5B3E96"       
MAUVE = "#7A5CB8"      
GREY = "#8A7BA8"        
LILAC = "#B7A4E3"      
LILAC_SOFT = "#E5D7F8"  
LILAC_MIST = "#F3EAFC"  
LILAC_RING = "#D9C6F5"  
LILAC_TRACK = "#EFE3FB"   
ROSE = "#E3B5CF"     
BG_END = "#FAF6FE" 
LANG_COLORS = [GOLD, MAUVE, LILAC, VIOLET, ROSE]
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Arial, sans-serif"

def graphql(query, variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_contributions():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    data = graphql(query, {"login": USERNAME})
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
    today = datetime.now(timezone.utc).date()
    days = [d for d in days if datetime.fromisoformat(d["date"]).date() <= today]

    longest = running = 0
    for day in days:
        running = running + 1 if day["contributionCount"] > 0 else 0
        longest = max(longest, running)

    current = 0
    for index, day in enumerate(reversed(days)):
        if day["contributionCount"] > 0:
            current += 1
        elif index == 0:
            continue
        else:
            break
    return calendar["totalContributions"], current, longest

def fetch_top_languages(limit=5):
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }"""
    data = graphql(query, {"login": USERNAME})
    totals = {}
    for repo in data["user"]["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
    grand_total = sum(size for _, size in ranked) or 1
    return [
        {"name": name, "pct": round(size / grand_total * 100, 1), "color": LANG_COLORS[i % len(LANG_COLORS)]}
        for i, (name, size) in enumerate(ranked)
    ]


def metric(x, label, value, caption, value_size=46):
    return f"""
  <g transform="translate({x},48)">
    <text x="0" y="0" font-family="{SANS}" font-size="13" letter-spacing=".3" fill="{MAUVE}">{escape(label)}</text>
    <text x="0" y="52" font-family="{SERIF}" font-size="{value_size}" fill="{PLUM}">{escape(str(value))}</text>
    <text x="0" y="76" font-family="{SANS}" font-size="12" letter-spacing=".3" fill="{GREY}">{escape(caption)}</text>
  </g>"""


def language_bar(languages, x, y, width):
    segments, legend = [], []
    cursor = x
    for i, lang in enumerate(languages):
        seg_width = width * lang["pct"] / 100
        segments.append(f'<rect x="{cursor:.1f}" y="{y}" width="{seg_width:.1f}" height="8" fill="{lang["color"]}"/>')
        cursor += seg_width
        lx = x + i * 175
        legend.append(
            f'<circle cx="{lx + 5}" cy="{y + 30}" r="4" fill="{lang["color"]}"/>'
            f'<text x="{lx + 16}" y="{y + 34}" font-family="{SANS}" font-size="12" fill="{PLUM}">'
            f'{escape(lang["name"])} · {lang["pct"]} %</text>'
        )
    return f"""
  <rect x="{x}" y="{y}" width="{width}" height="8" rx="4" fill="{LILAC_TRACK}"/>
  <clipPath id="barClip"><rect x="{x}" y="{y}" width="{width}" height="8" rx="4"/></clipPath>
  <g clip-path="url(#barClip)">{''.join(segments)}</g>
  {''.join(legend)}"""


def build_svg(total, current, longest, languages):
    width, height = 1000, 250
    top_language = languages[0]["name"] if languages else "—"
    # Les noms de langages longs (ex. « TypeScript ») sont réduits pour tenir dans la colonne
    language_size = 46 if len(top_language) <= 5 else 34 if len(top_language) <= 9 else 28
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Statistiques GitHub">
  <title>Statistiques GitHub</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="{BG_END}"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{GOLD}"/><stop offset=".5" stop-color="{GOLD_LIGHT}"/><stop offset="1" stop-color="{GOLD}"/>
    </linearGradient>
    <linearGradient id="goldd" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{GOLD}"/><stop offset=".5" stop-color="{GOLD_LIGHT}"/><stop offset="1" stop-color="{GOLD_DARK}"/>
    </linearGradient>
    <path id="spark" d="M0,-1 C0.12,-0.3 0.3,-0.12 1,0 C0.3,0.12 0.12,0.3 0,1 C-0.12,0.3 -0.3,0.12 -1,0 C-0.3,-0.12 -0.12,-0.3 0,-1Z"/>
    <clipPath id="cardClip"><rect width="{width}" height="{height}" rx="14"/></clipPath>
  </defs>
  <rect width="{width}" height="{height}" rx="14" fill="url(#bg)"/>
  <g clip-path="url(#cardClip)">
    <path d="M{width},0 H{width - 150} C{width - 175},50 {width - 120},120 {width - 150},{height} H{width} Z" fill="{LILAC_MIST}"/>
    <path d="M0,{height} H170 C140,{height - 40} 190,{height - 90} 150,{height - 130} C110,{height - 150} 40,{height - 130} 0,{height - 170} Z" fill="{LILAC_SOFT}" fill-opacity="0.55"/>
  </g>
  <rect x="5" y="5" width="{width - 10}" height="{height - 10}" rx="10" fill="none" stroke="url(#gold)" stroke-width="1.2"/>
  <circle cx="{width - 48}" cy="40" r="26" fill="none" stroke="{LILAC_RING}" stroke-width="1.6" stroke-dasharray="1 6" stroke-linecap="round"/>
  <use href="#spark" transform="translate({width - 48} 40) scale(6)" fill="{GOLD}"/>
  <use href="#spark" transform="translate({width - 86} 24) scale(4)" fill="{GOLD_LIGHT}"/>
  <use href="#spark" transform="translate(30 26) scale(6)" fill="{GOLD_LIGHT}"/>
  {metric(48, "Contributions", total, "12 derniers mois")}
  {metric(300, "Série actuelle", f"{current} j", "jours consécutifs")}
  {metric(540, "Plus longue série", f"{longest} j", "sur 12 mois")}
  {metric(790, "Langage principal", top_language, "dépôts personnels", value_size=language_size)}
  <rect x="48" y="156" width="60" height="2.5" rx="1.25" fill="url(#gold)"/>
  <text x="48" y="182" font-family="{SANS}" font-size="13" letter-spacing=".3" fill="{MAUVE}">Répartition des langages</text>
  {language_bar(languages, 48, 196, width - 96)}
  <text x="{width - 24}" y="{height - 14}" text-anchor="end" font-family="{SANS}" font-size="10" fill="{GREY}">Mis à jour le {updated}</text>
</svg>"""


def main():
    if not TOKEN:
        sys.exit("Erreur : GITHUB_TOKEN manquant (secret METRICS_TOKEN dans le workflow).")
    total, current, longest = fetch_contributions()
    languages = fetch_top_languages()
    if not languages:
        sys.exit("Erreur : aucun langage récupéré (vérifier les droits du jeton).")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(build_svg(total, current, longest, languages))
    print(f"{OUTPUT} généré pour {USERNAME}")


if __name__ == "__main__":
    main()