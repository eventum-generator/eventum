<p align="center">
  <img src="https://raw.githubusercontent.com/eventum-generator/eventum/master/static/logo.svg" alt="Eventum" width="120" />
</p>

<h1 align="center">Eventum</h1>

<p align="center">
  <strong>
    Data generation platform
  </strong>
</p>

<p align="center">
  <a href="https://github.com/eventum-generator/eventum/actions/workflows/ci.yml"><img src="https://github.com/eventum-generator/eventum/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://codecov.io/gh/eventum-generator/eventum"><img src="https://codecov.io/gh/eventum-generator/eventum/graph/badge.svg" alt="Coverage" /></a>
  <a href="https://pypi.org/project/eventum-generator"><img src="https://img.shields.io/pypi/v/eventum-generator?color=8282ef" alt="PyPI" /></a>
  <a href="https://pypi.org/project/eventum-generator"><img src="https://img.shields.io/pypi/pyversions/eventum-generator?color=8282ef" alt="Python" /></a>
  <a href="https://hub.docker.com/r/rnv812/eventum-generator"><img src="https://img.shields.io/docker/v/rnv812/eventum-generator?label=docker&color=8282ef" alt="Docker" /></a>
  <a href="https://github.com/eventum-generator/eventum/blob/master/LICENSE"><img src="https://img.shields.io/github/license/eventum-generator/eventum?color=8282ef" alt="License" /></a>
</p>

<p align="center">
  <a href="https://eventum.run"><strong>Documentation</strong></a> &nbsp;·&nbsp;
  <a href="https://eventum.run/docs/tutorials"><strong>Tutorials</strong></a> &nbsp;·&nbsp;
  <a href="https://eventum.run/docs/api"><strong>API Reference</strong></a> &nbsp;·&nbsp;
  <a href="https://github.com/eventum-generator/eventum/blob/master/CHANGELOG.md"><strong>Changelog</strong></a> &nbsp;·&nbsp;
  <a href="https://github.com/orgs/eventum-generator/projects/4"><strong>Task tracker</strong></a>  &nbsp;·&nbsp;
  <a href="https://github.com/orgs/eventum-generator/discussions"><strong>Discuss</strong></a>
</p>

---

Eventum produces synthetic events and delivers them anywhere — in real time or in batch. Generate a continuous stream of logs for your SIEM, seed a staging database with realistic data, or stress-test a pipeline with high-throughput traffic. Define everything in YAML, no code required.

<p align="center">
  <img src="https://raw.githubusercontent.com/eventum-generator/eventum/master/.github/assets/pipeline.svg" alt="Input → Event → Output pipeline" width="680" />
</p>

## ✨ Highlights

🎭 **Realistic data** — Jinja2 templates with [Faker](https://faker.readthedocs.io/) and [Mimesis](https://mimesis.name/) generate believable names, IPs, timestamps, and domain-specific values

🕐 **Flexible scheduling** — cron expressions, fixed intervals, or statistical time patterns that mimic real-world traffic curves

📤 **Multiple destinations** — fan-out to stdout, files, ClickHouse, OpenSearch, or any HTTP endpoint simultaneously

🔀 **Two modes** — stream events in real time at their scheduled timestamps, or generate everything as fast as possible

🖥️ **Built-in web UI** — [Eventum Studio](https://eventum.run) for visual editing, event preview, and monitoring

⚡ **REST API** — start, stop, and manage generators programmatically

🔒 **Encrypted secrets** — credentials stored securely via an encrypted keyring

🐳 **Docker ready** — multi-stage builds, runs anywhere

## 🚀 Quick start

**Install**

```bash
pip install eventum-generator
```

> Also available via [uv](https://docs.astral.sh/uv/) (`uv tool install eventum-generator`) or [Docker](https://hub.docker.com/r/rnv812/eventum-generator) (`docker pull rnv812/eventum-generator`).

**Create a template** — `events.jinja`

```jinja
{{ timestamp }} INFO  user={{ module.faker.locale.en.user_name() }} action=login ip={{ module.faker.locale.en.ipv4() }}
```

**Create a config** — `generator.yml`

```yaml
input:
  - cron:
      expression: "* * * * * *"
      count: 1

event:
  template:
    mode: all
    templates:
      - my_event:
          template: events.jinja

output:
  - stdout: {}
```

**Run**

```bash
eventum generate --path generator.yml --live-mode
```

```
2026-02-23 12:00:01+00:00 INFO  user=jsmith action=login ip=192.168.44.12
2026-02-23 12:00:02+00:00 INFO  user=amiller action=login ip=10.0.128.55
2026-02-23 12:00:03+00:00 INFO  user=kwilson action=login ip=172.16.0.91
```


## 🔌 Plugins

Each part of the pipeline is a plugin. Swap, combine, or extend — change the schedule without touching templates, add new outputs without modifying anything else. See the [plugin reference](https://eventum.run/docs/plugins) for the full list.

## 🖥️ Application mode

Run multiple generators with a web UI and REST API:

```bash
eventum run -c eventum.yml
```

Starts on port **9474** with **Eventum Studio** (web UI), **REST API**, and **multi-generator orchestration** — each generator runs independently with its own schedule, templates, and outputs.

## 📖 Documentation

Full documentation at **[eventum.run](https://eventum.run)**:

- [Getting started](https://eventum.run/docs) — overview and first example
- [Installation](https://eventum.run/docs/core/introduction/installation) — pip, Docker, or from source
- [Core concepts](https://eventum.run/docs/core/concepts/generator) — pipeline, plugins, scheduling
- [Plugin reference](https://eventum.run/docs/plugins) — every plugin with full parameter tables
- [Tutorials](https://eventum.run/docs/tutorials) — end-to-end walkthroughs (SIEM, clickstream, IoT, and more)

## 📄 License

[Apache License 2.0](LICENSE)
