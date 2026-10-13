// The sandbox policy describes Linux paths even when its contract runs on Windows.
import path from 'node:path/posix';

export const HOST_PATHS_TO_HIDE = Object.freeze([
  '/etc',
  '/home',
  '/root',
  '/run',
  '/var',
  '/tmp',
  '/sys',
  '/media',
  '/mnt',
  '/opt',
  '/srv',
  '/usr/local',
  '/workspace',
  '/workspaces',
  '/data',
  '/backup',
  '/backups',
  '/volumes',
  '/secrets',
  '/credentials',
]);

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return (
    relative === '' ||
    (relative !== '..' &&
      !relative.startsWith(`..${path.sep}`) &&
      !path.isAbsolute(relative))
  );
}

export function hostPathsToHide(sourceRoot) {
  const checkout = path.resolve(sourceRoot);
  const filesystemRoot = path.parse(checkout).root;
  if (checkout === filesystemRoot)
    throw new Error('The candidate checkout cannot be the filesystem root.');

  if (HOST_PATHS_TO_HIDE.some((directory) => isWithin(directory, checkout)))
    return [...HOST_PATHS_TO_HIDE];

  const parent = path.dirname(checkout);
  return [
    ...HOST_PATHS_TO_HIDE,
    parent === filesystemRoot ? checkout : parent,
  ];
}

export function sandboxMountOperations({
  workspace,
  runDirectory,
  externalMounts,
  dependencyMounts,
  hiddenDirectories,
  guestWorkspace,
  guestRun,
  markerFile,
  guestMarker,
}) {
  const operations = hiddenDirectories.map((directory) => ({
    type: 'tmpfs',
    path: directory,
    hostMask: true,
  }));
  operations.push(
    { type: 'dir', path: guestWorkspace },
    { type: 'dir', path: guestRun },
    { type: 'bind-fd', source: workspace, target: guestWorkspace },
    { type: 'bind-fd', source: runDirectory, target: guestRun },
  );
  for (const [source, target] of externalMounts)
    operations.push({ type: 'ro-bind-fd', source, target });
  for (const [source, target] of dependencyMounts)
    operations.push({ type: 'ro-bind-fd', source, target });
  operations.push({ type: 'ro-bind-fd', source: markerFile, target: guestMarker });
  return operations;
}

const sensitiveName =
  /^(?:[.]env(?:$|[.](?!example$)[^/]+)|[.]ssh|[.]aws|[.]gnupg|id_(?:rsa|ed25519)|[.]git-credentials|[.]npmrc|[.]pypirc|[.]netrc|[^/]+[.](?:pem|key))$/iu;
const sensitiveCredentialName =
  /^(?:auth(?:entication)?|tokens?|credentials?|secrets?)$/iu;
const sensitiveCredentialConfigFile =
  /^(?:auth(?:entication)?|tokens?|credentials?|secrets?)[.](?:json|ya?ml|toml|ini|cfg|conf|env|properties|xml|txt)$/iu;
const sourceCodeFile =
  /[.](?:c|cc|cpp|cs|css|go|h|hpp|java|js|jsx|mjs|php|py|rb|rs|sql|swift|ts|tsx|vue)$/iu;

export function isSensitiveCandidatePath(relativePath) {
  const segments = relativePath.replaceAll(String.fromCharCode(92), '/').split('/');
  if (segments.includes('.git') || segments.includes('node_modules'))
    return true;
  if (segments.some((segment) => sensitiveName.test(segment)))
    return true;

  const filename = segments.at(-1) ?? '';
  if (
    sensitiveCredentialName.test(filename) ||
    sensitiveCredentialConfigFile.test(filename)
  )
    return true;

  const insideCredentialDirectory = segments
    .slice(0, -1)
    .some((segment) => sensitiveCredentialName.test(segment));
  return insideCredentialDirectory && !sourceCodeFile.test(filename);
}
