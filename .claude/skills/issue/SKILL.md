---
name: issue
description: File a GitHub issue in the eventum-generator org with the tracker sidebar filled in - issue type, board fields, assignee.
---

## Input

- What to file: a defect, a user-facing addition, or a piece of internal work. Usually the current session; sometimes a bare one-liner from the user.
- Target repository, if not `eventum`.

## Output

- Issue in `eventum-generator/<repo>` carrying a typed body, and on the [Task tracker](https://github.com/orgs/eventum-generator/projects/4) board with Type, Status, Priority, Component, Size and assignee set.

## When to use

Filing anything the tracker should hold: a bug found while working, a follow-up spotted during a review, a feature to plan. Not for a fix already in the working tree - commit it instead.

## Process

Six steps. Step 4 waits for the user, unless they already asked to file it without review.

### 1. Gather facts

Read the code before describing it. A body that names a file, a line, a log line or an actual traceback is worth filing; one that paraphrases symptoms is not. Reproduce the defect when it is cheap to reproduce.

Check for duplicates before drafting:

```bash
gh issue list --repo eventum-generator/<repo> --state all --limit 20 --search "<keywords>"
```

If a match exists, report it and stop - a comment on the open issue beats a second one.

### 2. Classify

| Field | Value |
|---|---|
| Type | `Bug` - behaviour contradicts what Eventum documents or promises. `Feature` - a capability that does not exist yet. `Improvement` - existing behaviour, docs or code made better: UX, performance, error messages, refactoring, tests, CI. The three are exhaustive; nothing else is filed |
| Component | `Eventum Studio` (`ui/`), `Core` (`core/`, `app/`), `Plugins` (`plugins/`), `API/MCP/CLI` (`api/`, `cli/`, `server/`, `mcp/`), `Other` (build, CI, docs repo) |
| Priority | `High` when data is lost, a release is blocked or a user is stuck with no workaround; `Low` for cosmetics and nice-to-haves; `Medium` otherwise |
| Size | `XS` one-line change, `S` one module plus a test, `M` several modules, `L` cross-cutting (backend plus UI plus docs), `XL` needs splitting first - propose the split instead of filing it |
| Status | Always `Backlog` |
| Assignee | `rnv812` unless the user says otherwise |

Pick Component from where the fix lands, not from where the symptom shows.

### 3. Draft

Title: a plain phrase naming the defect or the outcome, not the symptom - "Formatter rejections of individual events never reach the format_failed metric", not "metrics look wrong". No `[Bug]: ` prefix; the issue type carries the classification and shows on the board card.

Sections are `##`, chosen by type:

- **Bug** - `Summary`, `Reproduction`, `Root cause` (when found), `Impact` or `Why it matters`, `Fix`, `Related`
- **Feature** - `Summary`, `Current state`, `Scope`, `Out of scope`, `To sync`
- **Improvement** - `Summary`, `Current state`, `Impact`, `Scope` - take what applies

`Summary` always opens and carries the evidence - `path/file.py:120-125`, the failing snippet, the real log line. `Fix` names a direction, not a patch. `To sync` lists the cross-cutting artifacts the change drags along: OpenAPI schema, Zod schema, docs page, `CHANGELOG.md`, tests. `Related` links prior issues and PRs.

The forms under `.github/ISSUE_TEMPLATE/` define the minimum facts an issue has to carry, not its layout: what happens and how to reproduce it, the version, the area, and the config or log that shows it. Cover the same facts under the headings above - a filed issue that skips the reproduction path or the affected version is incomplete whichever way it was opened. The form's **Area** maps onto the board's `Component`, with `Documentation` and `Not sure` landing on `Other`.

Style follows `CLAUDE.md`: dense, factual, no marketing tone, single hyphen instead of an em dash, no AI attribution.

### 4. Confirm

Show the title, the body and every field from step 2 in one message, then wait. Skip only when the user has already said to file it without review.

### 5. Create and set fields

Write the body to a temporary file outside the repository and create the issue:

```bash
gh issue create --repo eventum-generator/<repo> \
    --title "<title>" \
    --body-file <tmpfile> \
    --assignee rnv812
```

No labels: the type classifies the issue, and `bug` / `feature` alongside it would be a second copy of the same fact. `duplicate` and `question` stay for triage.

`gh issue create` cannot set the issue type, and the board fields need the item id, so four calls follow. Set the type:

```bash
ISSUE_ID=$(gh api graphql -f query='
  { repository(owner: "eventum-generator", name: "<repo>") { issue(number: <n>) { id } } }
' --jq '.data.repository.issue.id')

gh api graphql -f query='
  mutation($issue: ID!, $type: ID!) {
    updateIssueIssueType(input: {issueId: $issue, issueTypeId: $type}) {
      issue { issueType { name } }
    }
  }
' -f issue="$ISSUE_ID" -f type=<type-id>
```

Put the issue on the board and take its item id. The call is idempotent - it returns the existing item when a board automation already added the issue, and creates no duplicate:

```bash
ITEM_ID=$(gh project item-add 4 --owner eventum-generator \
    --url https://github.com/eventum-generator/<repo>/issues/<n> \
    --format json --jq '.id')
```

Then set each of the four fields:

```bash
gh project item-edit --project-id PVT_kwDOCiUXlc4BP0JC --id "$ITEM_ID" \
    --field-id <field-id> --single-select-option-id <option-id>
```

### 6. Verify

Read back what was actually set - a failed mutation is silent in a chain of four calls:

```bash
gh api graphql -f query='
{
  repository(owner: "eventum-generator", name: "<repo>") {
    issue(number: <n>) {
      issueType { name }
      assignees(first: 5) { nodes { login } }
      projectItems(first: 5) {
        nodes {
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
        }
      }
    }
  }
}' --jq '.data.repository.issue | {type: .issueType.name, assignees: [.assignees.nodes[].login], fields: [.projectItems.nodes[].fieldValues.nodes[] | select(.name) | {(.field.name): .name}]}'
```

Every one of Type, Status, Priority, Component, Size and the assignee must come back non-empty. Fix what is missing, then report the issue URL.

## Identifiers

Verified 2026-08-08. Issue types and the board are org-level, so the same ids serve `eventum`, `docs` and `content-packs`.

| Entity | Id |
|---|---|
| Project (Task tracker, number 4) | `PVT_kwDOCiUXlc4BP0JC` |
| Issue type Improvement / Bug / Feature | `IT_kwDOCiUXlc4BVM0X` / `IT_kwDOCiUXlc4BVM0Y` / `IT_kwDOCiUXlc4BVM0Z` |
| Field Status | `PVTSSF_lADOCiUXlc4BP0JCzg-HW5U` - Backlog `f75ad846`, Todo `61e4505c`, In progress `47fc9ee4`, Done `98236657` |
| Field Priority | `PVTSSF_lADOCiUXlc4BP0JCzg-HXEM` - High `79628723`, Medium `0a877460`, Low `da944a9c` |
| Field Component | `PVTSSF_lADOCiUXlc4BP0JCzg-HX4I` - Eventum Studio `5a9396fe`, Core `73c7da0c`, Plugins `b0be8b34`, API/MCP/CLI `a93c596c`, Other `79a07051` |
| Field Size | `PVTSSF_lADOCiUXlc4BP0JCzg-HXEQ` - XS `6c6483d2`, S `f784b110`, M `7515a9f1`, L `817d0097`, XL `db339eb2` |

If a mutation rejects an id, re-fetch and update this table:

```bash
gh project field-list 4 --owner eventum-generator --format json
gh api graphql -f query='
  { repository(owner: "eventum-generator", name: "eventum") { issueTypes(first: 10) { nodes { name id } } } }
'
```

## Notes

- The forms carry a hardcoded version list. The `release` skill adds the new minor to `.github/ISSUE_TEMPLATE/bug_report.yml` and drops the oldest.
- GitHub's Relationships sidebar has no public API. Express dependencies in the body (`Blocked by #N`, `Unblocks #N`); they show up in the timeline.
- Milestones stay unset - the tracker does not use them.
- Implementation belongs to the `implement-issue` skill. This one stops at the filed issue.
