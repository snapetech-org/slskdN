// Copyright (c) snapetech and SeerrNG contributors.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  HOST_PATHS_TO_HIDE,
  hostPathsToHide,
  isSensitiveCandidatePath,
  sandboxMountOperations,
} from './trusted-test-sandbox-policy.mjs';

const launcher = fileURLToPath(
  new URL(
    './trusted-test-launcher.mjs',
    import.meta.url
  )
);
for (const hostPath of ['/etc', '/opt', '/srv', '/usr/local'])
  assert.ok(
    HOST_PATHS_TO_HIDE.includes(hostPath),
    `the sandbox must hide host path ${hostPath}`
  );
const bwrap = ['/usr/bin/bwrap', '/bin/bwrap'].find(existsSync);
const sandboxAvailable = (() => {
  if (process.platform !== 'linux' || !bwrap) return false;
  return (
    spawnSync(
      bwrap,
      [
        '--die-with-parent',
        '--unshare-user',
        '--ro-bind',
        '/',
        '/',
        '--',
        '/bin/true',
      ],
      { stdio: 'ignore' }
    ).status === 0
  );
})();

test('preserves tracked token-named source while excluding credential files', () => {
  assert.equal(isSensitiveCandidatePath('web/src/lib/token.js'), false);
  assert.equal(isSensitiveCandidatePath('vendor/mainline/src/rpc/server/tokens.rs'), false);
  assert.equal(isSensitiveCandidatePath('src/authentication.ts'), false);
  assert.equal(isSensitiveCandidatePath('src/authentication/UserStore.cs'), false);
  assert.equal(isSensitiveCandidatePath('auth'), true);
  assert.equal(isSensitiveCandidatePath('nested/tokens'), true);
  assert.equal(isSensitiveCandidatePath('credentials'), true);
  assert.equal(isSensitiveCandidatePath('secrets'), true);
  assert.equal(isSensitiveCandidatePath('auth.json'), true);
  assert.equal(isSensitiveCandidatePath('nested/config/secrets.yaml'), true);
  assert.equal(isSensitiveCandidatePath('.env.local'), true);
  assert.equal(isSensitiveCandidatePath('tokens.env'), true);
  assert.equal(isSensitiveCandidatePath('nested/credentials/private-key'), true);
  assert.equal(isSensitiveCandidatePath('src/tokens/index.ts'), false);
  assert.equal(isSensitiveCandidatePath('nested/credentials/TokenStore.ts'), false);
  assert.equal(isSensitiveCandidatePath('nested/credentials.txt'), true);
});

test('binds open sources only after masking their host directories', () => {
  const hiddenDirectories = hostPathsToHide('/home/runner/work/project')
    .filter((directory) => ['/home', '/tmp', '/mnt'].includes(directory));
  const operations = sandboxMountOperations({
    workspace: '/home/runner/work/project',
    runDirectory: '/home/runner/work/_temp/validation-run',
    externalMounts: [['/usr/local/bin/node', '/mnt/run-data/dependencies/0']],
    dependencyMounts: [['/home/runner/work/project/node_modules/react', '/mnt/workspace/node_modules/react']],
    hiddenDirectories,
    guestWorkspace: '/mnt/workspace',
    guestRun: '/mnt/run-data',
    markerFile: '/home/runner/work/_temp/validation-run/sandbox-marker',
    guestMarker: '/run/validation-engine-sandbox',
  });
  const finalHostMask = Math.max(...operations
    .map((operation, index) => operation.hostMask ? index : -1));
  const descriptorBinds = operations.filter((operation) =>
    operation.type === 'bind-fd' || operation.type === 'ro-bind-fd');

  assert.equal(operations.filter((operation) => operation.hostMask).length, hiddenDirectories.length);
  assert.ok(descriptorBinds.length > 0);
  assert.ok(operations.indexOf(descriptorBinds[0]) > finalHostMask);
  assert.equal(descriptorBinds[0].source, '/home/runner/work/project');
  assert.equal(descriptorBinds[0].target, '/mnt/workspace');
  assert.equal(descriptorBinds.at(-1).source, '/home/runner/work/_temp/validation-run/sandbox-marker');
});

