FloodConnect extension context — thin pointer only, no copied content.

- Usage skill (CLI/MCP tool names, install, call contract): `skills/floodconnect/SKILL.md`
- Method skill (the Sandwich reasoning rules themselves, runnable with no repo at all): `skills/floodconnect-method/SKILL.md`
- Repo entrypoint for any AI: `AI.md` (repo root)

Both skills under `skills/` are auto-discovered by Gemini CLI; this file exists only
so a client requiring a context file has one to load, and it never restates their
content -- read the two files above directly.
