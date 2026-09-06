# Releasing st-supabase-connection

The release workflow uses PyPI Trusted Publishing. It does not need a PyPI username,
password, or long-lived API token.

## One-time setup

1. Merge `.github/workflows/publish_PYPI_each_tag.yml` into the default branch.
2. In the GitHub repository settings, create environments named `testpypi` and `pypi`.
3. Require manual approval for the `pypi` environment. Restrict it to release tags such as
   `v*` if the repository's GitHub plan supports deployment tag restrictions.
4. On the existing PyPI project, open **Manage > Publishing** and add a GitHub Actions
   trusted publisher with these values:

   - Owner: `SiddhantSadangi`
   - Repository: `st_supabase_connection`
   - Workflow: `publish_PYPI_each_tag.yml`
   - Environment: `pypi`

5. Configure the same publisher on TestPyPI, using the `testpypi` environment. If the
   project does not exist there yet, create a pending publisher for
   `st-supabase-connection`.
6. Delete the obsolete `PYPI_USERNAME` and `PYPI_PASSWORD` GitHub secrets, if present,
   and revoke any superseded PyPI API tokens.

PyPI and TestPyPI accounts are separate. Both publishers must be configured before their
corresponding jobs can authenticate.

## Rehearse on TestPyPI

1. Open **Actions > Publish Python package > Run workflow** on the default branch.
2. The workflow runs all library and demo tests, builds and validates both distributions,
   and publishes only to TestPyPI.
3. Verify the uploaded version in a clean environment:

   ```bash
   python -m pip install \
     --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     st-supabase-connection==2.2.0
   ```

TestPyPI does not allow replacing a file with the same project name and version. Bump the
version before rerunning if `2.2.0` has already been uploaded there.

## Publish to PyPI

Before publishing, run a brief browser smoke test against the updated demo:

- Sign in, read Database and Storage results, sign out, and return to both workspaces:
  previous results and downloads must be gone. Repeat with a different account.
- Review a write, check that an incorrect phrase cannot confirm it, then cancel.
  Confirm only against a disposable test target; verify the result and clean up.
- Confirm fresh reads are the default and cached reads can be enabled explicitly.
- Check sidebar navigation and the version display at desktop and narrow window widths.

AppTest covers server-side state transitions but is not a substitute for checking
the actual dialog lifecycle and layout in a browser.

1. Confirm CI passes on the release commit.
2. Confirm `src/st_supabase_connection/__init__.py` contains the intended version.
3. Create and publish a GitHub Release using the matching tag, such as `v2.2.0`.
4. Approve the `pypi` environment deployment after reviewing the build job.
5. Verify the release on PyPI and install it in a clean environment.

The workflow rejects a GitHub Release whose tag does not match the package version. Both
`2.2.0` and `v2.2.0` tag formats are accepted.
