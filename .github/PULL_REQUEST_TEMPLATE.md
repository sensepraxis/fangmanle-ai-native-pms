## Summary

<!-- Why this change exists -->

## Checklist

- [ ] OpenCore still starts / smokes with `FML_COMMERCIAL=0`
- [ ] LLM sessions are not a hard OpenCore dependency
- [ ] `ruff check src` · `ruff format --check src tools` · frontend `npm run lint` + `npm run format:check` · `pytest` (`pytest -m "not commercial"` for OpenCore)
- [ ] User-visible behavior is noted in `CHANGELOG.md` (and `CHANGELOG_zh.md` if you maintain the Chinese copy)
- [ ] Commits are DCO signed-off (`git commit -s`)

OpenCore is Apache-2.0; `src/commercial/` is BUSL. After a fork, point `pyproject.toml` `[project.urls]` at your repo.

Commits: [Conventional Commits](https://www.conventionalcommits.org/) — see [CONTRIBUTING.md](../CONTRIBUTING.md).
