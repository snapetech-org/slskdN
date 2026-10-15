import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi, beforeEach } from 'vitest';
import Visualizer from './Visualizer';
import { createButterchurnEngine } from './visualizers/butterchurnEngine';
import { createNativeMilkdropEngine } from './visualizers/nativeMilkdropEngine';

const butterchurnEngine = {
  dispose: vi.fn(),
  nextPreset: vi.fn(() => 'Butterchurn next'),
  presetName: 'Butterchurn preset',
  render: vi.fn(),
  resize: vi.fn(),
  name: 'Butterchurn',
};

const nativeEngine = {
  dispose: vi.fn(),
  exportPresetFragment: vi.fn((type) => ({
    fileName: `active.${type}`,
    source: `[${type}]\nenabled=1\n`,
  })),
  exportPresetText: vi.fn(() => ({
    fileName: 'active.milk',
    source: 'name=Active\nzoom=1\n',
  })),
  getPresetFragmentSummary: vi.fn(() => ({
    shapes: [{ index: 0, label: 'Shape 1: 5 sides' }],
    waves: [{ index: 0, label: 'Wave 1: 32 samples' }],
  })),
  getPresetDebugSnapshot: vi.fn(() => ({
    format: 'milk',
    parameters: { decay: 0.91, zoom: 1 },
    presetCount: 1,
    shaderSections: { comp: false, warp: true },
    shapes: 1,
    sprites: 0,
    title: 'Native preset',
    waves: 1,
  })),
  getPresetParameterSummary: vi.fn(() => ({
    decay: 0.91,
    wave_r: 0.4,
    zoom: 1,
  })),
  inspectPresetText: vi.fn(() => ({ title: 'Imported native preset' })),
  loadPresetFragmentText: vi.fn((_source, fileName) => ({
    source: `name=Imported native preset\n; merged ${fileName}`,
    title: `Imported native preset + ${fileName}`,
  })),
  loadPresetText: vi.fn(() => 'Imported native preset'),
  nextPreset: vi.fn(() => 'Native next'),
  presetName: 'Native preset',
  render: vi.fn(),
  removePresetFragment: vi.fn((type) => ({
    source: `name=Edited\n; removed ${type}`,
    title: `Edited without ${type}`,
  })),
  randomizePresetParameters: vi.fn(() => ({
    source: 'name=Randomized\nzoom=1.2\nwave_r=0.8',
    title: 'Randomized native preset',
    values: {
      wave_r: 0.8,
      zoom: 1.2,
    },
  })),
  resize: vi.fn(),
  setPresetAutomation: vi.fn(),
  setMouseState: vi.fn(),
  updatePresetBaseValue: vi.fn((key, value) => ({
    source: `name=Edited\n${key}=${value}`,
    title: `Edited ${key}`,
    values: {
      [key]: value,
    },
  })),
  name: 'slskdN MilkDrop WebGL',
};

vi.mock('./audioGraph', () => ({
  getOrCreateAudioGraph: vi.fn(() => ({ ctx: { state: 'suspended' }, visualizerInput: {} })),
  resumeAudioGraph: vi.fn(() =>
    Promise.resolve({
      ctx: {},
      visualizerInput: {},
    })),
  suspendAudioGraph: vi.fn(() => Promise.resolve({ ctx: { state: 'suspended' }, visualizerInput: {} })),
}));

vi.mock('./visualizers/butterchurnEngine', () => ({
  createButterchurnEngine: vi.fn(() => Promise.resolve(butterchurnEngine)),
}));

vi.mock('./visualizers/nativeMilkdropEngine', () => ({
  createNativeMilkdropEngine: vi.fn(() => Promise.resolve(nativeEngine)),
}));

const createFileList = (fileOrFiles) => {
  const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
  files.item = (index) => files[index];
  return files;
};

const createAudioElement = (paused = false) => {
  const audioElement = document.createElement('audio');
  Object.defineProperty(audioElement, 'paused', { configurable: true, value: paused });
  Object.defineProperty(audioElement, 'readyState', {
    configurable: true,
    value: paused ? HTMLMediaElement.HAVE_NOTHING : HTMLMediaElement.HAVE_ENOUGH_DATA,
  });
  return audioElement;
};

const originalMatchMediaDescriptor = Object.getOwnPropertyDescriptor(window, 'matchMedia');

const stubMotionPreference = (initialMatches) => {
  let matches = initialMatches;
  const listeners = new Set();
  const mediaQuery = {
    addEventListener: (_type, listener) => listeners.add(listener),
    get matches() { return matches; },
    media: '(prefers-reduced-motion: reduce)',
    removeEventListener: (_type, listener) => listeners.delete(listener),
  };
  window.matchMedia = vi.fn(() => mediaQuery);

  return (nextMatches) => {
    matches = nextMatches;
    listeners.forEach((listener) => listener({ matches, media: mediaQuery.media }));
  };
};

