# Native approval acceptance fixture

Install this separate plugin only in an isolated live test home. It requests the
host's ordinary human approval for `terminal` commands starting with
`printf CAT916_APPROVAL_`. It never grants approvals or executes commands itself.

```bash
cp -R tests/fixtures/approval_gate "$HERMES_HOME/plugins/catalog-acceptance-gate"
hermes plugins validate "$HERMES_HOME/plugins/catalog-acceptance-gate"
hermes plugins enable catalog-acceptance-gate
```

Restart the test Gateway. Ask it to run `printf CAT916_APPROVAL_ONCE`; verify the
Catalog waiting status, choose the native **Once** button, then verify the final
reply. Repeat with `printf CAT916_APPROVAL_DENY` and **Deny**. Use a distinct marker
for each run so session/permanent approval decisions cannot affect another case.
Use manual approval mode for this test. An untouched request can also test the
host's configured approval timeout.

After testing, disable and remove `catalog-acceptance-gate`, then restart the
Gateway. This fixture is excluded from the Catalog ZIP by its build allowlist.