test(
  'trusted launcher contains import-time candidate code before it runs',
  { skip: !sandboxAvailable && 'bubblewrap user namespaces are unavailable' },
  async (t) => {
    const parent = mkdtempSync(
      path.join(tmpdir(), 'trusted-validation-launcher-')
    );
    const source = path.join(parent, 'candidate');
    const hostFile = path.join(parent, 'host-canary.txt');
    const browserCache = path.join(parent, 'playwright-cache');
    const outsideDependencies = path.join(parent, 'outside-dependencies');
    const hostSocket = path.join(parent, 'host-canary.sock');
    const candidateWrite = path.join(source, 'launcher-write-canary.txt');
    mkdirSync(path.join(source, 'bin'), { recursive: true });
    mkdirSync(browserCache, { recursive: true });
    mkdirSync(outsideDependencies, { recursive: true });
    const tcpServer = createServer();
    tcpServer.listen(0, '127.0.0.1');
    await once(tcpServer, 'listening');
    const socketServer = createServer();
    socketServer.listen(hostSocket);
    await once(socketServer, 'listening');
    t.after(async () => {
      if (tcpServer.listening)
        await new Promise((resolve) => tcpServer.close(resolve));
      if (socketServer.listening)
        await new Promise((resolve) => socketServer.close(resolve));
      rmSync(parent, { recursive: true, force: true });
    });
    mkdirSync(path.join(source, 'nested/config'), { recursive: true });
    mkdirSync(path.join(source, 'web/src/lib'), { recursive: true });
    mkdirSync(path.join(source, 'vendor/mainline/src/rpc/server'), { recursive: true });
    writeFileSync(path.join(source, 'web/src/lib/token.js'), 'export const token = "source code";\n');
    writeFileSync(path.join(source, 'vendor/mainline/src/rpc/server/tokens.rs'), 'pub fn tokens() {}\n');
    writeFileSync(hostFile, 'host canary stays unchanged');
    writeFileSync(path.join(browserCache, 'browser-canary.txt'), 'read-only browser');
    writeFileSync(path.join(source, '.gitignore'), 'node_modules/\n');
    writeFileSync(path.join(source, '.env'), 'PRIVATE_ENV_CANARY=hidden\n');
    writeFileSync(path.join(source, 'config.json'), '{"private":true}\n');
    writeFileSync(
      path.join(source, 'nested/.env.local'),
      'NESTED_ENV_CANARY=hidden\n'
    );
    writeFileSync(
      path.join(source, 'nested/config/secrets.json'),
      '{"secret":"hidden"}\n'
    );
    writeFileSync(path.join(source, 'auth.json'), '{"token":"private"}\n');
    writeFileSync(path.join(source, 'token.json'), '{"token":"private"}\n');
    writeFileSync(path.join(source, 'tokens.env'), 'PRIVATE_TOKENS_CANARY=hidden\n');
    mkdirSync(path.join(source, 'nested/credentials'), { recursive: true });
    writeFileSync(path.join(source, 'nested/credentials/private-key'), 'private credential\n');
    mkdirSync(path.join(source, 'src/tokens'), { recursive: true });
    writeFileSync(path.join(source, 'src/tokens/index.ts'), 'export const source = "token directory source";\n');
    mkdirSync(path.join(source, 'node_modules'), { recursive: true });
    writeFileSync(
      path.join(source, 'node_modules/marker.txt'),
      'read-only dependency'
    );
    mkdirSync(path.join(source, 'node_modules/fixture-dependency'));
    writeFileSync(
      path.join(source, 'node_modules/fixture-dependency/package.json'),
      '{"name":"fixture-dependency","type":"module","exports":"./index.js"}\n'
    );
    writeFileSync(
      path.join(source, 'node_modules/fixture-dependency/index.js'),
      'export default "sibling dependency resolved";\n'
    );
    writeFileSync(
      path.join(source, 'bin/run-local-validation.mjs'),
      `import assert from 'node:assert/strict';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import fixtureDependency from 'fixture-dependency';
const hostFile = ${JSON.stringify(hostFile)};
const hostSocket = ${JSON.stringify(hostSocket)};
const hostPort = ${tcpServer.address().port};
assert.throws(() => readFileSync(hostFile), { code: 'ENOENT' });
assert.equal(process.env.SECRET_CANARY, undefined);
assert.equal(existsSync('/mnt/workspace/.env'), false);
assert.equal(existsSync('/mnt/workspace/config.json'), true);
assert.equal(existsSync('/mnt/workspace/nested/config/operator.json'), false);
assert.equal(existsSync('/mnt/workspace/auth.json'), false);
assert.equal(existsSync('/mnt/workspace/token.json'), false);
assert.equal(existsSync('/mnt/workspace/tokens.env'), false);
assert.equal(existsSync('/mnt/workspace/nested/credentials/private-key'), false);
assert.match(readFileSync('/mnt/workspace/src/tokens/index.ts', 'utf8'), /token directory source/u);
assert.match(readFileSync('/mnt/workspace/web/src/lib/token.js', 'utf8'), /source code/u);
assert.match(readFileSync('/mnt/workspace/vendor/mainline/src/rpc/server/tokens.rs', 'utf8'), /pub fn tokens/u);
assert.equal(existsSync('/mnt/workspace/nested/.env.local'), false);
assert.equal(existsSync('/mnt/workspace/nested/config/secrets.json'), false);
assert.equal(existsSync('/etc/os-release'), false);
const originalCheckout = ${JSON.stringify(source)};
assert.throws(() => readFileSync(path.join(originalCheckout, 'auth.json')), { code: 'ENOENT' });
assert.throws(() => writeFileSync(hostFile, 'escaped'));
assert.equal(readFileSync('/run/validation-engine-sandbox', 'utf8'), process.env.VALIDATION_OUTER_SANDBOX_TOKEN);
assert.equal(fixtureDependency, 'sibling dependency resolved');
const connectionResults = await Promise.all([
  new Promise((resolve) => { const socket = net.connect(hostPort, '127.0.0.1'); socket.once('connect', () => { socket.destroy(); resolve('connected'); }); socket.once('error', () => resolve('blocked')); socket.setTimeout(1000, () => { socket.destroy(); resolve('blocked'); }); }),
  new Promise((resolve) => { const socket = net.createConnection(hostSocket); socket.once('connect', () => { socket.destroy(); resolve('connected'); }); socket.once('error', () => resolve('blocked')); socket.setTimeout(1000, () => { socket.destroy(); resolve('blocked'); }); }),
]);
assert.deepEqual(connectionResults, ['blocked', 'blocked']);
assert.equal(readFileSync(path.join(process.env.PLAYWRIGHT_BROWSERS_PATH, 'browser-canary.txt'), 'utf8'), 'read-only browser');
assert.throws(() => writeFileSync(path.join(process.env.PLAYWRIGHT_BROWSERS_PATH, 'browser-canary.txt'), 'changed'));
writeFileSync('/mnt/workspace/launcher-write-canary.txt', 'candidate only');
assert.equal(readFileSync('/mnt/workspace/node_modules/marker.txt', 'utf8'), 'read-only dependency');
assert.throws(() => writeFileSync('/mnt/workspace/node_modules/marker.txt', 'changed'));
`
    );
    execFileSync('git', ['init', '--quiet', '--initial-branch=main'], {
      cwd: source,
    });
    execFileSync('git', ['config', 'user.name', 'Fixture'], { cwd: source });
    execFileSync('git', ['config', 'user.email', 'fixture@example.invalid'], {
      cwd: source,
    });
    execFileSync('git', ['add', '--all'], { cwd: source });
    execFileSync('git', ['commit', '--quiet', '-m', 'Fixture'], {
      cwd: source,
    });
    mkdirSync(path.join(source, 'nested/config'), { recursive: true });
    writeFileSync(
      path.join(source, 'nested/config/operator.json'),
      '{"private":true}\n'
    );
    const result = spawnSync(
      process.execPath,
      [
        launcher,
        source,
        '--playwright-cache',
        browserCache,
        '--',
        process.execPath,
        'bin/run-local-validation.mjs',
      ],
      {
        encoding: 'utf8',
        env: { ...process.env, SECRET_CANARY: 'must-not-be-inherited' },
        timeout: 30_000,
      }
    );
    assert.equal(result.error, undefined, result.error?.message);
    assert.equal(
      result.status,
      0,
      `${result.stdout ?? ''}${result.stderr ?? ''}`
    );
    assert.equal(readFileSync(hostFile, 'utf8'), 'host canary stays unchanged');
    assert.equal(existsSync(candidateWrite), false);

    rmSync(path.join(source, 'node_modules'), { recursive: true, force: true });
    symlinkSync(outsideDependencies, path.join(source, 'node_modules'), 'dir');
    const linkedDependencyResult = spawnSync(
      process.execPath,
      [launcher, source, '--', process.execPath, '-e', 'process.exit(99)'],
      { encoding: 'utf8', timeout: 30_000 }
    );
    assert.equal(linkedDependencyResult.error, undefined);
    assert.equal(linkedDependencyResult.status, 1);
    assert.match(
      linkedDependencyResult.stderr,
      /Installed dependency path must be a real directory/u
    );
  }
);

test('sandbox masks candidate checkouts outside the standard host paths', () => {
  assert.ok(hostPathsToHide('/projects/QuestarrNG').includes('/projects'));
  assert.ok(hostPathsToHide('/QuestarrNG').includes('/QuestarrNG'));
  assert.equal(
    hostPathsToHide('/home/keith/QuestarrNG').includes('/home/keith'),
    false
  );
  assert.throws(() => hostPathsToHide('/'), /cannot be the filesystem root/u);
});
