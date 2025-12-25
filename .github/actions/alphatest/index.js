const core = require('@actions/core');
const github = require('@actions/github');
const axios = require('axios');

async function run() {
  try {
    // Get inputs
    const apiKey = core.getInput('api-key', { required: true });
    const projectId = core.getInput('project-id', { required: true });
    const baseUrl = core.getInput('base-url');
    const specs = core.getInput('specs') || 'all';
    const failOnError = core.getInput('fail-on-error') === 'true';
    const waitForCompletion = core.getInput('wait-for-completion') === 'true';
    const timeout = parseInt(core.getInput('timeout') || '30');
    const commentOnPR = core.getInput('comment-on-pr') === 'true';

    // AlphaTest API endpoint (update with your actual domain)
    const alphatestUrl = process.env.ALPHATEST_URL || 'https://alphatest.dev';

    core.info('🚀 Starting AlphaTest run...');
    core.info(`Project ID: ${projectId}`);
    if (baseUrl) core.info(`Base URL: ${baseUrl}`);
    core.info(`Specs: ${specs}`);

    // Trigger test run via API
    const triggerResponse = await axios.post(
      `${alphatestUrl}/api/v1/run`,
      {
        project_id: projectId,
        base_url: baseUrl || undefined,
        specs: specs === 'all' ? undefined : specs.split(',').map(s => s.trim()),
        source: 'github-actions',
        metadata: {
          repository: github.context.payload.repository?.full_name,
          branch: github.context.ref?.replace('refs/heads/', ''),
          commit: github.context.sha,
          pr: github.context.payload.pull_request?.number,
          actor: github.context.actor,
          workflow: github.context.workflow,
          run_id: github.context.runId
        }
      },
      {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const runId = triggerResponse.data.run_id;
    const reportUrl = `${alphatestUrl}/reports/${projectId}/${runId}`;

    core.info(`✅ Test run started: ${runId}`);
    core.info(`📊 Report URL: ${reportUrl}`);

    if (!waitForCompletion) {
      core.setOutput('report-url', reportUrl);
      core.info('⏭️  Not waiting for completion (wait-for-completion=false)');
      return;
    }

    // Poll for completion
    core.info('⏳ Waiting for tests to complete...');
    const startTime = Date.now();
    const timeoutMs = timeout * 60 * 1000;
    let testResult = null;

    while (Date.now() - startTime < timeoutMs) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Poll every 5 seconds

      const statusResponse = await axios.get(
        `${alphatestUrl}/api/v1/run/${runId}/status`,
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`
          }
        }
      );

      const status = statusResponse.data;

      if (status.completed) {
        testResult = status;
        break;
      }

      core.info(`⏳ Status: ${status.progress || 'Running'}...`);
    }

    if (!testResult) {
      throw new Error(`Test run timed out after ${timeout} minutes`);
    }

    // Set outputs
    core.setOutput('report-url', reportUrl);
    core.setOutput('passed', testResult.passed || 0);
    core.setOutput('failed', testResult.failed || 0);
    core.setOutput('total', testResult.total || 0);
    core.setOutput('success', testResult.failed === 0);

    // Log results
    core.info('\n📊 Test Results:');
    core.info(`   ✅ Passed: ${testResult.passed || 0}`);
    core.info(`   ❌ Failed: ${testResult.failed || 0}`);
    core.info(`   📝 Total:  ${testResult.total || 0}`);
    core.info(`   🔗 Report: ${reportUrl}`);

    // Post PR comment if applicable
    if (commentOnPR && github.context.payload.pull_request) {
      await postPRComment(github.context.payload.pull_request.number, testResult, reportUrl);
    }

    // Fail the action if tests failed and fail-on-error is true
    if (testResult.failed > 0 && failOnError) {
      core.setFailed(`❌ ${testResult.failed} test(s) failed. View report: ${reportUrl}`);
    } else if (testResult.failed > 0) {
      core.warning(`⚠️  ${testResult.failed} test(s) failed, but continuing (fail-on-error=false)`);
    } else {
      core.info('✅ All tests passed!');
    }

  } catch (error) {
    core.setFailed(`Action failed: ${error.message}`);
  }
}

async function postPRComment(prNumber, testResult, reportUrl) {
  try {
    const token = process.env.GITHUB_TOKEN;
    if (!token) {
      core.warning('GITHUB_TOKEN not available, skipping PR comment');
      return;
    }

    const octokit = github.getOctokit(token);
    const { owner, repo } = github.context.repo;

    const passed = testResult.passed || 0;
    const failed = testResult.failed || 0;
    const total = testResult.total || 0;
    const success = failed === 0;

    const emoji = success ? '✅' : '❌';
    const status = success ? 'All tests passed!' : `${failed} test(s) failed`;

    const comment = `
## ${emoji} AlphaTest Results

${status}

| Metric | Count |
|--------|-------|
| ✅ Passed | ${passed} |
| ❌ Failed | ${failed} |
| 📝 Total | ${total} |

[📊 View Full Report](${reportUrl})

---
<sub>Powered by [AlphaTest](https://alphatest.dev) - AI-powered autonomous testing</sub>
    `.trim();

    await octokit.rest.issues.createComment({
      owner,
      repo,
      issue_number: prNumber,
      body: comment
    });

    core.info('✅ Posted results to PR comment');
  } catch (error) {
    core.warning(`Failed to post PR comment: ${error.message}`);
  }
}

run();
