<!-- BEGIN WING-GENERATED -->
## Wing IDE project guides

Read `.wing/guides.md` before creating or changing files here: it has
the project's rules and how to use Wing's MCP servers.  Detail
files sit beside it in `.wing/`, also served by the `wing_guide` tool.

Always, read or not.  These tools are on the `wing-review` MCP
server, and your tool list names them with the server added (as
`wing-review__create_tracked_file` or `wing-review-create_tracked_file`),
so look for the name within it:
- A new file to be tracked: `create_tracked_file`, never your own
  file-creation tool, which leaves the file untracked.
- Commit only when asked (unless `.wing/guides.md` says this
  project commits on its own), and only with `vcs_commit`, never
  git or hg commit.
- Never call `review_start` unless asked to.

Wing generates this block and rewrites it in place; edit your own
content above or below the markers.
<!-- END WING-GENERATED -->
