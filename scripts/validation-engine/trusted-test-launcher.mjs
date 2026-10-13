#!/usr/bin/env node
// Copy this file outside the checkout from a reviewed revision before using it
// to execute a candidate tree. It runs no candidate JavaScript until bubblewrap
// has isolated the candidate workspace, home, service sockets, and network.
import { execFileSync, spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import {
  chmodSync,
  closeSync,
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readdirSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  hostPathsToHide,
  isSensitiveCandidatePath,
  sandboxMountOperations,
} from './trusted-test-sandbox-policy.mjs';

const GUEST_WORKSPACE = '/mnt/workspace';
const GUEST_RUN = '/mnt/run-data';
const GUEST_MARKER = '/run/validation-engine-sandbox';
const GIT = ['/usr/bin/git', '/bin/git'].find(existsSync);
function isSensitive(relativePath, tracked) {
  const segments = relativePath.replaceAll(String.fromCharCode(92), '/').split('/');
  if (
    !tracked &&
    (segments.includes('config') || /^config\.[^/]+$/iu.test(segments[0]))
  )
    return true;
  return isSensitiveCandidatePath(relativePath);
}

function gitEnvironment(home, template) {
  const env = {};
  for (const key of ['PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'SYSTEMROOT'])
    if (typeof process.env[key] === 'string') env[key] = process.env[key];
  return {
    ...env,
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: '/dev/null',
    GIT_ATTR_NOSYSTEM: '1',
    GIT_TEMPLATE_DIR: template,
    GIT_TERMINAL_PROMPT: '0',
    HOME: home,
  };
}

function indexedFiles(root, env) {
  const trackedOutput = execFileSync(
    GIT,
    ['-c', 'core.fsmonitor=false', '-C', root, 'ls-files', '--cached', '-z'],
    { encoding: 'buffer', env, maxBuffer: 64 * 1024 * 1024 }
  );
  const files = trackedOutput.toString('utf8').split('\0').filter(Boolean);
  return {
    files: files.sort(),
    tracked: new Set(files),
  };
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return (
    relative === '' ||
    (relative !== '..' &&
      !relative.startsWith(`..${path.sep}`) &&
      !path.isAbsolute(relative))
  );
}

function copyCandidateFile(sourceRoot, workspaceRoot, relativePath, tracked) {
  if (
    path.isAbsolute(relativePath) ||
    relativePath.split(/[\\/]/u).includes('..') ||
    isSensitive(relativePath, tracked)
  )
    return;
  const source = path.resolve(sourceRoot, relativePath);
  const target = path.resolve(workspaceRoot, relativePath);
  if (!target.startsWith(`${workspaceRoot}${path.sep}`))
    throw new Error('Candidate file escaped the disposable workspace');

  let ancestor = sourceRoot;
  const components = relativePath.split(/[\\/]/u);
  for (const component of components.slice(0, -1)) {
    ancestor = path.join(ancestor, component);
    if (lstatSync(ancestor).isSymbolicLink())
      throw new Error(
        `Candidate source contains a linked parent: ${relativePath}`
      );
  }
  const metadata = lstatSync(source);
  if (metadata.isSymbolicLink())
    throw new Error(
      `Candidate source contains a symbolic link: ${relativePath}`
    );
  if (!metadata.isFile())
    throw new Error(`Candidate source is not a regular file: ${relativePath}`);
  mkdirSync(path.dirname(target), { recursive: true });
  cpSync(source, target, { preserveTimestamps: true });
  chmodSync(target, metadata.mode & 0o777);
}

function createSyntheticGitRepository(workspace, runDirectory) {
  const template = path.join(runDirectory, 'empty-git-template');
  mkdirSync(template, { mode: 0o700 });
  const env = gitEnvironment(workspace, template);
  const git = (args) => execFileSync(GIT, ['-C', workspace, ...args], { env });
  git(['init', '--quiet', '--initial-branch=main']);
  git(['config', 'user.name', 'Disposable Validation']);
  git(['config', 'user.email', 'validation@example.invalid']);
  git(['config', 'core.hooksPath', '/dev/null']);
  git(['add', '--all']);
  git([
    'commit',
    '--quiet',
    '--no-verify',
    '-m',
    'Disposable validation snapshot',
  ]);
}

function linkDependencies(sourceRoot, workspace) {
  const dependencies = [];
  const dependencyDirectories = [];
  const pending = [{ absolute: sourceRoot, relative: '' }];
  const skipped = new Set([
    '.git',
    '.next',
    '.turbo',
    '.cache',
    '.venv',
    'venv',
    'target',
    'dist',
    'coverage',
    'TestResults',
    'bin',
    'obj',
  ]);
  while (pending.length > 0) {
    const current = pending.pop();
    for (const entry of readdirSync(current.absolute, {
      withFileTypes: true,
    })) {
      const relative = current.relative
        ? `${current.relative}/${entry.name}`
        : entry.name;
      const absolute = path.join(current.absolute, entry.name);
      if (entry.name === 'node_modules') {
        let metadata;
        try {
          metadata = lstatSync(absolute);
        } catch (error) {
          if (error.code === 'ENOENT') continue;
          throw error;
        }
        if (metadata.isSymbolicLink() || !metadata.isDirectory())
          throw new Error(
            `Installed dependency path must be a real directory, not a symbolic link: ${relative}`
          );
        const dependency = realpathSync(absolute);
        if (!isWithin(sourceRoot, dependency))
          throw new Error(
            `Installed dependencies escape the candidate workspace: ${relative}`
          );
        if (!lstatSync(dependency).isDirectory())
          throw new Error(
            `Installed dependency path is not a directory: ${relative}`
          );
        dependencyDirectories.push({ relative, dependency });
        continue;
      }
      if (entry.isDirectory() && !skipped.has(entry.name))
        pending.push({ absolute, relative });
    }
  }
  for (const {
    relative: relativePath,
  } of dependencyDirectories.sort((left, right) =>
    left.relative.localeCompare(right.relative)
  )) {
    const target = path.join(workspace, relativePath);
    mkdirSync(target, { recursive: true, mode: 0o700 });
  }
  return dependencyDirectories.map(({ relative, dependency }) => ({
    relative,
    source: dependency,
  }));
}

function bubblewrapPath() {
  for (const candidate of ['/usr/bin/bwrap', '/bin/bwrap'])
    if (existsSync(candidate)) return candidate;
  throw new Error('bubblewrap is required; candidate code was not started.');
}

function makeSandboxCommand({
  sourceRoot,
  workspace,
  runDirectory,
  dependencies,
  playwrightCache,
  targetCommand,
}) {
  if (process.platform !== 'linux')
    throw new Error(
      'The trusted local test launcher requires Linux bubblewrap.'
    );
  const runtimePath = realpathSync(process.execPath);
  const runtimeDirectory = path.dirname(runtimePath);
  const externalRoots = [];
  let playwrightCacheIndex = -1;
  if (playwrightCache) {
    playwrightCacheIndex = externalRoots.indexOf(playwrightCache);
    if (playwrightCacheIndex === -1) {
      playwrightCacheIndex = externalRoots.length;
      externalRoots.push(playwrightCache);
    }
  }
  let runtimeIndex = externalRoots.indexOf(runtimeDirectory);
  if (runtimeIndex === -1) {
    runtimeIndex = externalRoots.length;
    externalRoots.push(runtimeDirectory);
  }
  const mounts = externalRoots.map((source, index) => [
    realpathSync(source),
    `${GUEST_RUN}/dependencies/${index}`,
  ]);
  const dependencyMounts = dependencies.map(({ relative, source }) => [
    realpathSync(source),
    path.posix.join(GUEST_WORKSPACE, relative.split(path.sep).join('/')),
  ]);
  mkdirSync(path.join(runDirectory, 'dependencies'), { recursive: true });
  for (let index = 0; index < mounts.length; index++)
    mkdirSync(path.join(runDirectory, 'dependencies', String(index)), {
      recursive: true,
      mode: 0o700,
    });

  const runtimeGuest = mounts[runtimeIndex][1];
  const runtimeExecutable = `${runtimeGuest}/${path.basename(runtimePath)}`;
  const markerToken = randomBytes(32).toString('hex');
  const markerFile = path.join(runDirectory, 'sandbox-marker');
  writeFileSync(markerFile, markerToken, { mode: 0o600, flag: 'wx' });

  const env = {
    PATH: `${runtimeGuest}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`,
    NODE_ENV: 'test',
    HOME: `${GUEST_RUN}/home`,
    USERPROFILE: `${GUEST_RUN}/home`,
    DOTNET_CLI_HOME: `${GUEST_RUN}/dotnet-cli`,
    TMPDIR: '/tmp',
    TMP: '/tmp',
    TEMP: '/tmp',
    APPDATA: `${GUEST_RUN}/AppData/Roaming`,
    LOCALAPPDATA: `${GUEST_RUN}/AppData/Local`,
    XDG_CONFIG_HOME: `${GUEST_RUN}/xdg-config`,
    XDG_CACHE_HOME: `${GUEST_RUN}/xdg-cache`,
    CONFIG_DIRECTORY: `${GUEST_RUN}/config`,
    VALIDATION_OUTER_SANDBOX_TOKEN: markerToken,
  };
  if (playwrightCacheIndex !== -1)
    env.PLAYWRIGHT_BROWSERS_PATH = mounts[playwrightCacheIndex][1];
  for (const key of ['LANG', 'LC_ALL', 'LC_CTYPE', 'TZ'])
    if (typeof process.env[key] === 'string') env[key] = process.env[key];

  const args = [
    '--die-with-parent',
    '--new-session',
    '--unshare-user',
    '--unshare-pid',
    '--unshare-ipc',
    '--unshare-uts',
    '--unshare-net',
    '--ro-bind',
    '/',
    '/',
  ];
  const hiddenDirectories = hostPathsToHide(sourceRoot)
    .filter((directory) => directory === '/mnt' || existsSync(directory));
  const mountOperations = sandboxMountOperations({
    workspace,
    runDirectory,
    externalMounts: mounts,
    dependencyMounts,
    hiddenDirectories,
    guestWorkspace: GUEST_WORKSPACE,
    guestRun: GUEST_RUN,
    markerFile,
    guestMarker: GUEST_MARKER,
  });
  const commandPath = bubblewrapPath();
  const sourceDescriptors = [];
  try {
    for (const operation of mountOperations) {
      if (operation.type === 'dir') {
        args.push('--dir', operation.path);
      } else if (operation.type === 'tmpfs') {
        args.push('--tmpfs', operation.path);
      } else if (
        operation.type === 'bind-fd' ||
        operation.type === 'ro-bind-fd'
      ) {
        const descriptor = openSync(operation.source, 'r');
        sourceDescriptors.push(descriptor);
        const childDescriptor = sourceDescriptors.length + 2;
        // The inherited fd pins the source even when its host path is masked.
        args.push(
          operation.type === 'bind-fd' ? '--bind' : '--ro-bind',
          '/proc/self/fd/' + childDescriptor,
          operation.target
        );
      } else {
        throw new Error('Unknown sandbox mount operation: ' + operation.type);
      }
    }
  } catch (error) {
    for (const descriptor of sourceDescriptors) closeSync(descriptor);
    throw error;
  }
  args.push(
    '--proc',
    '/proc',
    '--dev',
    '/dev',
    '--tmpfs',
    '/dev/shm',
  );
  for (const directory of [
    env.HOME,
    env.DOTNET_CLI_HOME,
    env.APPDATA,
    env.LOCALAPPDATA,
    env.XDG_CONFIG_HOME,
    env.XDG_CACHE_HOME,
    env.CONFIG_DIRECTORY,
  ])
    args.push('--dir', directory);
  args.push('--chdir', GUEST_WORKSPACE);
  for (const [name, value] of Object.entries(env))
    args.push('--setenv', name, value);
  const [requestedCommand, ...requestedArgs] = targetCommand;
  const executable =
    requestedCommand === process.execPath
      ? runtimeExecutable
      : requestedCommand;
  args.push('--', executable, ...requestedArgs);
  return { command: commandPath, args, sourceDescriptors };
}

async function executeSandboxed(command, env) {
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawn(command.command, command.args, {
        env,
        stdio: ['inherit', 'inherit', 'inherit', ...command.sourceDescriptors],
      });
    } catch (error) {
      for (const descriptor of command.sourceDescriptors) closeSync(descriptor);
      reject(error);
      return;
    }
    for (const descriptor of command.sourceDescriptors) closeSync(descriptor);
    const forward = (signal) => child.kill(signal);
    process.once('SIGINT', forward);
    process.once('SIGTERM', forward);
    let spawnError;
    child.once('error', (error) => {
      spawnError = error;
    });
    child.once('close', (code, signal) => {
      process.removeListener('SIGINT', forward);
      process.removeListener('SIGTERM', forward);
      if (spawnError) reject(spawnError);
      else if (signal) resolve(128 + (signal === 'SIGINT' ? 2 : 15));
      else resolve(code ?? 1);
    });
  });
}

