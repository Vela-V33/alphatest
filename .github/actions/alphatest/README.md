# AlphaTest GitHub Action

AI-powered autonomous testing for your web applications. Run AlphaTest in your CI/CD pipeline with GitHub Actions.

## Usage

### Basic Example

```yaml
name: AlphaTest CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run AlphaTest
        uses: ./.github/actions/alphatest
        with:
          api-key: ${{ secrets.ALPHATEST_API_KEY }}
          project-id: 'your-project-id'
```

### Advanced Example

```yaml
name: AlphaTest CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write  # Required for PR comments

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          # Your deployment script here
          echo "Deploying to staging..."

      - name: Run AlphaTest
        uses: ./.github/actions/alphatest
        with:
          api-key: ${{ secrets.ALPHATEST_API_KEY }}
          project-id: 'your-project-id'
          base-url: 'https://staging.yourapp.com'
          specs: 'login-flow,checkout-flow,user-profile'
          fail-on-error: 'true'
          comment-on-pr: 'true'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-key` | AlphaTest API key (get from dashboard) | Yes | - |
| `project-id` | Project ID to run tests for | Yes | - |
| `base-url` | Base URL to test (overrides project URL) | No | Project URL |
| `specs` | Comma-separated list of spec IDs to run | No | `all` |
| `fail-on-error` | Fail the workflow if tests fail | No | `true` |
| `wait-for-completion` | Wait for tests to complete | No | `true` |
| `timeout` | Maximum time to wait (in minutes) | No | `30` |
| `comment-on-pr` | Post test results as PR comment | No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `report-url` | URL to the test report |
| `passed` | Number of tests that passed |
| `failed` | Number of tests that failed |
| `total` | Total number of tests run |
| `success` | Overall test success (true/false) |

## Setup

### 1. Get Your API Key

1. Go to your AlphaTest dashboard
2. Navigate to Settings → API Keys
3. Click "Generate New API Key"
4. Copy the API key (starts with `at_`)

### 2. Add API Key to GitHub Secrets

1. Go to your repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `ALPHATEST_API_KEY`
4. Value: Paste your API key
5. Click "Add secret"

### 3. Get Your Project ID

1. Go to your AlphaTest dashboard
2. Open your project
3. The project ID is in the URL: `https://alphatest.dev/project/{PROJECT_ID}`

### 4. Create Workflow File

Create `.github/workflows/alphatest.yml` in your repository:

```yaml
name: AlphaTest
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/alphatest
        with:
          api-key: ${{ secrets.ALPHATEST_API_KEY }}
          project-id: 'YOUR_PROJECT_ID'
```

## Examples

### Run Specific Tests

```yaml
- uses: ./.github/actions/alphatest
  with:
    api-key: ${{ secrets.ALPHATEST_API_KEY }}
    project-id: 'my-app'
    specs: 'login,signup,checkout'  # Only run these specs
```

### Test Staging Environment

```yaml
- uses: ./.github/actions/alphatest
  with:
    api-key: ${{ secrets.ALPHATEST_API_KEY }}
    project-id: 'my-app'
    base-url: 'https://staging.myapp.com'
```

### Don't Fail on Test Failures

Useful for running tests but not blocking the build:

```yaml
- uses: ./.github/actions/alphatest
  with:
    api-key: ${{ secrets.ALPHATEST_API_KEY }}
    project-id: 'my-app'
    fail-on-error: 'false'
```

### Trigger Tests Without Waiting

Useful for long-running test suites:

```yaml
- uses: ./.github/actions/alphatest
  with:
    api-key: ${{ secrets.ALPHATEST_API_KEY }}
    project-id: 'my-app'
    wait-for-completion: 'false'
```

### Use Outputs

```yaml
- name: Run AlphaTest
  id: alphatest
  uses: ./.github/actions/alphatest
  with:
    api-key: ${{ secrets.ALPHATEST_API_KEY }}
    project-id: 'my-app'

- name: Check Results
  run: |
    echo "Tests passed: ${{ steps.alphatest.outputs.passed }}"
    echo "Tests failed: ${{ steps.alphatest.outputs.failed }}"
    echo "Report URL: ${{ steps.alphatest.outputs.report-url }}"
```

## PR Comments

When `comment-on-pr` is enabled and `GITHUB_TOKEN` is available, AlphaTest will automatically post test results as a comment on your pull request:

<img src="https://via.placeholder.com/600x300/1e293b/10b981?text=AlphaTest+PR+Comment+Example" alt="PR Comment" />

The comment includes:
- ✅ / ❌ Overall test status
- Number of passed/failed tests
- Link to full report

## Troubleshooting

### "Invalid API key" error

- Make sure your API key is correct and starts with `at_`
- Check that the secret name matches exactly: `ALPHATEST_API_KEY`
- Regenerate your API key if needed

### "Project not found" error

- Verify the project ID is correct
- Make sure the API key belongs to the user who owns the project

### Tests timing out

- Increase the `timeout` value
- Or set `wait-for-completion: 'false'` to trigger tests without waiting

### PR comments not working

- Make sure `GITHUB_TOKEN` is set in environment variables
- Add `permissions: pull-requests: write` to your job

## Support

- 📖 [Documentation](https://docs.alphatest.dev)
- 💬 [Discord Community](https://discord.gg/alphatest)
- 📧 [Email Support](mailto:support@alphatest.dev)
- 🐛 [Report Issues](https://github.com/your-org/alphatest/issues)

## License

MIT
