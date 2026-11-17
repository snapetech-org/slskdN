// <copyright file="slskdn-node.test.ts" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>
// @vitest-environment node
import { EventEmitter } from 'node:events';
import { PassThrough, Writable } from 'node:stream';
import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SlskdnNode } from '../e2e/harness/SlskdnNode';
import { MultiPeerHarness } from '../e2e/harness/MultiPeerHarness';

const mocks = vi.hoisted(() => ({ spawn: vi.fn(), failLog: false, logs: [] as any[] }));
vi.mock('node:fs', async (original) => {
  const real = await original<typeof import('node:fs')>();
  return { ...real, createWriteStream: vi.fn((file) => {
    const stream = mocks.failLog
      ? new Writable({ write(chunk, encoding, callback) { callback(new Error('Disk write failed')); } })
      : real.createWriteStream(file);
    mocks.logs.push(stream);
    return stream;
  }) };
});
vi.mock('node:child_process', async (original) => ({ ...await original(), spawn: mocks.spawn }));
vi.mock('node:net', async (original) => {
  const { EventEmitter } = await import('node:events');
  return { ...await original(), Socket: class extends EventEmitter {
    setTimeout() {}
    destroy() {}
    connect() { queueMicrotask(() => this.emit('connect')); }
  } };
});

class Child extends EventEmitter {
  stdout = new PassThrough();
  stderr = new PassThrough();
  exitCode: number | null = null;
  signalCode: string | null = null;
  pid = 123;
  kill = vi.fn((signal: string) => {
    queueMicrotask(() => this.close(signal));
    return true;
  });
  close(signal: string | null = null, code = 0) {
    this.exitCode = code;
    this.signalCode = signal;
    this.stdout.end();
    this.stderr.end();
    this.emit('exit', code, signal);
    queueMicrotask(() => this.emit('close', code, signal));
  }
}