async function main() {
  if (!GIT) throw new Error('A trusted system Git executable is required.');
  const separator = process.argv.indexOf('--');
  const launcherArguments = process.argv.slice(
    2,
    separator === -1 ? process.argv.length : separator
  );
  const requestedRoot = launcherArguments[0]?.startsWith('--')
    ? process.cwd()
    : launcherArguments.shift() ?? process.cwd();
  let playwrightCache;
  for (let index = 0; index < launcherArguments.length; index += 1) {
    if (launcherArguments[index] === '--playwright-cache') {
      const requestedCache = launcherArguments[index + 1];
      if (!requestedCache)
        throw new Error('--playwright-cache requires a directory path.');
      if (playwrightCache)
        throw new Error('--playwright-cache may only be provided once.');
      if (lstatSync(requestedCache).isSymbolicLink())
        throw new Error('--playwright-cache cannot be a symbolic link.');
      const cacheStat = lstatSync(requestedCache);
      if (!cacheStat.isDirectory())
        throw new Error('--playwright-cache must name a directory.');
      playwrightCache = realpathSync(requestedCache);
      index += 1;
      continue;
    }
    throw new Error(`Unknown launcher option: ${launcherArguments[index]}`);
  }
  const targetCommand =
    separator === -1
      ? [
          process.execPath,
          'bin/run-local-validation.mjs',
          '--tests-only',
          '--inside-sandbox',
        ]
      : process.argv.slice(separator + 1);
  if (targetCommand.length === 0)
    throw new Error('Pass a candidate test command after --.');
  const sourceRoot = realpathSync(requestedRoot);
  const runDirectory = mkdtempSync(path.join(tmpdir(), 'trusted-validation-run-'));
  const workspace = path.join(runDirectory, 'workspace');
  mkdirSync(workspace, { mode: 0o700 });
  try {
    const hostEnv = gitEnvironment(
      sourceRoot,
      path.join(runDirectory, 'empty')
    );
    mkdirSync(hostEnv.GIT_TEMPLATE_DIR, { mode: 0o700 });
    const candidateFiles = indexedFiles(sourceRoot, hostEnv);
    for (const file of candidateFiles.files)
      copyCandidateFile(
        sourceRoot,
        workspace,
        file,
        candidateFiles.tracked.has(file)
      );
    createSyntheticGitRepository(workspace, runDirectory);
    const dependencies = linkDependencies(sourceRoot, workspace);
    const command = makeSandboxCommand({
      sourceRoot,
      workspace,
      runDirectory,
      dependencies,
      playwrightCache,
      targetCommand,
    });
    const env = {};
    if (typeof process.env.PATH === 'string') env.PATH = process.env.PATH;
    if (typeof process.env.LANG === 'string') env.LANG = process.env.LANG;
    return await executeSandboxed(command, env);
  } finally {
    rmSync(runDirectory, { recursive: true, force: true });
  }
}

main()
  .then((code) => {
    process.exitCode = code;
  })
  .catch((error) => {
    process.stderr.write(`Trusted sandbox launcher failed: ${error.message}\n`);
    process.exitCode = 1;
  });
