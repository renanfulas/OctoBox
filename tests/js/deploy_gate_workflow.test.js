const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const WORKFLOW_PATH = path.resolve(__dirname, '../../.github/workflows/deploy-vps.yml');
const TARGET_SHA = 'a'.repeat(40);
const REQUIRED_CHECKS = [
  'Full Test Suite',
  'CI Gates',
  'OctoBox CI Checks (Performance & Integrity)',
  'Student Onboarding Corridors Regression',
  'Student Onboarding Real Smoke',
  'Security Scanners 🛡️',
  'CURVA Gates',
  'WOD Mobile Gates',
];

function loadGateScript() {
  const workflow = fs.readFileSync(WORKFLOW_PATH, 'utf8');
  const marker = '          script: |';
  const markerIndex = workflow.indexOf(marker);
  assert.notEqual(markerIndex, -1, 'deploy gate script must remain embedded in deploy-vps.yml');

  const afterMarker = workflow.slice(markerIndex + marker.length).replace(/^\r?\n/, '');
  const lines = afterMarker.split(/\r?\n/);
  const scriptLines = [];
  for (const line of lines) {
    if (line.trim() && !line.startsWith('            ')) break;
    scriptLines.push(line.startsWith('            ') ? line.slice(12) : '');
  }
  assert.ok(scriptLines.length > 0, 'deploy gate script must not be empty');
  return scriptLines.join('\n');
}

function successfulRuns(sha = TARGET_SHA) {
  return REQUIRED_CHECKS.map((name, index) => ({
    name,
    head_sha: sha,
    head_branch: 'main',
    event: 'push',
    status: 'completed',
    conclusion: 'success',
    updated_at: `2026-10-23T12:${String(index).padStart(2, '0')}:00Z`,
  }));
}

async function runGate({ context, runs, mainSha = TARGET_SHA, onRunsRequest, apiError } = {}) {
  const outputs = {};
  const failures = [];
  const infos = [];
  let runQueries = 0;
  const github = {
    rest: {
      repos: {
        getBranch: async () => ({ data: { commit: { sha: mainSha } } }),
      },
      actions: {
        listWorkflowRunsForRepo: async (params) => {
          runQueries += 1;
          onRunsRequest?.(runQueries, params);
          if (apiError) throw apiError;
          return { data: { workflow_runs: typeof runs === 'function' ? runs(runQueries) : runs } };
        },
      },
    },
  };
  const core = {
    setOutput: (name, value) => { outputs[name] = value; },
    setFailed: (message) => { failures.push(message); },
    info: (message) => { infos.push(message); },
  };
  const script = new AsyncFunction('context', 'github', 'core', 'setTimeout', loadGateScript());
  await script(context, github, core, (callback) => { callback(); return 0; });
  return { outputs, failures, infos, runQueries };
}

function dispatchContext({ ref = 'refs/heads/main', sha = TARGET_SHA } = {}) {
  return {
    eventName: 'workflow_dispatch',
    ref,
    runId: 8123,
    repo: { owner: 'octoboxfit', repo: 'octobox' },
    payload: { inputs: { target_sha: sha } },
  };
}

test('manual dispatch accepts explicit main SHA after every required check succeeds', async () => {
  const result = await runGate({ context: dispatchContext(), runs: successfulRuns() });

  assert.deepEqual(result.outputs, { target_sha: TARGET_SHA, deploy_run_id: '8123' });
  assert.deepEqual(result.failures, []);
  assert.equal(result.runQueries, 1);
});

test('manual dispatch refuses a SHA after main advances', async () => {
  const result = await runGate({
    context: dispatchContext(),
    runs: successfulRuns(),
    mainSha: 'b'.repeat(40),
  });

  assert.match(result.failures[0], /Release obsoleta/);
  assert.deepEqual(result.outputs, {});
  assert.equal(result.runQueries, 1);
});

test('manual dispatch refuses a completed failed required check', async () => {
  const runs = successfulRuns();
  runs[2].conclusion = 'failure';
  const result = await runGate({ context: dispatchContext(), runs });

  assert.match(result.failures[0], /OctoBox CI Checks \(Performance & Integrity\)/);
  assert.deepEqual(result.outputs, {});
});