describe('isolated node lifecycle', () => {
  let directory: string;
  let node: SlskdnNode;
  let child: Child;
  beforeEach(async () => {
    mocks.spawn.mockReset();
    mocks.failLog = false;
    mocks.logs = [];
    directory = await fs.mkdtemp(path.join(os.tmpdir(), 'player-harness-'));
    const project = path.join(directory, 'src', 'slskd');
    await fs.mkdir(project, { recursive: true });
    await fs.writeFile(path.join(project, 'slskd.csproj'), '<TargetFramework>net11.0</TargetFramework>');
    await fs.writeFile(path.join(directory, 'slskd.dll'), 'fixture');
    node = new SlskdnNode({ apiPort: 12345, appDir: path.join(directory, 'app'), nodeName: 'A', shareDir: [] });
    vi.spyOn(node as any, 'getRepoRoot').mockReturnValue(directory);
    vi.spyOn(node as any, 'getBuiltAppBaseDir').mockResolvedValue(directory);
    vi.spyOn(node as any, 'syncWebUi').mockResolvedValue(undefined);
    // The API port is supplied; only the Soulseek port needs allocation.
    child = new Child();
    mocks.spawn.mockReturnValue(child);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 200 }));
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(async () => {
    vi.useRealTimers();
    await node.stop();
    await fs.rm(directory, { recursive: true, force: true });
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('clears the hard-kill deadline after graceful shutdown', async () => {
    await node.start();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    await node.stop();
    expect(child.kill).toHaveBeenCalledExactlyOnceWith('SIGTERM');
    expect(vi.getTimerCount()).toBe(0);
  });

  it('flushes complete disk logs and closes both streams', async () => {
    vi.stubEnv('SLSKDN_TEST_KEEP_ARTIFACTS', '1');
    await node.start();
    const stdout = 'a'.repeat(200_000) + '\nstdout final\n';
    const stderr = 'one stderr line\n';
    child.stdout.write(stdout);
    child.stderr.write(stderr);
    await node.stop();
    expect(await fs.readFile(path.join(node.getAppDir(), 'artifacts', 'stdout.log'), 'utf8')).toBe(stdout);
    expect(await fs.readFile(path.join(node.getAppDir(), 'artifacts', 'stderr.log'), 'utf8')).toBe(stderr);
    expect(mocks.logs).toHaveLength(2);
    expect(mocks.logs.every((stream) => stream.closed && stream.writableFinished)).toBe(true);
  });

  it('serializes concurrent cleanup and tolerates repeated Stop', async () => {
    await node.start();
    await Promise.all([node.stop(), node.stop(), node.stop()]);
    await node.stop();
    expect(child.kill).toHaveBeenCalledExactlyOnceWith('SIGTERM');
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
  });

  it('drains already-exited children without signaling them again', async () => {
    await node.start();
    child.close();
    await node.stop();
    expect(child.kill).not.toHaveBeenCalled();
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
  });

  it('forces an unresponsive child to close and clears its deadline', async () => {
    await node.start();
    child.kill.mockImplementation((signal) => {
      if (signal === 'SIGKILL') queueMicrotask(() => child.close(signal));
      return true;
    });
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    const stopped = node.stop();
    await vi.advanceTimersByTimeAsync(5_000);
    await stopped;
    expect(child.kill.mock.calls).toEqual([['SIGTERM'], ['SIGKILL']]);
    expect(vi.getTimerCount()).toBe(0);
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
  });

  it('reports spawn failure through startup and closes partially owned output', async () => {
    child.pid = undefined as any;
    mocks.spawn.mockImplementation(() => {
      queueMicrotask(() => {
        child.emit('error', new Error('Executable unavailable'));
        child.close();
      });
      return child;
    });
    await expect(node.start()).rejects.toThrow('Failed to start slskdn process: Executable unavailable');
    expect(child.kill).not.toHaveBeenCalled();
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
    await expect(fs.access(node.getAppDir())).rejects.toThrow();
  });

  it('surfaces log write failure through awaited cleanup and still closes output', async () => {
    mocks.failLog = true;
    await node.start();
    child.stdout.write('output that cannot be saved');
    await expect(node.stop()).rejects.toThrow('Could not write node log');
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
    await expect(node.stop()).resolves.toBeUndefined();
  });

  it('bounds failure diagnostics without duplicating stderr or truncating disk logs', async () => {
    vi.stubEnv('SLSKDN_TEST_KEEP_ARTIFACTS', '1');
    await node.start();
    const stdout = 'a'.repeat(200_000) + 'stdout final';
    const stderr = 'unique stderr final';
    child.stdout.write(stdout);
    child.stderr.write(stderr);
    child.close(null, 1);
    await node.stop();
    const exit = await fs.readFile(path.join(node.getAppDir(), 'artifacts', 'exit.log'), 'utf8');
    expect(exit.length).toBeLessThan(67_000);
    expect(exit.split(stderr)).toHaveLength(2);
    expect(exit).toContain('stdout final');
    expect(await fs.readFile(path.join(node.getAppDir(), 'artifacts', 'stdout.log'), 'utf8')).toBe(stdout);
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
  });

  it('cleans up a failure after acquiring the child but before registration', async () => {
    const original = (node as any).startProcess.bind(node);
    vi.spyOn(node as any, 'startProcess').mockImplementation(async () => {
      await original();
      throw new Error('Readiness failed');
    });
    await expect(node.start()).rejects.toThrow('Readiness failed');
    expect(child.kill).toHaveBeenCalledExactlyOnceWith('SIGTERM');
    expect(mocks.logs.every((stream) => stream.closed)).toBe(true);
    await expect(fs.access(node.getAppDir())).rejects.toThrow();
  });

  it('awaits every peer cleanup before reporting a failed peer', async () => {
    vi.spyOn(SlskdnNode.prototype, 'start').mockResolvedValue(undefined);
    const harness = new MultiPeerHarness();
    const first = await harness.startNode('A', []);
    const second = await harness.startNode('B', []);
    vi.spyOn(first, 'stop').mockRejectedValue(new Error('First cleanup failed'));
    let release: () => void;
    vi.spyOn(second, 'stop').mockReturnValue(new Promise<void>((resolve) => { release = resolve; }));
    let settled = false;
    const cleanup = harness.stopAll().catch((error) => error);
    cleanup.then(() => { settled = true; });
    await new Promise((resolve) => setImmediate(resolve));
    expect(settled).toBe(false);
    release!();
    const error = await cleanup;
    expect(error).toBeInstanceOf(AggregateError);
    expect(error.errors[0].message).toBe('First cleanup failed');
    expect(harness.getNodeNames()).toEqual([]);
  });

});
