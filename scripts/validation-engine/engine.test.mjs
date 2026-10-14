// Copyright (c) slskdN Team. All rights reserved.
import assert from 'node:assert/strict';
import {
  existsSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { after, test } from 'node:test';
import { validation } from './config.mjs';
import {
  captureCandidate,
  createPlan,
  discoverInventory,
  executePlan,
  formatValidationProgress,
  globRegex,
  isolatedTaskEnvironment,
  summarizeResult,
} from './engine.mjs';

const temporaryRoots = [];

function makeRoot(files = {}) {
  const root = mkdtempSync(path.join(os.tmpdir(), 'slskdn-validation-contract-'));
  temporaryRoots.push(root);
  for (const [relative, contents] of Object.entries(files)) {
    const fullPath = path.join(root, relative);
    mkdirSync(path.dirname(fullPath), { recursive: true });
    writeFileSync(fullPath, contents);
  }
  const git = (args) => {
    const result = spawnSync('git', args, { cwd: root, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  git(['init', '--quiet']);
  git(['config', 'user.email', 'validation-test@example.invalid']);
  git(['config', 'user.name', 'Validation Engine Test']);
  git(['add', '--all']);
  git(['commit', '--quiet', '-m', 'fixture baseline']);
  return root;
}

function baseConfig(overrides = {}) {
  return {
    repository: 'fixture',
    inputs: ['package.json'],
    requiredCommands: [],
    inventory: [{
      id: 'unit',
      glob: 'tests/**/*.test.mjs',
      framework: 'node:test',
      owner: 'unit',
    }],
    tasks: [{
      id: 'unit-tests',
      name: 'Unit tests',
      stage: 'repository',
      kind: 'test',
      command: [process.execPath, '--test', 'tests/example.test.mjs'],
      casePattern: '(?:ℹ|#)\\s*pass\\s+(\\d+)',
      minimumCases: 1,
      inventoryLanes: ['unit'],
      timeoutSeconds: 10,
    }],
    ...overrides,
  };
}

function fixture() {
  const root = makeRoot({
    'package.json': '{"name":"validation-fixture"}\n',
    'tests/example.test.mjs': "import test from 'node:test';\ntest('fixture passes', () => {});\n",
  });
  return { root, config: baseConfig() };
}

function fixturePlan(root, config, options = {}) {
  return createPlan(root, config, {
    ...options,
    executionContext: {
      executor: 'local',
      platform: process.platform,
      architecture: process.arch,
      nodeVersion: process.version,
      github: null,
    },
  });
}

after(() => {
  for (const root of temporaryRoots) rmSync(root, { recursive: true, force: true });
});

test('glob matching covers root and nested files without crossing sibling names', () => {
  const nested = globRegex('src/**/*.test.*');
  assert.equal(nested.test('src/a.test.js'), true);
  assert.equal(nested.test('src/components/a.test.jsx'), true);
  assert.equal(nested.test('src-other/a.test.js'), false);
  assert.equal(globRegex('**/*.spec.ts').test('a.spec.ts'), true);
});

test('live progress summary distinguishes completed, blocked, pending, and active tasks', () => {
  const tasks = [
    { id: 'passed', name: 'Passed task' },
    { id: 'blocked', name: 'Blocked task' },
    { id: 'running', name: 'Long task' },
  ];
  const results = new Map([
    ['passed', { status: 'passed', startedAt: '2026-10-12T00:00:00.000Z' }],
    ['blocked', { status: 'blocked' }],
  ]);
  assert.equal(
    formatValidationProgress('sample', tasks, results, tasks[2], 65_000),
    '[validation] sample: 1/3 selected tasks complete (1 passed, 0 failed, 1 blocked, 1 pending); running Long task (1m05s)',
  );
});

test('inventory records scoped file digests and rejects empty or duplicate ownership', () => {
  const { root, config } = fixture();
  const inventory = discoverInventory(root, config.inventory);
  assert.deepEqual(inventory.laneCounts, { unit: 1 });
  assert.equal(inventory.entries[0].file, 'tests/example.test.mjs');
  assert.match(inventory.entries[0].sha256, /^[a-f0-9]{64}$/);
  assert.throws(() => discoverInventory(root, [
    ...config.inventory,
    { ...config.inventory[0], id: 'duplicate-owner', owner: 'other' },
  ]), /duplicate ownership/);
  assert.throws(() => discoverInventory(root, [{
    ...config.inventory[0],
    glob: 'tests/missing/**/*.test.mjs',
  }]), /inventory is empty/);
});

test('inventory rejects symbolic links in native test discovery scopes', () => {
  const root = makeRoot({ 'package.json': '{}\n' });
  mkdirSync(path.join(root, 'tests'), { recursive: true });
  writeFileSync(path.join(root, 'outside.test.mjs'), '');
  symlinkSync('../outside.test.mjs', path.join(root, 'tests', 'linked.test.mjs'));
  assert.throws(() => discoverInventory(root, baseConfig().inventory), /Symlink in test discovery scope/);
});

test('plan binds the candidate and closes test selection over its dependencies', () => {
  const { root, config } = fixture();
  config.tasks.unshift({
    id: 'prepare',
    name: 'Prepare',
    stage: 'prepare',
    kind: 'setup',
    command: [process.execPath, '-e', 'process.exit(0)'],
  });
  config.tasks[1].dependsOn = ['prepare'];
  config.tasks.push({
    id: 'optional-browser',
    name: 'Optional browser suite',
    stage: 'browser',
    kind: 'test',
    browserCache: 'playwright',
    command: [process.execPath, '-e', 'process.exit(0)'],
    casePattern: 'passed (\\d+)',
    minimumCases: 1,
    defaultSelected: false,
  });
  const plan = fixturePlan(root, config, { testsOnly: true });
  assert.deepEqual(plan.tasks.filter((task) => task.selected).map((task) => task.id), [
    'prepare',
    'unit-tests',
  ]);
  const browserTask = plan.tasks.find((task) => task.id === 'optional-browser');
  assert.equal(browserTask.browserCache, 'playwright');
  assert.ok(browserTask.envKeys.includes('PLAYWRIGHT_BROWSERS_PATH'));
  assert.equal(plan.inventoryCounts.unit, 1);
  assert.equal(plan.candidate.commit.length, 40);
  assert.match(plan.candidate.sourceSha256, /^[a-f0-9]{64}$/);
  assert.equal(plan.runtimes.length, 0);
  assert.match(plan.inventoryLaneDigests.unit, /^[a-f0-9]{64}$/);
});

test('executor rejects a plan whose task contract was changed after hashing', async () => {
  const { root, config } = fixture();
  const plan = fixturePlan(root, config);
  plan.tasks[0].command = [process.execPath, '-e', 'process.exit(0)'];
  await assert.rejects(executePlan(root, config, plan), /plan digest/);
});

test('native execution records passing case counts, source identity and private evidence', async () => {
  const { root, config } = fixture();
  const plan = fixturePlan(root, config);
  const runRoot = mkdtempSync(path.join(os.tmpdir(), 'slskdn-validation-receipt-'));
  temporaryRoots.push(runRoot);
  const result = await executePlan(root, config, plan, { runRoot });
  assert.equal(result.exitCode, 0, JSON.stringify(result.receipt, null, 2) +
    '\\n' + readFileSync(path.join(runRoot, 'unit-tests.log'), 'utf8'));
  assert.equal(result.receipt.status, 'passed');
  assert.equal(result.receipt.totals.executed, 1);
  assert.equal(result.receipt.totals.activeCases, 1);
  assert.deepEqual(result.receipt.tasks[0].inventory.map((item) => item.discoveredFiles), [1]);
  assert.equal(statSync(runRoot).mode & 0o777, 0o700);
  const log = path.join(runRoot, result.receipt.tasks[0].logFile);
  assert.equal(statSync(log).mode & 0o777, 0o600);
  assert.match(readFileSync(path.join(runRoot, 'receipt.json'), 'utf8'), /"status": "passed"/);
});

test('executor rejects a GitHub SHA that differs from the candidate commit', async () => {
  const { root, config } = fixture();
  const executionContext = {
    executor: 'github-actions',
    platform: process.platform,
    architecture: process.arch,
    nodeVersion: process.version,
    github: { sha: 'not-the-candidate-commit' },
  };
  const plan = createPlan(root, config, { executionContext });
  const result = await executePlan(root, config, plan);

  assert.equal(result.receipt.status, 'incomplete');
  assert.deepEqual(result.receipt.prerequisites, [{
    command: 'GITHUB_SHA',
    available: false,
    expected: plan.candidate.commit,
    actual: executionContext.github.sha,
  }]);
  assert.equal(result.receipt.tasks[0].status, 'not-run');
});

test('execution fails closed when a test reports zero active cases', async () => {
  const { root, config } = fixture();
  config.tasks[0].command = [process.execPath, '-e', 'console.log("suite completed")'];
  const plan = fixturePlan(root, config);
  const result = await executePlan(root, config, plan);
  assert.equal(result.receipt.tasks[0].status, 'incomplete');
  assert.equal(result.receipt.status, 'failed');
  assert.equal(result.receipt.totals.activeCases, 0);
});

test('execution blocks later tasks when a command changes the planned source', async () => {
  const { root, config } = fixture();
  config.tasks.push({
    id: 'after-tests',
    name: 'Must not run after drift',
    stage: 'repository',
    kind: 'check',
    command: [process.execPath, '-e', 'process.exit(0)'],
  });
  config.tasks[0].command = [
    process.execPath,
    '-e',
    "require('node:fs').writeFileSync('package.json', '{\\\"changed\\\":true}\\n')",
  ];
  const plan = fixturePlan(root, config);
  const result = await executePlan(root, config, plan);
  assert.equal(result.receipt.status, 'failed');
  assert.equal(result.receipt.tasks[0].status, 'incomplete');
  assert.match(result.receipt.tasks[1].reason, /candidate source changed/);
  assert.equal(result.receipt.totals.blocked, 1);
});

test('execution streams logs before timeout and does not accept failed commands', async () => {
  const { root, config } = fixture();
  config.tasks[0].command = [
    process.execPath,
    '-e',
    "process.stdout.write('persisted-before-timeout');setInterval(() => {}, 1000)",
  ];
  config.tasks[0].timeoutSeconds = 0.1;
  const plan = fixturePlan(root, config);
  const result = await executePlan(root, config, plan);
  assert.equal(result.receipt.tasks[0].status, 'failed');
  assert.equal(result.receipt.tasks[0].timedOut, true);
  assert.equal(result.receipt.status, 'failed');
  const logPath = path.join(result.runRoot, result.receipt.tasks[0].logFile);
  assert.match(readFileSync(logPath, 'utf8'), /persisted-before-timeout/u);
});

test('execution caps task logs and marks truncated output', async () => {
  const { root, config } = fixture();
  config.tasks[0].kind = 'check';
  const outputBytes = 16 * 1024 * 1024 + 1;
  config.tasks[0].command = [
    process.execPath,
    '-e',
    'process.stdout.write(Buffer.alloc(' + outputBytes + ', 120));process.stdout.write("VALIDATION_TEST_CASES_PASSED=1")',
  ];
  const result = await executePlan(root, config, fixturePlan(root, config));
  const logPath = path.join(result.runRoot, result.receipt.tasks[0].logFile);
  const log = readFileSync(logPath);
  assert.equal(result.receipt.tasks[0].status, 'passed');
  assert.equal(result.receipt.tasks[0].outputBytes, outputBytes + Buffer.byteLength('VALIDATION_TEST_CASES_PASSED=1'));
  assert.equal(log.length, 16 * 1024 * 1024);
  assert.match(log.toString('utf8'), /\[validation log truncated after 16 MiB\]\n$/u);
});

test('child environments hide sensitive values unless a task explicitly needs them', async () => {
  const key = 'VALIDATION_ENGINE_TEST_SECRET';
  const operatorTemp = mkdtempSync(path.join(os.tmpdir(), 'slskdn-validation-operator-tmp-'));
  const injected = {
    [key]: 'do-not-log-me',
    GITHUB_TOKEN: 'synthetic-github-token',
    NODE_OPTIONS: '--require=/nonexistent-slskdn-validation-module.cjs',
    HOME: '/operator/home',
    TMPDIR: operatorTemp,
    XDG_CONFIG_HOME: '/operator/config',
    NUGET_PACKAGES: '/operator/nuget',
    HTTPS_PROXY: 'http://proxy.invalid',
    RANDOM_PRIVATE_VALUE: 'synthetic-private-value',
    LOCAL_IDENTITY_DENYLIST: 'synthetic-local-identity-list',
    CI: 'false',
  };
  const previous = new Map(Object.keys(injected).map((name) => [name, process.env[name]]));
  Object.assign(process.env, injected);
  try {
    assert.throws(
      () => isolatedTaskEnvironment({ id: '../outside' }, operatorTemp),
      /safe lowercase identifier/,
    );
    const { root, config } = fixture();
    config.runtimes = [{
      command: process.execPath,
      args: ['-e', `process.stdout.write(process.env[${JSON.stringify(key)}] ?? 'not-inherited')`],
    }, {
      command: process.execPath,
      args: ['-e', `process.stdout.write(JSON.stringify({ home: process.env.HOME, dotnetHome: process.env.DOTNET_CLI_HOME, nugetPackages: process.env.NUGET_PACKAGES, secret: process.env[${JSON.stringify(key)}] ?? null }))`],
    }];
    const plan = createPlan(root, config);
    assert.equal(plan.runtimes[0].version, 'not-inherited');
    const probeEnvironment = JSON.parse(plan.runtimes[1].version);
    assert.notEqual(probeEnvironment.home, injected.HOME);
    assert.notEqual(probeEnvironment.dotnetHome, injected.DOTNET_CLI_HOME);
    assert.notEqual(probeEnvironment.nugetPackages, injected.NUGET_PACKAGES);
    assert.equal(probeEnvironment.secret, null);
    assert.match(probeEnvironment.home, /slskdn-validation-runtime-probe-/u);
    assert.equal(existsSync(probeEnvironment.home), false);

    config.tasks[0].kind = 'check';
    config.tasks[0].command = [
      process.execPath,
      '-e',
      `const keys = ${JSON.stringify(Object.keys(injected))}; process.stdout.write(JSON.stringify(Object.fromEntries(keys.map((name) => [name, process.env[name] ?? null]))))`,
    ];
    let result = await executePlan(root, config, fixturePlan(root, config));
    let log = path.join(result.runRoot, result.receipt.tasks[0].logFile);
    const childEnvironment = JSON.parse(readFileSync(log, 'utf8'));
    const environmentRoot = path.join(result.runRoot, `${config.tasks[0].id}-environment`);
    assert.equal(childEnvironment[key], null);
    assert.equal(childEnvironment.GITHUB_TOKEN, null);
    assert.equal(childEnvironment.NODE_OPTIONS, null);
    assert.equal(childEnvironment.HTTPS_PROXY, null);
    assert.equal(childEnvironment.RANDOM_PRIVATE_VALUE, null);
    assert.equal(childEnvironment.LOCAL_IDENTITY_DENYLIST, null);
    assert.equal(childEnvironment.HOME, path.join(environmentRoot, 'home'));
    assert.equal(childEnvironment.TMPDIR, path.join(environmentRoot, 'tmp'));
    assert.equal(childEnvironment.XDG_CONFIG_HOME, path.join(environmentRoot, 'xdg-config'));
    assert.equal(childEnvironment.NUGET_PACKAGES, path.join(environmentRoot, 'nuget-packages'));
    assert.equal(childEnvironment.CI, 'true');

    config.tasks[0].passEnv = [key];
    assert.throws(() => fixturePlan(root, config), /unapproved inherited environment variable/);
    config.tasks[0].id = 'remediation-baseline';
    config.tasks[0].passEnv = ['LOCAL_IDENTITY_DENYLIST'];
    config.tasks[0].command = [process.execPath, '-e', "process.stdout.write(process.env.LOCAL_IDENTITY_DENYLIST ?? '')"];
    result = await executePlan(root, config, fixturePlan(root, config));
    log = path.join(result.runRoot, result.receipt.tasks[0].logFile);
    assert.equal(readFileSync(log, 'utf8'), 'synthetic-local-identity-list');
    assert.deepEqual(result.receipt.tasks[0].envKeys, ['LOCAL_IDENTITY_DENYLIST']);
  } finally {
    for (const [name, value] of previous) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    rmSync(operatorTemp, { recursive: true, force: true });
  }
});

test('Playwright tasks use the job cache and keep standard runs offline', () => {
  const runRoot = makeRoot({ 'package.json': '{}\n' });
  const runnerTemp = path.join(os.tmpdir(), 'slskdn-validation-runner-temp');
  const task = {
    id: 'browser-e2e',
    kind: 'test',
    browserCache: 'playwright',
  };
  const env = isolatedTaskEnvironment(task, runRoot, {
    RUNNER_TEMP: runnerTemp,
    TMPDIR: '/operator/temp',
    HOME: '/operator/home',
    XDG_CACHE_HOME: '/operator/cache',
    PLAYWRIGHT_BROWSERS_PATH: '/operator/cache/untrusted-browsers',
  });
  const environmentRoot = path.join(runRoot, 'browser-e2e-environment');
  const workflow = readFileSync(
    new URL('../../.github/workflows/e2e-tests.yml', import.meta.url),
    'utf8',
  );

  assert.equal(
    env.PLAYWRIGHT_BROWSERS_PATH,
    path.join(runnerTemp, 'slskdn-playwright-browsers'),
  );
  assert.equal(env.HOME, path.join(environmentRoot, 'home'));
  assert.equal(env.XDG_CACHE_HOME, path.join(environmentRoot, 'xdg-cache'));
  assert.notEqual(env.PLAYWRIGHT_BROWSERS_PATH, '/operator/cache/untrusted-browsers');
  const mountedCacheEnv = isolatedTaskEnvironment(task, runRoot, {
    PLAYWRIGHT_BROWSERS_PATH: '/mnt/run-data/dependencies/0',
  });
  assert.equal(
    mountedCacheEnv.PLAYWRIGHT_BROWSERS_PATH,
    '/mnt/run-data/dependencies/0',
  );
  const nestedHostPathEnv = isolatedTaskEnvironment(task, runRoot, {
    PLAYWRIGHT_BROWSERS_PATH: '/mnt/run-data/dependencies/0/../../home/operator',
  });
  assert.equal(
    nestedHostPathEnv.PLAYWRIGHT_BROWSERS_PATH,
    path.join(os.tmpdir(), 'slskdn-playwright-browsers'),
  );
  for (const id of ['browser-e2e', 'web-browser-e2e']) {
    const definition = validation.tasks.find((candidate) => candidate.id === id);
    assert.equal(definition?.env?.SLSKDN_TEST_NO_CONNECT, 'true');
    const taskEnvironment = isolatedTaskEnvironment(definition, runRoot, {
      RUNNER_TEMP: runnerTemp,
      SLSKDN_TEST_NO_CONNECT: 'false',
    });
    assert.equal(taskEnvironment.SLSKDN_TEST_NO_CONNECT, 'true');
  }
  assert.match(
    workflow,
    /PLAYWRIGHT_BROWSERS_PATH:\s*\$\{\{\s*runner\.temp\s*\}\}\/slskdn-playwright-browsers/,
  );
  assert.throws(
    () => isolatedTaskEnvironment({ ...task, browserCache: '/operator/cache' }, runRoot, {}),
    /unsupported browser cache/,
  );
});

test('remediation baseline ignores synthetic runtime identities in its isolated task', () => {
  const runRoot = makeRoot({ 'package.json': '{}\n' });
  const task = validation.tasks.find((candidate) => candidate.id === 'remediation-baseline');

  assert.ok(task);
  assert.equal(task.env?.LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES, '0');
  const environment = isolatedTaskEnvironment(task, runRoot, {
    HOME: '/operator/home',
    USER: 'operator',
  });

  assert.equal(environment.LOCAL_IDENTITY_SCAN_RUNTIME_IDENTITIES, '0');
  assert.equal(
    environment.HOME,
    path.join(runRoot, 'remediation-baseline-environment', 'home'),
  );
});

test('plan and executor reject dependency cycles and report missing tools', async () => {
  const { root, config } = fixture();
  config.tasks[0].dependsOn = ['other'];
  config.tasks.push({
    id: 'other',
    name: 'Other',
    stage: 'repository',
    kind: 'check',
    command: [process.execPath, '-e', 'process.exit(0)'],
    dependsOn: ['unit-tests'],
  });
  assert.throws(() => fixturePlan(root, config), /dependency cycle/);

  const missingRoot = makeRoot({ 'package.json': '{}\n' });
  const missingConfig = baseConfig({
    inventory: [],
    tasks: [{
      id: 'check',
      name: 'Check',
      stage: 'repository',
      kind: 'check',
      command: [process.execPath, '-e', 'throw new Error("must not execute")'],
    }],
    requiredCommands: ['command-that-is-not-installed-validation-test'],
  });
  const plan = fixturePlan(missingRoot, missingConfig);
  const result = await executePlan(missingRoot, missingConfig, plan);
  assert.equal(result.receipt.status, 'incomplete');
  assert.equal(result.receipt.totals.executed, 0);
  assert.equal(result.receipt.prerequisites.some((item) => !item.available), true);
  const summary = summarizeResult(missingConfig.repository, result);
  assert.deepEqual(summary.preflightFailures.map((item) => item.command), [
    'command-that-is-not-installed-validation-test',
  ]);
});

test('candidate digests change after tracked source edits', () => {
  const { root, config } = fixture();
  const before = captureCandidate(root, config.inputs, discoverInventory(root, config.inventory));
  writeFileSync(path.join(root, 'package.json'), '{"edited":true}\n');
  const afterEdit = captureCandidate(root, config.inputs, discoverInventory(root, config.inventory));
  assert.notEqual(before.sourceSha256, afterEdit.sourceSha256);
});