test('manual dispatch refuses workflow refs other than main before querying the API', async () => {
  const result = await runGate({
    context: dispatchContext({ ref: 'refs/heads/codex/candidate' }),
    runs: successfulRuns(),
  });

  assert.match(result.failures[0], /workflow da branch main/);
  assert.equal(result.runQueries, 0);
});

test('manual dispatch refuses an incomplete SHA before querying the API', async () => {
  const result = await runGate({
    context: dispatchContext({ sha: 'a'.repeat(39) }),
    runs: successfulRuns(),
  });

  assert.match(result.failures[0], /SHA completo de 40 caracteres/);
  assert.equal(result.runQueries, 0);
});

test('automatic workflow_run refuses a source repository outside the trusted repository', async () => {
  const result = await runGate({
    context: {
      eventName: 'workflow_run',
      runId: 8124,
      repo: { owner: 'octoboxfit', repo: 'octobox' },
      payload: {
        workflow_run: {
          conclusion: 'success',
          head_branch: 'main',
          event: 'push',
          head_sha: TARGET_SHA,
          head_repository: { full_name: 'attacker/octobox' },
          repository: { full_name: 'octoboxfit/octobox' },
        },
      },
    },
    runs: successfulRuns(),
  });

  assert.match(result.failures[0], /repositório confiável/);
  assert.equal(result.runQueries, 0);
});

test('same-name checks from pull requests or non-main refs do not satisfy production gates', async () => {
  const untrusted = successfulRuns().map((run) => ({ ...run, event: 'pull_request' }));
  const result = await runGate({ context: dispatchContext(), runs: untrusted });

  assert.deepEqual(result.outputs, {});
  assert.deepEqual(result.failures, ['Gates incompletos para ' + TARGET_SHA + ': ' + REQUIRED_CHECKS.join(', ')]);
  assert.equal(result.runQueries, 120);
});

test('the newest completed attempt governs even when an older attempt succeeded', async () => {
  const runs = successfulRuns();
  runs.push({
    ...runs[0],
    status: 'completed',
    conclusion: 'failure',
    updated_at: '2026-10-23T14:00:00Z',
  });
  const result = await runGate({ context: dispatchContext(), runs });

  assert.match(result.failures[0], /Full Test Suite/);
  assert.deepEqual(result.outputs, {});
});

test('an incomplete gate set waits for the same SHA and succeeds when the missing gate completes', async () => {
  const allRuns = successfulRuns();
  const firstAttempt = allRuns.filter((run) => run.name !== 'WOD Mobile Gates');
  const result = await runGate({
    context: dispatchContext(),
    runs: (attempt) => attempt === 1 ? firstAttempt : allRuns,
  });

  assert.deepEqual(result.outputs, { target_sha: TARGET_SHA, deploy_run_id: '8123' });
  assert.deepEqual(result.failures, []);
  assert.equal(result.runQueries, 2);
});

test('GitHub API failure aborts the gate instead of allowing deployment', async () => {
  await assert.rejects(
    runGate({
      context: dispatchContext(),
      runs: successfulRuns(),
      apiError: new Error('GitHub API unavailable'),
    }),
    /GitHub API unavailable/,
  );
});

test('workflow_run deploy uses source head SHA and forwards the current deploy run ID', async () => {
  const result = await runGate({
    context: {
      eventName: 'workflow_run',
      runId: 8125,
      repo: { owner: 'octoboxfit', repo: 'octobox' },
      payload: {
        workflow_run: {
          conclusion: 'success',
          head_branch: 'main',
          event: 'push',
          head_sha: TARGET_SHA.toUpperCase(),
          head_repository: { full_name: 'OCTOBOXFIT/OCTOBOX' },
          repository: { full_name: 'octoboxfit/octobox' },
        },
      },
    },
    runs: successfulRuns(),
    onRunsRequest: (_count, params) => {
      assert.equal(params.head_sha, TARGET_SHA);
      assert.equal(params.branch, 'main');
    },
  });

  assert.deepEqual(result.outputs, { target_sha: TARGET_SHA, deploy_run_id: '8125' });
  assert.deepEqual(result.failures, []);
});