describe('Visualizer', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    stubMotionPreference(false);
    window.localStorage.clear();
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({}));
    window.requestAnimationFrame = vi.fn(() => 1);
    window.cancelAnimationFrame = vi.fn();
    createButterchurnEngine.mockClear();
    createNativeMilkdropEngine.mockClear();
    butterchurnEngine.dispose.mockClear();
    nativeEngine.dispose.mockClear();
    nativeEngine.exportPresetFragment.mockClear();
    nativeEngine.exportPresetText.mockClear();
    nativeEngine.getPresetDebugSnapshot.mockClear();
    nativeEngine.getPresetFragmentSummary.mockClear();
    nativeEngine.getPresetParameterSummary.mockClear();
    nativeEngine.inspectPresetText.mockClear();
    nativeEngine.loadPresetFragmentText.mockClear();
    nativeEngine.loadPresetText.mockClear();
    nativeEngine.nextPreset.mockClear();
    nativeEngine.randomizePresetParameters.mockClear();
    nativeEngine.removePresetFragment.mockClear();
    nativeEngine.resize.mockClear();
    nativeEngine.render.mockReset();
    nativeEngine.render.mockImplementation(() => {});
    nativeEngine.setMouseState.mockClear();
    nativeEngine.setPresetAutomation.mockClear();
    nativeEngine.updatePresetBaseValue.mockClear();
  });

  afterEach(() => {
    if (originalMatchMediaDescriptor) {
      Object.defineProperty(window, 'matchMedia', originalMatchMediaDescriptor);
    } else {
      delete window.matchMedia;
    }
  });

  it('honors reduced motion and keeps the renderer across presentation changes', async () => {
    stubMotionPreference(true);
    const audioElement = createAudioElement(false);
    const { rerender } = render(
      <Visualizer audioElement={audioElement} mode="inline" onModeChange={vi.fn()} />,
    );

    expect(await screen.findByText(
      'Animation is paused because reduced motion is enabled.',
    )).toBeInTheDocument();
    expect(createButterchurnEngine).not.toHaveBeenCalled();
    expect(window.requestAnimationFrame).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Animate anyway' }));
    await waitFor(() => {
      expect(createButterchurnEngine).toHaveBeenCalledTimes(1);
      expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);
    });

    rerender(
      <Visualizer audioElement={audioElement} mode="fullwindow" onModeChange={vi.fn()} />,
    );

    expect(createButterchurnEngine).toHaveBeenCalledTimes(1);
    expect(butterchurnEngine.dispose).not.toHaveBeenCalled();
    expect(window.cancelAnimationFrame).not.toHaveBeenCalled();

    rerender(<Visualizer audioElement={audioElement} mode="off" onModeChange={vi.fn()} />);
    expect(butterchurnEngine.dispose).toHaveBeenCalledTimes(1);
    rerender(<Visualizer audioElement={audioElement} mode="inline" onModeChange={vi.fn()} />);
    expect(await screen.findByText(
      'Animation is paused because reduced motion is enabled.',
    )).toBeInTheDocument();
    expect(createButterchurnEngine).toHaveBeenCalledTimes(1);
  });

  it('stops an active renderer when the system preference changes to reduced motion', async () => {
    const setMotionPreference = stubMotionPreference(false);
    const audioElement = createAudioElement(false);
    render(<Visualizer audioElement={audioElement} mode="inline" onModeChange={vi.fn()} />);

    await waitFor(() => {
      expect(createButterchurnEngine).toHaveBeenCalledTimes(1);
      expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);
    });
    const frame = window.requestAnimationFrame.mock.results[0].value;

    act(() => setMotionPreference(true));

    expect(await screen.findByText(
      'Animation is paused because reduced motion is enabled.',
    )).toBeInTheDocument();
    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(frame);
    expect(butterchurnEngine.dispose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'Animate anyway' }));
    await waitFor(() => {
      expect(createButterchurnEngine).toHaveBeenCalledTimes(2);
      expect(window.requestAnimationFrame).toHaveBeenCalledTimes(2);
    });
  });

  it('keeps the renderer stopped while paused, buffering, or hidden', async () => {
    const audioElement = createAudioElement(true);
    render(<Visualizer audioElement={audioElement} mode="inline" onModeChange={vi.fn()} />);

    await waitFor(() => expect(createButterchurnEngine).toHaveBeenCalled());
    expect(window.requestAnimationFrame).not.toHaveBeenCalled();

    Object.defineProperty(audioElement, 'paused', { configurable: true, value: false });
    Object.defineProperty(audioElement, 'readyState', {
      configurable: true,
      value: HTMLMediaElement.HAVE_ENOUGH_DATA,
    });
    fireEvent(audioElement, new Event('playing'));
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);
    const playingFrame = window.requestAnimationFrame.mock.results[0].value;

    Object.defineProperty(audioElement, 'paused', { configurable: true, value: true });
    fireEvent(audioElement, new Event('pause'));
    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(playingFrame);
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, 'hidden', { configurable: true, value: true });
    fireEvent(document, new Event('visibilitychange'));
    Object.defineProperty(document, 'hidden', { configurable: true, value: false });
    fireEvent(document, new Event('visibilitychange'));
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1);

    Object.defineProperty(audioElement, 'paused', { configurable: true, value: false });
    fireEvent(audioElement, new Event('playing'));
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(2);
    const resumedFrame = window.requestAnimationFrame.mock.results[1].value;

    fireEvent(audioElement, new Event('waiting'));
    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(resumedFrame);
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(2);
  });

  it('switches to the native engine and imports a local preset', async () => {
    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByTestId('visualizer-switch-engine'));

    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.visualizerEngine')).toBe('native-webgl2');
    });
    expect(createNativeMilkdropEngine).toHaveBeenLastCalledWith(
      expect.objectContaining({ rendererBackend: 'webgl2' }),
    );

    const input = document.querySelector('input[type="file"]');
    const file = new File(['name=Imported native preset\nwave_r=1'], 'imported.milk', {
      type: 'text/plain',
    });
    const fileId = `${file.name}:${file.size}:${file.lastModified}`;
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList(file),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(nativeEngine.inspectPresetText).toHaveBeenCalledWith(
        'name=Imported native preset\nwave_r=1',
        'imported.milk',
      );
    });
    expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
      'name=Imported native preset\nwave_r=1',
      'imported.milk',
      { textureAssets: {} },
    );
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'Imported native preset',
    );
    expect(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary'),
    ).toContain('Imported native preset');

    fireEvent.change(screen.getByTestId('visualizer-native-preset-library'), {
      target: { value: fileId },
    });

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenLastCalledWith(
        'name=Imported native preset\nwave_r=1',
        'imported.milk',
        { textureAssets: {} },
      );
    });

    fireEvent.click(screen.getByTestId('visualizer-clear-native-preset-library'));

    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toBeNull();
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary')).toBeNull();
    expect(screen.queryByTestId('visualizer-native-preset-library')).not.toBeInTheDocument();
  });

  it('cycles visualizer engines through Butterchurn, MilkDrop3 WebGL2, and MilkDrop3 WebGPU', async () => {
    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="fullwindow"
        onModeChange={vi.fn()}
      />,
    );

    await screen.findByTestId('visualizer-switch-engine');
    expect(createButterchurnEngine).toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('visualizer-switch-engine'));
    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.visualizerEngine')).toBe('native-webgl2');
    });
    expect(createNativeMilkdropEngine).toHaveBeenLastCalledWith(
      expect.objectContaining({ rendererBackend: 'webgl2' }),
    );

    fireEvent.click(screen.getByTestId('visualizer-switch-engine'));
    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.visualizerEngine')).toBe('native-webgpu');
    });
    expect(createNativeMilkdropEngine).toHaveBeenLastCalledWith(
      expect.objectContaining({ rendererBackend: 'webgpu' }),
    );

    fireEvent.click(screen.getByTestId('visualizer-switch-engine'));
    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.visualizerEngine')).toBe('butterchurn');
    });
  });

  it('imports compatible native preset batches and reports skipped files', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    nativeEngine.inspectPresetText.mockImplementation((source, fileName) => {
      if (source.includes('warp_shader')) {
        throw new Error('Native MilkDrop preset has shader translation pending: warp_shader.');
      }
      return { title: fileName.replace(/\.milk2?$/, '') };
    });
    nativeEngine.loadPresetText.mockImplementation((source, fileName) =>
      fileName.replace(/\.milk2?$/, ''));

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    const input = document.querySelector('input[type="file"]');
    const firstFile = new File(['name=First\nwave_r=1'], 'first.milk', {
      type: 'text/plain',
    });
    const skippedFile = new File(['warp_shader=shader_body'], 'shader.milk', {
      type: 'text/plain',
    });
    const secondFile = new File(['name=Second\nwave_r=0.5'], 'second.milk', {
      type: 'text/plain',
    });
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList([firstFile, skippedFile, secondFile]),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
        'second.milk',
      );
    });

    const library = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary'),
    );
    expect(library.map((preset) => preset.fileName)).toEqual(['second.milk', 'first.milk']);
    expect(nativeEngine.loadPresetText).toHaveBeenCalledTimes(1);
    expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
      'name=Second\nwave_r=0.5',
      'second.milk',
      { textureAssets: {} },
    );
    expect(screen.getByText(/Imported 2; skipped 1: shader.milk/)).toBeInTheDocument();
  });

  it('imports native .shape and .wave fragments into the active preset', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'base.milk',
        id: 'base',
        source: 'name=Base\nwave_r=1',
        title: 'Base',
      }),
    );

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=Base\nwave_r=1',
        'base.milk',
        { textureAssets: undefined },
      );
    });

    const input = document.querySelector('input[type="file"]');
    const shapeFile = new File(['sides=6\nrad=0.2'], 'hex.shape', {
      type: 'text/plain',
    });
    const waveFile = new File(['samples=32\nper_point_1=x=i;'], 'scope.wave', {
      type: 'text/plain',
    });
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList([shapeFile, waveFile]),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(nativeEngine.loadPresetFragmentText).toHaveBeenCalledWith(
        'sides=6\nrad=0.2',
        'hex.shape',
        { textureAssets: {} },
      );
    });
    expect(nativeEngine.loadPresetFragmentText).toHaveBeenCalledWith(
      'samples=32\nper_point_1=x=i;',
      'scope.wave',
      { textureAssets: {} },
    );
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'scope.wave',
    );
    const library = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary'),
    );
    expect(library[0]).toEqual(expect.objectContaining({
      id: 'base',
      title: 'Imported native preset + scope.wave',
    }));
  });

  it('exports native shape and wave fragments from the active preset', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    const createObjectUrl = vi.fn(() => 'blob:native-fragment');
    const revokeObjectUrl = vi.fn();
    Object.defineProperty(window.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl,
    });
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl,
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('visualizer-export-native-shape'));
    fireEvent.click(screen.getByTestId('visualizer-export-native-wave'));

    expect(nativeEngine.exportPresetFragment).toHaveBeenCalledWith('shape', 0);
    expect(nativeEngine.exportPresetFragment).toHaveBeenCalledWith('wave', 0);
    expect(createObjectUrl).toHaveBeenCalledTimes(2);
    expect(clickSpy).toHaveBeenCalledTimes(2);
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:native-fragment');
    clickSpy.mockRestore();
  });

  it('exports the active native preset text', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    const createObjectUrl = vi.fn(() => 'blob:native-preset');
    const revokeObjectUrl = vi.fn();
    Object.defineProperty(window.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl,
    });
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl,
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByTestId('visualizer-export-native-preset'));

    expect(nativeEngine.exportPresetText).toHaveBeenCalled();
    expect(createObjectUrl).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:native-preset');
    clickSpy.mockRestore();
  });

  it('selects and removes native shape and wave fragments from the active preset', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'editable.milk',
        id: 'editable',
        source: 'name=Editable\nshape00_sides=3\nshape01_sides=8\nwavecode_0_samples=32',
        title: 'Editable',
      }),
    );
    nativeEngine.getPresetFragmentSummary.mockReturnValue({
      shapes: [
        { index: 0, label: 'Shape 1: 3 sides' },
        { index: 1, label: 'Shape 2: 8 sides' },
      ],
      waves: [
        { index: 0, label: 'Wave 1: 32 samples' },
        { index: 1, label: 'Wave 2: 64 samples' },
      ],
    });
    nativeEngine.removePresetFragment.mockImplementation((type, index) => ({
      source: `name=Editable\n; removed ${type} ${index}`,
      title: `Editable without ${type} ${index}`,
    }));

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    expect(await screen.findByRole('option', { name: 'Shape 2: 8 sides' })).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('visualizer-native-shape-fragment'), {
      target: { value: '1' },
    });
    fireEvent.click(screen.getByTestId('visualizer-remove-native-shape'));

    expect(nativeEngine.removePresetFragment).toHaveBeenCalledWith('shape', 1, {
      textureAssets: undefined,
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'Editable without shape 1',
    );

    fireEvent.change(screen.getByTestId('visualizer-native-wave-fragment'), {
      target: { value: '1' },
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    fireEvent.click(screen.getByTestId('visualizer-export-native-wave'));
    expect(nativeEngine.exportPresetFragment).toHaveBeenCalledWith('wave', 1);
    clickSpy.mockRestore();
  });

  it('applies native preset parameter edits to a browser-local edited copy', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'editable.milk',
        id: 'editable',
        source: 'name=Editable\nzoom=1',
        textureAssets: {
          cover: { dataUrl: 'data:image/png;base64,fixture', fileName: 'cover.png' },
        },
        title: 'Editable',
      }),
    );

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    expect(await screen.findByTestId('visualizer-native-parameter')).toHaveValue('decay');
    fireEvent.change(screen.getByTestId('visualizer-native-parameter'), {
      target: { value: 'zoom' },
    });
    fireEvent.change(screen.getByTestId('visualizer-native-parameter-value'), {
      target: { value: '1.25' },
    });
    fireEvent.click(screen.getByTestId('visualizer-apply-native-parameter'));

    expect(nativeEngine.updatePresetBaseValue).toHaveBeenCalledWith('zoom', 1.25, {
      textureAssets: {
        cover: { dataUrl: 'data:image/png;base64,fixture', fileName: 'cover.png' },
      },
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'Edited zoom',
    );
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary')).toContain(
      'zoom=1.25',
    );
  });

  it('randomizes native parameters and toggles debug details', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'editable.milk',
        id: 'editable',
        source: 'name=Editable\nzoom=1',
        title: 'Editable',
      }),
    );

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await screen.findByTestId('visualizer-randomize-native-parameters');
    await waitFor(() => expect(createNativeMilkdropEngine).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByTestId('visualizer-randomize-native-parameters'));
    expect(nativeEngine.randomizePresetParameters).toHaveBeenCalledWith({
      textureAssets: undefined,
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'Randomized native preset',
    );
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary')).toContain(
      'wave_r=0.8',
    );

    fireEvent.click(screen.getByTestId('visualizer-toggle-native-debug'));
    expect(screen.getByTestId('visualizer-native-debug')).toHaveTextContent('Native preset');
    expect(screen.getByTestId('visualizer-native-debug')).toHaveTextContent('1 shapes');
    fireEvent.change(screen.getByTestId('visualizer-native-fps-cap'), {
      target: { value: '30' },
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropFpsCap')).toBe('30');
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropQuality')).toBe('custom');
    fireEvent.change(screen.getByTestId('visualizer-native-quality'), {
      target: { value: 'efficient' },
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropQuality')).toBe('efficient');
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropFpsCap')).toBe('30');
    expect(createNativeMilkdropEngine).toHaveBeenCalledTimes(1);
    expect(nativeEngine.dispose).not.toHaveBeenCalled();
  });

  it('feeds normalized pointer state into the native engine', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    const visualizer = await screen.findByTestId('player-visualizer');
    vi.spyOn(visualizer, 'getBoundingClientRect').mockReturnValue({
      bottom: 100,
      height: 100,
      left: 0,
      right: 200,
      top: 0,
      width: 200,
      x: 0,
      y: 0,
      toJSON: () => {},
    });

    fireEvent.pointerMove(visualizer, {
      buttons: 1,
      clientX: 150,
      clientY: 25,
    });
    fireEvent.pointerUp(visualizer);

    expect(nativeEngine.setMouseState).toHaveBeenCalledWith({
      mouse_down: 1,
      mouse_dx: 0.25,
      mouse_dy: -0.25,
      mouse_x: 0.75,
      mouse_y: 0.25,
    });
    expect(nativeEngine.setMouseState).toHaveBeenLastCalledWith({
      mouse_down: 0,
      mouse_dx: 0,
      mouse_dy: 0,
    });
  });

  it('cycles and persists native automatic preset change modes', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.setPresetAutomation).toHaveBeenCalledWith({
        beatsPerPreset: 8,
        mode: 'off',
        timedIntervalSeconds: 30,
      });
    });

    fireEvent.click(screen.getByTestId('visualizer-native-automation'));
    expect(
      JSON.parse(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetAutomation')),
    ).toEqual({
      beatsPerPreset: 8,
      mode: 'beat',
      timedIntervalSeconds: 30,
    });
    await waitFor(() => {
      expect(nativeEngine.setPresetAutomation).toHaveBeenCalledWith({
        beatsPerPreset: 8,
        mode: 'beat',
        timedIntervalSeconds: 30,
      });
    });

    fireEvent.change(screen.getByTestId('visualizer-native-automation-beats'), {
      target: { value: '16' },
    });
    await waitFor(() => {
      expect(nativeEngine.setPresetAutomation).toHaveBeenCalledWith({
        beatsPerPreset: 16,
        mode: 'beat',
        timedIntervalSeconds: 30,
      });
    });

    fireEvent.click(screen.getByTestId('visualizer-native-automation'));
    await waitFor(() => {
      expect(nativeEngine.setPresetAutomation).toHaveBeenCalledWith({
        beatsPerPreset: 16,
        mode: 'timed',
        timedIntervalSeconds: 30,
      });
    });

    fireEvent.change(screen.getByTestId('visualizer-native-automation-interval'), {
      target: { value: '60' },
    });
    await waitFor(() => {
      expect(nativeEngine.setPresetAutomation).toHaveBeenCalledWith({
        beatsPerPreset: 16,
        mode: 'timed',
        timedIntervalSeconds: 60,
      });
    });
  });

  it('updates displayed native preset name when automation advances', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    let animationFrameCalled = false;
    window.requestAnimationFrame = vi.fn((callback) => {
      if (!animationFrameCalled) {
        animationFrameCalled = true;
        callback();
      }
      return 1;
    });
    nativeEngine.render.mockImplementationOnce(() => ({
      presetName: 'Native automated next',
    }));

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="fullwindow"
        onModeChange={vi.fn()}
      />,
    );

    expect(await screen.findByText(/Native automated next/)).toBeInTheDocument();
  });

  it('stores selected image assets with imported native presets', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    vi.stubGlobal('FileReader', class {
      readAsDataURL() {
        this.result = 'data:image/png;base64,fixture';
        this.onload();
      }
    });

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    const input = document.querySelector('input[type="file"]');
    const presetFile = new File(
      ['name=Textured\nshape00_enabled=1\nshape00_texture=cover.png'],
      'textured.milk',
      { type: 'text/plain' },
    );
    const textureFile = new File(['fixture'], 'cover.png', { type: 'image/png' });
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList([presetFile, textureFile]),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=Textured\nshape00_enabled=1\nshape00_texture=cover.png',
        'textured.milk',
        {
          textureAssets: expect.objectContaining({
            'cover.png': expect.objectContaining({
              dataUrl: 'data:image/png;base64,fixture',
            }),
            cover: expect.objectContaining({
              dataUrl: 'data:image/png;base64,fixture',
            }),
          }),
        },
      );
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
      'cover.png',
    );
  });

  it('stores only referenced image assets with each imported native preset', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    nativeEngine.inspectPresetText.mockImplementation((_source, fileName) => ({
      title: fileName.replace(/\.milk$/, ''),
    }));
    nativeEngine.loadPresetText.mockImplementation((_source, fileName) =>
      fileName.replace(/\.milk$/, ''));
    vi.stubGlobal('FileReader', class {
      readAsDataURL(file) {
        this.result = `data:${file.name}`;
        this.onload();
      }
    });

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    const input = document.querySelector('input[type="file"]');
    const firstPreset = new File(
      ['name=First\nshape00_enabled=1\nshape00_texture=art/first.png'],
      'first.milk',
      { type: 'text/plain' },
    );
    const secondPreset = new File(
      ['name=Second\nsprite00_enabled=1\nsprite00_image=second.png'],
      'second.milk',
      { type: 'text/plain' },
    );
    const firstImage = new File(['first'], 'first.png', { type: 'image/png' });
    const secondImage = new File(['second'], 'second.png', { type: 'image/png' });
    Object.defineProperty(firstImage, 'webkitRelativePath', {
      configurable: true,
      value: 'pack/art/first.png',
    });
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList([firstPreset, secondPreset, firstImage, secondImage]),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toContain(
        'second.milk',
      );
    });

    const activePreset = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPreset'),
    );
    expect(Object.keys(activePreset.textureAssets).sort()).toEqual(['second', 'second.png']);

    const library = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary'),
    );
    const firstEntry = library.find((preset) => preset.fileName === 'first.milk');
    expect(Object.keys(firstEntry.textureAssets).sort()).toEqual([
      'first',
      'first.png',
      'pack/art/first.png',
    ]);
    expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
      'name=Second\nsprite00_enabled=1\nsprite00_image=second.png',
      'second.milk',
      {
        textureAssets: expect.not.objectContaining({
          first: expect.anything(),
        }),
      },
    );
  });

  it('imports native preset folders with relative asset paths', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    nativeEngine.inspectPresetText.mockImplementation((_source, fileName) => ({
      title: fileName.replace(/\.milk$/, ''),
    }));
    nativeEngine.loadPresetText.mockImplementation((_source, fileName) =>
      fileName.replace(/\.milk$/, ''));
    vi.stubGlobal('FileReader', class {
      readAsDataURL(file) {
        this.result = `data:${file.name}`;
        this.onload();
      }
    });

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    const folderInput = screen.getByTestId('visualizer-native-pack-input');
    expect(folderInput).toHaveAttribute('webkitdirectory');
    expect(folderInput).toHaveAttribute('directory');

    const clickSpy = vi.spyOn(folderInput, 'click').mockImplementation(() => {});
    fireEvent.click(screen.getByTestId('visualizer-import-native-preset-folder'));
    expect(clickSpy).toHaveBeenCalled();

    const presetFile = new File(
      ['name=Pack\nsprite00_enabled=1\nsprite00_image=assets/cover.png'],
      'pack.milk',
      { type: 'text/plain' },
    );
    const textureFile = new File(['cover'], 'cover.png', { type: 'image/png' });
    Object.defineProperty(presetFile, 'webkitRelativePath', {
      configurable: true,
      value: 'pack/presets/pack.milk',
    });
    Object.defineProperty(textureFile, 'webkitRelativePath', {
      configurable: true,
      value: 'pack/assets/cover.png',
    });
    Object.defineProperty(folderInput, 'files', {
      configurable: true,
      value: createFileList([presetFile, textureFile]),
    });
    fireEvent.change(folderInput);

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=Pack\nsprite00_enabled=1\nsprite00_image=assets/cover.png',
        'pack.milk',
        {
          textureAssets: expect.objectContaining({
            'pack/assets/cover.png': expect.objectContaining({
              dataUrl: 'data:cover.png',
            }),
            'cover.png': expect.objectContaining({
              dataUrl: 'data:cover.png',
            }),
            cover: expect.objectContaining({
              dataUrl: 'data:cover.png',
            }),
          }),
        },
      );
    });
  });

  it('reports skipped native texture assets during import', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.resize).toHaveBeenCalled();
    });

    const input = document.querySelector('input[type="file"]');
    const presetFile = new File(['name=Textured\nshape00_texture=huge.png'], 'textured.milk', {
      type: 'text/plain',
    });
    const textureFile = new File(['fixture'], 'huge.png', { type: 'image/png' });
    Object.defineProperty(textureFile, 'size', {
      configurable: true,
      value: 1024 * 1024 + 1,
    });
    Object.defineProperty(input, 'files', {
      configurable: true,
      value: createFileList([presetFile, textureFile]),
    });
    fireEvent.change(input);

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=Textured\nshape00_texture=huge.png',
        'textured.milk',
        { textureAssets: {} },
      );
    });
    expect(screen.getByText(/Skipped 1 texture asset: huge.png/)).toBeInTheDocument();
  });

  it('removes only the selected native preset from the local library', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'first.milk',
        id: 'first',
        source: 'name=First\nwave_r=1',
        title: 'First',
      }),
    );
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPresetLibrary',
      JSON.stringify([
        {
          fileName: 'first.milk',
          id: 'first',
          source: 'name=First\nwave_r=1',
          title: 'First',
        },
        {
          fileName: 'second.milk',
          id: 'second',
          source: 'name=Second\nwave_r=0.5',
          title: 'Second',
        },
      ]),
    );

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=First\nwave_r=1',
        'first.milk',
        { textureAssets: undefined },
      );
    });

    fireEvent.click(screen.getByTestId('visualizer-remove-native-preset'));

    const library = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibrary'),
    );
    expect(library.map((preset) => preset.id)).toEqual(['second']);
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toBeNull();
    expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('');
  });

  it('supports native preset favorites, history, next, and random library jumps', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'first.milk',
        id: 'first',
        source: 'name=First\nwave_r=1',
        title: 'First',
      }),
    );
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPresetLibrary',
      JSON.stringify([
        {
          fileName: 'first.milk',
          id: 'first',
          source: 'name=First\nwave_r=1',
          title: 'First',
        },
        {
          fileName: 'second.milk',
          id: 'second',
          source: 'name=Second\nwave_r=0.5',
          title: 'Second',
        },
        {
          fileName: 'third.milk',
          id: 'third',
          source: 'name=Third\nwave_b=1',
          title: 'Third',
        },
      ]),
    );
    nativeEngine.loadPresetText.mockImplementation((_source, fileName) =>
      fileName.replace(/\.milk$/, ''));
    const randomSpy = vi.spyOn(Math, 'random').mockReturnValue(0.9);

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=First\nwave_r=1',
        'first.milk',
        { textureAssets: undefined },
      );
    });

    fireEvent.click(screen.getByTestId('visualizer-toggle-native-favorite'));
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetFavorites')).toContain(
      'first',
    );

    fireEvent.click(screen.getByTestId('visualizer-next-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('second');
    });
    expect(nativeEngine.nextPreset).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('visualizer-previous-native-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('first');
    });

    fireEvent.click(screen.getByTestId('visualizer-random-native-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('third');
    });
    expect(randomSpy).toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('visualizer-toggle-native-favorites-only'));
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetLibraryMode')).toBe(
      'favorites',
    );
    expect(screen.getByRole('option', { name: '(favorite) First' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Second' })).not.toBeInTheDocument();
    randomSpy.mockRestore();
  });

  it('filters the native preset bank search and scopes native next navigation', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'first.milk',
        id: 'first',
        source: 'name=First\nwave_r=1',
        title: 'First',
      }),
    );
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPresetLibrary',
      JSON.stringify([
        {
          fileName: 'first.milk',
          id: 'first',
          source: 'name=First\nwave_r=1',
          title: 'First',
        },
        {
          fileName: 'second.milk',
          id: 'second',
          source: 'name=Second\nwave_r=0.5',
          title: 'Second',
        },
        {
          fileName: 'third-grid.milk',
          id: 'third',
          source: 'name=Third Grid\nwave_b=1',
          title: 'Third Grid',
        },
      ]),
    );
    nativeEngine.loadPresetText.mockImplementation((_source, fileName) =>
      fileName.replace(/\.milk$/, ''));

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=First\nwave_r=1',
        'first.milk',
        { textureAssets: undefined },
      );
    });

    fireEvent.change(screen.getByTestId('visualizer-native-preset-search'), {
      target: { value: 'grid' },
    });
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetSearch')).toBe('grid');
    expect(screen.getByRole('option', { name: 'Third Grid' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Second' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('visualizer-next-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('third');
    });

    fireEvent.change(screen.getByTestId('visualizer-native-preset-search'), {
      target: { value: 'missing' },
    });
    expect(screen.getByText('No matches')).toBeInTheDocument();
    expect(screen.getByTestId('visualizer-next-preset')).toBeDisabled();

    fireEvent.click(screen.getByTestId('visualizer-clear-native-preset-search'));
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetSearch')).toBeNull();
    expect(screen.getByTestId('visualizer-native-preset-search')).toHaveValue('');
    expect(screen.getByRole('option', { name: 'Second' })).toBeInTheDocument();
  });

  it('saves, scopes, clears, and removes native preset playlists', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'first.milk',
        id: 'first',
        source: 'name=First\nwave_r=1',
        title: 'First',
      }),
    );
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPresetLibrary',
      JSON.stringify([
        {
          fileName: 'first.milk',
          id: 'first',
          source: 'name=First\nwave_r=1',
          title: 'First',
        },
        {
          fileName: 'warm-grid.milk',
          id: 'second',
          source: 'name=Warm Grid\nwave_r=0.5',
          title: 'Warm Grid',
        },
        {
          fileName: 'cold-grid.milk',
          id: 'third',
          source: 'name=Cold Grid\nwave_b=1',
          title: 'Cold Grid',
        },
      ]),
    );
    nativeEngine.loadPresetText.mockImplementation((_source, fileName) =>
      fileName.replace(/\.milk$/, ''));
    const promptSpy = vi.spyOn(window, 'prompt')
      .mockReturnValueOnce('Grid playlist')
      .mockReturnValueOnce('Renamed grid');

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(nativeEngine.loadPresetText).toHaveBeenCalledWith(
        'name=First\nwave_r=1',
        'first.milk',
        { textureAssets: undefined },
      );
    });

    fireEvent.change(screen.getByTestId('visualizer-native-preset-search'), {
      target: { value: 'grid' },
    });
    fireEvent.click(screen.getByTestId('visualizer-save-native-playlist'));

    const storedPlaylists = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetPlaylists'),
    );
    expect(storedPlaylists).toHaveLength(1);
    expect(storedPlaylists[0]).toEqual(expect.objectContaining({
      name: 'Grid playlist',
      presetIds: ['second', 'third'],
    }));
    expect(
      window.localStorage.getItem('slskdn.player.nativeMilkdropActivePresetPlaylist'),
    ).toBe(storedPlaylists[0].id);

    fireEvent.click(screen.getByTestId('visualizer-rename-native-playlist'));
    const renamedPlaylists = JSON.parse(
      window.localStorage.getItem('slskdn.player.nativeMilkdropPresetPlaylists'),
    );
    expect(renamedPlaylists[0]).toEqual(expect.objectContaining({
      name: 'Renamed grid',
    }));

    fireEvent.click(screen.getByTestId('visualizer-clear-native-preset-search'));
    expect(screen.queryByRole('option', { name: 'First' })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Warm Grid' })).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('visualizer-next-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('second');
    });
    fireEvent.click(screen.getByTestId('visualizer-next-preset'));
    await waitFor(() => {
      expect(screen.getByTestId('visualizer-native-preset-library')).toHaveValue('third');
    });

    fireEvent.click(screen.getByTestId('visualizer-clear-active-native-playlist'));
    expect(
      window.localStorage.getItem('slskdn.player.nativeMilkdropActivePresetPlaylist'),
    ).toBeNull();
    expect(screen.getByRole('option', { name: 'First' })).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('visualizer-native-playlist'), {
      target: { value: storedPlaylists[0].id },
    });
    fireEvent.click(screen.getByTestId('visualizer-remove-native-playlist'));
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPresetPlaylists')).toBeNull();
    expect(screen.queryByTestId('visualizer-native-playlist')).not.toBeInTheDocument();
    promptSpy.mockRestore();
  });

  it('surfaces native render errors and clears the persisted imported preset', async () => {
    window.localStorage.setItem('slskdn.player.visualizerEngine', 'native');
    window.localStorage.setItem(
      'slskdn.player.nativeMilkdropPreset',
      JSON.stringify({
        fileName: 'bad.milk',
        source: 'per_frame_1=q1=rand(1);',
      }),
    );
    window.requestAnimationFrame = vi.fn((callback) => {
      callback();
      return 1;
    });
    nativeEngine.render.mockImplementationOnce(() => {
      throw new Error('Unsupported MilkDrop function: rand');
    });

    render(
      <Visualizer
        audioElement={createAudioElement()}
        mode="inline"
        onModeChange={vi.fn()}
      />,
    );

    expect(
      await screen.findByText('Native MilkDrop render failed.'),
    ).toBeInTheDocument();
    expect(window.localStorage.getItem('slskdn.player.nativeMilkdropPreset')).toBeNull();
  });
});
