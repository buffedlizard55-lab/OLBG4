# OLBG4 — Multi-sport line origination & picks dashboard

Automated pipeline that ingests **official league data** for the sports in scope, originates its
own betting lines, assigns picks with a confidence grade, and publishes a static dashboard.

- Live site: https://buffedlizard55-lab.github.io/OLBG4/
- Coordination board: [COORDINATION.md](COORDINATION.md)
- OLBG reverse-engineering notes: [docs/olbg-reverse-engineering.md](docs/olbg-reverse-engineering.md)
- Methodology: [docs/methodology.md](docs/methodology.md)

Everything under `data/`, `assets/` and the generated `*.html` pages at the repo root is produced by
`pipeline/run.py`. Do not hand-edit generated files.
