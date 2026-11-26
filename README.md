# Gumption

Self-hosted observability for background task queues: Celery first, any queue
through an SDK. One Go binary, PostgreSQL + ClickHouse, and a React UI built
only on the public API. Design: [`docs/design.md`](docs/design.md).

**Status:** pre-alpha. The binary only prints its version so far; see `feature_list.json` for the plan.

## How this repository is run

Gumption is built and maintained by AI agents. Humans set direction, own the
contracts, and answer the questions in [`DECISIONS.md`](DECISIONS.md).

- Agents start at [`AGENTS.md`](AGENTS.md).
- The operating model is in [`docs/harness/`](docs/harness/README.md).
- Progress: [`claude-progress.md`](claude-progress.md).

## Development

The toolchain (Go, Node, Python, just, golangci-lint) is pinned in
[`mise.toml`](mise.toml). Install [mise](https://mise.jdx.dev), then:

```bash
./init.sh                     # install pinned tools, run `just check`
just check                    # every verification step (CI runs the same)
just run version              # go run ./cmd/gumption version
just --list                   # all recipes
```

If mise is not activated in your shell, prefix commands with `mise exec --`.
