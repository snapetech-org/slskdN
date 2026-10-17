import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Icon, Popup } from 'semantic-ui-react';
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from '../../lib/storage';
import usePrefersReducedMotion from '../../lib/usePrefersReducedMotion';
import { getOrCreateAudioGraph, resumeAudioGraph, suspendAudioGraph } from './audioGraph';
import SpectrumAnalyzer from './SpectrumAnalyzer';
import { createButterchurnEngine } from './visualizers/butterchurnEngine';
import { createNativeMilkdropEngine } from './visualizers/nativeMilkdropEngine';

const visualizerEngineStorageKey = 'slskdn.player.visualizerEngine';
const nativePresetStorageKey = 'slskdn.player.nativeMilkdropPreset';
const nativePresetLibraryStorageKey = 'slskdn.player.nativeMilkdropPresetLibrary';
const nativePresetAutomationStorageKey = 'slskdn.player.nativeMilkdropPresetAutomation';
const nativePresetFavoritesStorageKey = 'slskdn.player.nativeMilkdropPresetFavorites';
const nativePresetFpsCapStorageKey = 'slskdn.player.nativeMilkdropFpsCap';
const nativePresetQualityStorageKey = 'slskdn.player.nativeMilkdropQuality';
const nativePresetLibraryModeStorageKey = 'slskdn.player.nativeMilkdropPresetLibraryMode';
const nativePresetSearchStorageKey = 'slskdn.player.nativeMilkdropPresetSearch';
const nativePresetPlaylistsStorageKey = 'slskdn.player.nativeMilkdropPresetPlaylists';
const activeNativePresetPlaylistStorageKey = 'slskdn.player.nativeMilkdropActivePresetPlaylist';
const nativePresetLibraryLimit = 20;
const nativePresetHistoryLimit = 12;
const nativePresetPlaylistLimit = 12;
const nativeTextureAssetMaxBytes = 1024 * 1024;
const nativeEditableParameters = [
  {
    defaultValue: 0.9,
    key: 'decay',
    get label() { return interfaceText("Decay"); },
    max: 1,
    min: 0.5,
    step: 0.01,
  },
  {
    defaultValue: 1,
    key: 'zoom',
    get label() { return interfaceText("Zoom"); },
    max: 1.5,
    min: 0.5,
    step: 0.01,
  },
  {
    defaultValue: 0,
    key: 'rot',
    get label() { return interfaceText("Rotation"); },
    max: 0.5,
    min: -0.5,
    step: 0.01,
  },
  {
    defaultValue: 0.7,
    key: 'wave_r',
    get label() { return interfaceText("Wave red"); },
    max: 1,
    min: 0,
    step: 0.01,
  },
  {
    defaultValue: 0.7,
    key: 'wave_g',
    get label() { return interfaceText("Wave green"); },
    max: 1,
    min: 0,
    step: 0.01,
  },
  {
    defaultValue: 0.7,
    key: 'wave_b',
    get label() { return interfaceText("Wave blue"); },
    max: 1,
    min: 0,
    step: 0.01,
  },
  {
    defaultValue: 1,
    key: 'wave_a',
    get label() { return interfaceText("Wave alpha"); },
    max: 1,
    min: 0,
    step: 0.01,
  },
];

const readStoredEngine = () => {
  const stored = getLocalStorageItem(visualizerEngineStorageKey);
  if (stored === 'native') return 'native-webgl2';
  return ['butterchurn', 'native-webgl2', 'native-webgpu'].includes(stored)
    ? stored
    : 'butterchurn';
};

const visualizerEngineModes = ['butterchurn', 'native-webgl2', 'native-webgpu'];

const isNativeEngine = (engine) => engine === 'native-webgl2' || engine === 'native-webgpu';

const getNativeRendererBackend = (engine) => (engine === 'native-webgpu' ? 'webgpu' : 'webgl2');

const getNextEngine = (engine) => {
  const index = visualizerEngineModes.indexOf(engine);
  return visualizerEngineModes[(index + 1) % visualizerEngineModes.length];
};

const getEngineLabel = (engine) => {
  if (engine === 'native-webgl2') return 'MilkDrop3 WebGL2';
  if (engine === 'native-webgpu') return 'MilkDrop3 WebGPU';
  return 'Butterchurn';
};

const getEngineIcon = (engine) => {
  if (engine === 'native-webgpu') return 'bolt';
  if (engine === 'native-webgl2') return 'microchip';
  return 'magic';
};

const isPromiseLike = (value) => value && typeof value.then === 'function';

const getNextNativeAutomationMode = (mode) => {
  if (mode === 'off') return 'beat';
  if (mode === 'beat') return 'timed';
  return 'off';
};

const getNativeAutomationLabel = (mode) => {
  if (mode === 'beat') return interfaceText('Beat');
  if (mode === 'timed') return interfaceText('Timed');
  return interfaceText('Off');
};

const defaultNativeAutomationSettings = {
  beatsPerPreset: 8,
  mode: 'off',
  timedIntervalSeconds: 30,
};

const normalizeNativeAutomationSettings = (settings = {}) => ({
  ...defaultNativeAutomationSettings,
  ...settings,
  beatsPerPreset: [4, 8, 16].includes(Number(settings.beatsPerPreset))
    ? Number(settings.beatsPerPreset)
    : defaultNativeAutomationSettings.beatsPerPreset,
  mode: ['beat', 'timed'].includes(settings.mode) ? settings.mode : 'off',
  timedIntervalSeconds: [15, 30, 60].includes(Number(settings.timedIntervalSeconds))
    ? Number(settings.timedIntervalSeconds)
    : defaultNativeAutomationSettings.timedIntervalSeconds,
});

const readStoredNativeAutomationSettings = () => {
  const stored = getLocalStorageItem(nativePresetAutomationStorageKey);
  if (['beat', 'timed', 'off'].includes(stored)) {
    return normalizeNativeAutomationSettings({ mode: stored });
  }
  try {
    return normalizeNativeAutomationSettings(JSON.parse(stored || '{}'));
  } catch {
    return defaultNativeAutomationSettings;
  }
};

const writeStoredNativeAutomationSettings = (settings) => {
  setLocalStorageItem(
    nativePresetAutomationStorageKey,
    JSON.stringify(normalizeNativeAutomationSettings(settings)),
  );
};

const getNativeEditableParameter = (key) =>
  nativeEditableParameters.find((parameter) => parameter.key === key)
  || nativeEditableParameters[0];

const readStoredNativeFpsCap = () => {
  const value = getLocalStorageItem(nativePresetFpsCapStorageKey, 'full');
  return ['full', '60', '30', '24'].includes(value) ? value : 'full';
};

const getNativeFpsCapMs = (fpsCap) => {
  if (fpsCap === '60') return 1000 / 60;
  if (fpsCap === '30') return 1000 / 30;
  if (fpsCap === '24') return 1000 / 24;
  return 0;
};

const nativeQualityPresets = {
  balanced: {
    fpsCap: '60',
    get label() { return interfaceText("Balanced"); },
  },
  efficient: {
    fpsCap: '30',
    get label() { return interfaceText("Efficient"); },
  },
  full: {
    fpsCap: 'full',
    get label() { return interfaceText("Full"); },
  },
};

const readStoredNativeQuality = () => {
  const value = getLocalStorageItem(nativePresetQualityStorageKey, 'balanced');
  return Object.keys(nativeQualityPresets).includes(value) || value === 'custom'
    ? value
    : 'balanced';
};

const nativeWebGpuReasonSources = new Set([
  'navigator.gpu unavailable',
  'WebGPU adapter request failed',
  'WebGPU adapter unavailable',
  'WebGPU device request failed',
  'WebGPU unavailable',
  'WebGPU renderer failed',
]);

const getNativeWebGpuDebugLabel = (status = {}) => {
  if (!status.available) {
    const reason = nativeWebGpuReasonSources.has(status.reason)
      ? interfaceText(status.reason)
      : status.reason;
    return reason
      ? interfaceText('WebGL2 baseline ({reason})', { reason })
      : interfaceText('WebGL2 baseline');
  }
  const adapterLabel = [
    status.adapterInfo?.vendor,
    status.adapterInfo?.architecture,
    status.adapterInfo?.device,
  ].filter(Boolean).join(' ');
  return adapterLabel
    ? interfaceText('WebGPU {adapter}', { adapter: adapterLabel })
    : interfaceText('WebGPU adapter ready');
};

const getVisualizerErrorMessage = (engineType, error) => {
  const message = error?.message || '';
  const localizedWebGpuErrorSources = new Set([
    'WebGPU is unavailable for the native MilkDrop renderer.',
    'WebGPU adapter is unavailable for the native MilkDrop renderer.',
    'WebGPU canvas context is unavailable for the native MilkDrop renderer.',
  ]);
  const detail = localizedWebGpuErrorSources.has(message)
    ? ` ${interfaceText(message)}`
    : '';
  return isNativeEngine(engineType)
    ? `${interfaceText('Native MilkDrop render failed.')}${detail}`
    : interfaceText('MilkDrop failed. Showing analyzer fallback.');
};

const readStoredNativePreset = () => {
  try {
    const preset = JSON.parse(getLocalStorageItem(nativePresetStorageKey, 'null'));
    return preset && typeof preset === 'object' && !Array.isArray(preset)
      ? preset
      : null;
  } catch {
    return null;
  }
};

const readStoredNativePresetLibrary = () => {
  try {
    const library = JSON.parse(
      getLocalStorageItem(nativePresetLibraryStorageKey, '[]'),
    );
    return Array.isArray(library)
      ? library.filter((preset) => preset?.id && preset?.source)
      : [];
  } catch {
    return [];
  }
};

const readStoredNativePresetFavorites = () => {
  try {
    const favorites = JSON.parse(
      getLocalStorageItem(nativePresetFavoritesStorageKey, '[]'),
    );
    return Array.isArray(favorites)
      ? favorites.filter((id) => typeof id === 'string' && id.length > 0)
      : [];
  } catch {
    return [];
  }
};

const readStoredNativePresetLibraryMode = () => {
  return getLocalStorageItem(nativePresetLibraryModeStorageKey) === 'favorites'
    ? 'favorites'
    : 'all';
};

const readStoredNativePresetSearch = () => {
  return getLocalStorageItem(nativePresetSearchStorageKey, '');
};

const readStoredNativePresetPlaylists = () => {
  try {
    const playlists = JSON.parse(
      getLocalStorageItem(nativePresetPlaylistsStorageKey, '[]'),
    );
    return Array.isArray(playlists)
      ? playlists
        .filter((playlist) =>
          playlist?.id
          && playlist?.name
          && Array.isArray(playlist?.presetIds))
        .map((playlist) => ({
          ...playlist,
          presetIds: playlist.presetIds.filter((id) => typeof id === 'string' && id.length > 0),
        }))
        .filter((playlist) => playlist.presetIds.length > 0)
      : [];
  } catch {
    return [];
  }
};

const readStoredActiveNativePresetPlaylistId = () => {
  return getLocalStorageItem(activeNativePresetPlaylistStorageKey, '');
};

const writeStoredNativePresetLibrary = (library) => {
  setLocalStorageItem(
    nativePresetLibraryStorageKey,
    JSON.stringify(library.slice(0, nativePresetLibraryLimit)),
  );
};

const writeStoredNativePresetFavorites = (favoriteIds) => {
  if (favoriteIds.length === 0) {
    removeLocalStorageItem(nativePresetFavoritesStorageKey);
    return;
  }
  setLocalStorageItem(
    nativePresetFavoritesStorageKey,
    JSON.stringify(favoriteIds),
  );
};

const writeStoredNativePresetPlaylists = (playlists) => {
  if (playlists.length === 0) {
    removeLocalStorageItem(nativePresetPlaylistsStorageKey);
    return;
  }
  setLocalStorageItem(
    nativePresetPlaylistsStorageKey,
    JSON.stringify(playlists.slice(0, nativePresetPlaylistLimit)),
  );
};

const upsertNativePresetLibraryEntry = (library, entry) => [
  entry,
  ...library.filter((preset) => preset.id !== entry.id),
].slice(0, nativePresetLibraryLimit);

const pruneNativePresetFavorites = (favoriteIds, library) => {
  const libraryIds = new Set(library.map((preset) => preset.id));
  return favoriteIds.filter((id) => libraryIds.has(id));
};

const pruneNativePresetPlaylists = (playlists, library) => {
  const libraryIds = new Set(library.map((preset) => preset.id));
  return playlists
    .map((playlist) => ({
      ...playlist,
      presetIds: playlist.presetIds.filter((id) => libraryIds.has(id)),
    }))
    .filter((playlist) => playlist.presetIds.length > 0)
    .slice(0, nativePresetPlaylistLimit);
};

const getNativePresetSearchText = (preset) =>
  [preset.title, preset.fileName].filter(Boolean).join(' ').toLowerCase();

const filterNativePresetLibrary = (library, search) => {
  const query = search.trim().toLowerCase();
  if (!query) return library;
  const terms = query.split(/\s+/).filter(Boolean);
  return library.filter((preset) => {
    const text = getNativePresetSearchText(preset);
    return terms.every((term) => text.includes(term));
  });
};

const getNativePresetPlaylistName = ({ mode, search }) => {
  const query = search.trim();
  if (query) return `Search: ${query}`;
  if (mode === 'favorites') return 'Favorites';
  return 'Native playlist';
};

const getNativePresetPlaylistId = () =>
  `playlist:${Date.now().toString(36)}:${Math.random().toString(36).slice(2, 8)}`;

const getNativePresetFileId = (file) =>
  [file.name, file.size, file.lastModified].filter((part) => part !== undefined).join(':');

const isNativePresetFile = (file) => /\.(milk2?|txt)$/i.test(file.name);

const isNativeFragmentFile = (file) => /\.(shape|wave)$/i.test(file.name);

const getNativeImportFilePath = (file) =>
  file.webkitRelativePath || file.name;

const isNativeTextureAssetCandidateFile = (file) =>
  /^image\//i.test(file.type) || /\.(png|jpe?g|webp|gif)$/i.test(file.name);

const getNativeTextureAssetSkip = (file) => {
  if (isNativePresetFile(file) || isNativeFragmentFile(file)) return null;
  if (!isNativeTextureAssetCandidateFile(file)) {
    return {
      fileName: file.name,
      message: interfaceText("Unsupported file type."),
    };
  }
  if (file.size > nativeTextureAssetMaxBytes) {
    return {
      fileName: file.name,
      message: interfaceText("Texture asset is larger than 1 MB."),
    };
  }
  return null;
};

const getTextureAssetKeys = (fileName) => {
  const normalized = fileName.trim().replace(/^['"]|['"]$/g, '').replace(/\\/g, '/').toLowerCase();
  const basename = normalized.replace(/^.*[\\/]/, '');
  const stem = basename.replace(/\.[^.]+$/, '');
  return Array.from(new Set([normalized, basename, stem].filter(Boolean)));
};

const textureReferencePattern =
  /(?:shape|sprite)\d+_(?:texture|tex|tex_name|image|img|file|filename)\s*=\s*([^\r\n;]+)/gi;
const standaloneTextureReferencePattern =
  /^\s*(?:texture|tex|tex_name|image|img|file|filename)\s*=\s*([^\r\n;]+)/gim;

const collectNativePresetTextureReferences = (source) => {
  const references = new Set();
  let match = textureReferencePattern.exec(source || '');
  while (match) {
    getTextureAssetKeys(match[1]).forEach((key) => references.add(key));
    match = textureReferencePattern.exec(source || '');
  }
  match = standaloneTextureReferencePattern.exec(source || '');
  while (match) {
    getTextureAssetKeys(match[1]).forEach((key) => references.add(key));
    match = standaloneTextureReferencePattern.exec(source || '');
  }
  return references;
};

const selectNativePresetTextureAssets = (source, textureAssets) => {
  const references = collectNativePresetTextureReferences(source);
  if (references.size === 0) return {};
  const selected = {};
  Object.entries(textureAssets).forEach(([key, asset]) => {
    if (!references.has(key)) return;
    getTextureAssetKeys(asset.fileName).forEach((alias) => {
      selected[alias] = asset;
    });
  });
  return selected;
};

const readFileAsDataUrl = (file) => new Promise((resolve, reject) => {
  if (typeof FileReader !== 'function') {
    reject(new Error(interfaceText('Texture asset imports require FileReader support.')));
    return;
  }
  const reader = new FileReader();
  reader.onerror = () => reject(reader.error || new Error(interfaceText('Failed to read {fileName}.', { fileName: file.name })));
  reader.onload = () => resolve(reader.result);
  reader.readAsDataURL(file);
});

const readNativeTextureAssets = async (files) => {
  const textureAssets = {};
  const skippedTextureAssets = [];
  for (const file of files.filter((entry) =>
    !isNativePresetFile(entry) && !isNativeFragmentFile(entry))) {
    const skip = getNativeTextureAssetSkip(file);
    if (skip) {
      skippedTextureAssets.push(skip);
      continue;
    }
    let dataUrl = null;
    try {
      dataUrl = await readFileAsDataUrl(file);
    } catch (textureError) {
      skippedTextureAssets.push({
        fileName: file.name,
        message: textureError?.message || interfaceText('Texture asset could not be read.'),
      });
      continue;
    }
    const filePath = getNativeImportFilePath(file);
    getTextureAssetKeys(filePath).forEach((key) => {
      textureAssets[key] = {
        dataUrl,
        fileName: filePath,
      };
    });
  }
  return { skippedTextureAssets, textureAssets };
};

const downloadTextFile = (fileName, source) => {
  const blob = new Blob([source], { type: 'text/plain' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

const formatSkippedFileNames = (skipped) => {
  const skippedNames = skipped.slice(0, 3).map((entry) => entry.fileName).join(', ');
  return skipped.length > 3
    ? interfaceText('{fileNames}, +{count} more', {
      count: skipped.length - 3,
      fileNames: skippedNames,
    })
    : skippedNames;
};

const getNativePresetImportMessage = ({ importedCount, skipped, skippedTextureAssets }) => {
  const messages = [];
  if (skipped.length > 0) {
    const fileNames = formatSkippedFileNames(skipped);
    messages.push(importedCount > 0
      ? interfaceText('Imported {importedCount}; skipped {skippedCount}: {fileNames}.', {
        fileNames,
        importedCount,
        skippedCount: skipped.length,
      })
      : interfaceText('Native preset import failed for {count}: {fileNames}.', {
        count: skipped.length,
        fileNames,
      }));
  }
  if (skippedTextureAssets.length > 0) {
    const fileNames = formatSkippedFileNames(skippedTextureAssets);
    messages.push(skippedTextureAssets.length === 1
      ? interfaceText('Skipped {count} texture asset: {fileNames}.', {
        count: skippedTextureAssets.length,
        fileNames,
      })
      : interfaceText('Skipped {count} texture assets: {fileNames}.', {
        count: skippedTextureAssets.length,
        fileNames,
      }));
  }
  return messages.length > 0 ? messages.join(' ') : null;
};

const supportsWebGl2 = () => {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2'));
  } catch {
    return false;
  }
};

const Visualizer = ({
  audioElement,
  compactControls = false,
  engineOverride,
  mode,
  onEngineChange,
  onModeChange,
}) => {
  useInterfaceLanguage();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [allowReducedMotionAnimation, setAllowReducedMotionAnimation] = useState(false);
  const motionSuppressed = prefersReducedMotion && !allowReducedMotionAnimation;
  const rendererEnabled = mode !== 'off' && !motionSuppressed;
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const directoryInputRef = useRef(null);
  const engineRef = useRef(null);
  const fileInputRef = useRef(null);
  const lastNativeMouseRef = useRef({ x: 0.5, y: 0.5 });
  const lastNativeRenderAtRef = useRef(0);
  const rafRef = useRef(null);
  const playbackActiveRef = useRef(false);
  const engineAudioNodeRef = useRef(null);
  const nativeAutomationSettingsRef = useRef(readStoredNativeAutomationSettings());
  const [fallbackMode, setFallbackMode] = useState(false);
  const [engineType, setEngineType] = useState(readStoredEngine);
  const [engineName, setEngineName] = useState('');
  const [nativeAutomationSettings, setNativeAutomationSettings] = useState(
    () => nativeAutomationSettingsRef.current,
  );
  const [activeNativePresetId, setActiveNativePresetId] = useState(
    () => readStoredNativePreset()?.id || '',
  );
  const [nativeFavoritePresetIds, setNativeFavoritePresetIds] = useState(
    readStoredNativePresetFavorites,
  );
  const [nativeLibraryMode, setNativeLibraryMode] = useState(
    readStoredNativePresetLibraryMode,
  );
  const [nativePresetHistory, setNativePresetHistory] = useState([]);
  const [nativePresetLibrary, setNativePresetLibrary] = useState(readStoredNativePresetLibrary);
  const [nativeFpsCap, setNativeFpsCap] = useState(readStoredNativeFpsCap);
  const [nativeFrameMs, setNativeFrameMs] = useState(0);
  const [nativeQualityPreset, setNativeQualityPreset] = useState(readStoredNativeQuality);
  const [nativePresetSearch, setNativePresetSearch] = useState(readStoredNativePresetSearch);
  const [nativePresetPlaylists, setNativePresetPlaylists] = useState(
    readStoredNativePresetPlaylists,
  );
  const [nativeFragmentSummary, setNativeFragmentSummary] = useState({
    shapes: [],
    waves: [],
  });
  const [nativeParameterValues, setNativeParameterValues] = useState({});
  const [nativeParameterDrafts, setNativeParameterDrafts] = useState({});
  const [selectedNativeParameter, setSelectedNativeParameter] = useState(
    nativeEditableParameters[0].key,
  );
  const [showNativeDebug, setShowNativeDebug] = useState(false);
  const [nativeDebugSnapshot, setNativeDebugSnapshot] = useState(null);
  const [selectedNativeShapeIndex, setSelectedNativeShapeIndex] = useState(0);
  const [selectedNativeWaveIndex, setSelectedNativeWaveIndex] = useState(0);
  const [activeNativePlaylistId, setActiveNativePlaylistId] = useState(
    readStoredActiveNativePresetPlaylistId,
  );
  const [presetName, setPresetName] = useState('');
  const [error, setError] = useState(null);
  const activeEngineType = engineOverride || engineType;
  const renderEngineTypeRef = useRef(activeEngineType);
  const renderFpsCapRef = useRef(nativeFpsCap);
  const renderDebugEnabledRef = useRef(showNativeDebug);
  renderEngineTypeRef.current = activeEngineType;
  renderFpsCapRef.current = nativeFpsCap;
  renderDebugEnabledRef.current = showNativeDebug;

  const activeNativePlaylist = nativePresetPlaylists.find(
    (playlist) => playlist.id === activeNativePlaylistId,
  );
  const playlistScopedNativePresetLibrary = activeNativePlaylist
    ? activeNativePlaylist.presetIds
      .map((presetId) => nativePresetLibrary.find((preset) => preset.id === presetId))
      .filter(Boolean)
    : nativePresetLibrary;
  const modeFilteredNativePresetLibrary = nativeLibraryMode === 'favorites'
    ? playlistScopedNativePresetLibrary.filter(
      (preset) => nativeFavoritePresetIds.includes(preset.id),
    )
    : playlistScopedNativePresetLibrary;
  const visibleNativePresetLibrary = filterNativePresetLibrary(
    modeFilteredNativePresetLibrary,
    nativePresetSearch,
  );
  const visibleNativePresetIndex = visibleNativePresetLibrary.findIndex(
    (preset) => preset.id === activeNativePresetId,
  );
  const activeNativePresetIsFavorite = nativeFavoritePresetIds.includes(activeNativePresetId);
  const selectedNativePresetValue = visibleNativePresetLibrary.some(
    (preset) => preset.id === activeNativePresetId,
  )
    ? activeNativePresetId
    : '';
  const hasNativePresetSearch = nativePresetSearch.trim().length > 0;
  const nativeBankNavigationDisabled = isNativeEngine(activeEngineType)
    && nativePresetLibrary.length > 0
    && visibleNativePresetLibrary.length === 0;
  const canSaveNativePlaylist = visibleNativePresetLibrary.length > 0;
  const hasNativeShapes = nativeFragmentSummary.shapes.length > 0;
  const hasNativeWaves = nativeFragmentSummary.waves.length > 0;
  const nativeAutomationMode = nativeAutomationSettings.mode;
  const nativeParameter = getNativeEditableParameter(selectedNativeParameter);
  const nativeParameterValue = Number(
    nativeParameterDrafts[selectedNativeParameter]
    ?? nativeParameterValues[selectedNativeParameter]
    ?? nativeParameter.defaultValue,
  );

  useEffect(() => {
    if (mode === 'off') setAllowReducedMotionAnimation(false);
  }, [mode]);

  const refreshNativeFragmentSummary = useCallback(() => {
    const summary = engineRef.current?.getPresetFragmentSummary?.() || {
      shapes: [],
      waves: [],
    };
    setNativeFragmentSummary(summary);
    setSelectedNativeShapeIndex((index) =>
      Math.min(index, Math.max(0, summary.shapes.length - 1)));
    setSelectedNativeWaveIndex((index) =>
      Math.min(index, Math.max(0, summary.waves.length - 1)));
    setNativeParameterValues(engineRef.current?.getPresetParameterSummary?.() || {});
    setNativeParameterDrafts({});
    setNativeDebugSnapshot(engineRef.current?.getPresetDebugSnapshot?.() || null);
  }, []);

  const renderLoop = useCallback((timestamp = performance.now()) => {
    rafRef.current = null;
    if (document.hidden || !playbackActiveRef.current) return;
    if (!engineRef.current) return;
    const engineType = renderEngineTypeRef.current;
    const fpsCap = renderFpsCapRef.current;
    const debugEnabled = renderDebugEnabledRef.current;
    try {
      const fpsCapMs = isNativeEngine(engineType) ? getNativeFpsCapMs(fpsCap) : 0;
      if (
        fpsCapMs > 0
        && lastNativeRenderAtRef.current
        && timestamp - lastNativeRenderAtRef.current < fpsCapMs
      ) {
        rafRef.current = window.requestAnimationFrame(renderLoop);
        return;
      }
      const startedAt = performance.now();
      const renderResult = engineRef.current.render();
      if (isNativeEngine(engineType)) {
        lastNativeRenderAtRef.current = timestamp;
        if (debugEnabled) {
          setNativeFrameMs(Number((performance.now() - startedAt).toFixed(1)));
        }
      }
      if (renderResult?.presetName) {
        setPresetName(renderResult.presetName);
      }
    } catch (renderError) {
      // eslint-disable-next-line no-console
      console.error('Failed to render MilkDrop visualizer', renderError);
      if (isNativeEngine(engineType)) {
        removeLocalStorageItem(nativePresetStorageKey);
      }
      setError(getVisualizerErrorMessage(engineType, renderError));
      return;
    }
    rafRef.current = window.requestAnimationFrame(renderLoop);
  }, []);

  const stopRendering = useCallback(() => {
    if (rafRef.current !== null) window.cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }, []);

  const startRendering = useCallback(() => {
    if (
      document.hidden || !playbackActiveRef.current || !engineRef.current || rafRef.current !== null
    ) return;
    rafRef.current = window.requestAnimationFrame(renderLoop);
  }, [renderLoop]);

  useEffect(() => {
    if (!rendererEnabled || !audioElement) return undefined;
    playbackActiveRef.current = !audioElement.paused && !audioElement.ended &&
      audioElement.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA;
    const handlePlaying = () => {
      playbackActiveRef.current = true;
      startRendering();
    };
    const handleStopped = () => {
      playbackActiveRef.current = false;
      stopRendering();
    };
    const handleVisibilityChange = () => {
      if (document.hidden) stopRendering();
      else startRendering();
    };
    audioElement.addEventListener('playing', handlePlaying);
    audioElement.addEventListener('pause', handleStopped);
    audioElement.addEventListener('waiting', handleStopped);
    audioElement.addEventListener('stalled', handleStopped);
    audioElement.addEventListener('ended', handleStopped);
    audioElement.addEventListener('error', handleStopped);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      audioElement.removeEventListener('playing', handlePlaying);
      audioElement.removeEventListener('pause', handleStopped);
      audioElement.removeEventListener('waiting', handleStopped);
      audioElement.removeEventListener('stalled', handleStopped);
      audioElement.removeEventListener('ended', handleStopped);
      audioElement.removeEventListener('error', handleStopped);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      playbackActiveRef.current = false;
      stopRendering();
    };
  }, [audioElement, rendererEnabled, startRendering, stopRendering]);

  const cycleNativeAutomationMode = useCallback(() => {
    setNativeAutomationSettings((current) =>
      normalizeNativeAutomationSettings({
        ...current,
        mode: getNextNativeAutomationMode(current.mode),
      }));
  }, []);

  const updateNativeAutomationBeats = useCallback((event) => {
    setNativeAutomationSettings((current) =>
      normalizeNativeAutomationSettings({
        ...current,
        beatsPerPreset: Number(event.target.value),
      }));
  }, []);

  const updateNativeAutomationInterval = useCallback((event) => {
    setNativeAutomationSettings((current) =>
      normalizeNativeAutomationSettings({
        ...current,
        timedIntervalSeconds: Number(event.target.value),
      }));
  }, []);

  const updateNativeFpsCap = useCallback((event) => {
    const fpsCap = event.target.value;
    setNativeFpsCap(fpsCap);
    setNativeQualityPreset('custom');
    setLocalStorageItem(nativePresetQualityStorageKey, 'custom');
    if (fpsCap === 'full') {
      removeLocalStorageItem(nativePresetFpsCapStorageKey);
    } else {
      setLocalStorageItem(nativePresetFpsCapStorageKey, fpsCap);
    }
    lastNativeRenderAtRef.current = 0;
  }, []);

  const updateNativeQualityPreset = useCallback((event) => {
    const quality = event.target.value;
    const preset = nativeQualityPresets[quality];
    if (!preset) return;
    setNativeQualityPreset(quality);
    setLocalStorageItem(nativePresetQualityStorageKey, quality);
    setNativeFpsCap(preset.fpsCap);
    if (preset.fpsCap === 'full') {
      removeLocalStorageItem(nativePresetFpsCapStorageKey);
    } else {
      setLocalStorageItem(nativePresetFpsCapStorageKey, preset.fpsCap);
    }
    lastNativeRenderAtRef.current = 0;
  }, []);

  const selectNativeParameter = useCallback((event) => {
    setSelectedNativeParameter(event.target.value);
  }, []);

  const updateNativeParameterDraft = useCallback((event) => {
    const value = Number(event.target.value);
    setNativeParameterDrafts((drafts) => ({
      ...drafts,
      [selectedNativeParameter]: value,
    }));
  }, [selectedNativeParameter]);

  const sizeCanvas = useCallback(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    const engine = engineRef.current;
    if (!container || !canvas || !engine) return;
    const rect = container.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    canvas.width = width;
    canvas.height = height;
    engine.resize(width, height);
  }, []);

  const loadNativePresetEntry = useCallback(async (preset, options = {}) => {
    if (!preset || !engineRef.current?.loadPresetText) return false;
    const { pushHistory = true } = options;

    try {
      setError(null);
      let loadedPresetName = engineRef.current.loadPresetText(
        preset.source,
        preset.fileName,
        { textureAssets: preset.textureAssets },
      );
      if (isPromiseLike(loadedPresetName)) {
        loadedPresetName = await loadedPresetName;
      }
      setLocalStorageItem(nativePresetStorageKey, JSON.stringify(preset));
      if (pushHistory && activeNativePresetId && activeNativePresetId !== preset.id) {
        setNativePresetHistory((history) => [
          activeNativePresetId,
          ...history.filter((id) => id !== activeNativePresetId && id !== preset.id),
        ].slice(0, nativePresetHistoryLimit));
      }
      setActiveNativePresetId(preset.id);
      setPresetName(loadedPresetName);
      refreshNativeFragmentSummary();
      sizeCanvas();
      return true;
    } catch (presetError) {
      // eslint-disable-next-line no-console
      console.error('Failed to load native MilkDrop preset from library', presetError);
      setError(presetError?.message || interfaceText('Native preset load failed.'));
      return false;
    }
  }, [activeNativePresetId, refreshNativeFragmentSummary, sizeCanvas]);

  const loadNativePresetByOffset = useCallback((offset) => {
    if (visibleNativePresetLibrary.length === 0) return false;
    const currentIndex = visibleNativePresetIndex >= 0
      ? visibleNativePresetIndex
      : (offset > 0 ? -1 : 0);
    const nextIndex = (
      currentIndex + offset + visibleNativePresetLibrary.length
    ) % visibleNativePresetLibrary.length;
    return loadNativePresetEntry(visibleNativePresetLibrary[nextIndex]);
  }, [loadNativePresetEntry, visibleNativePresetIndex, visibleNativePresetLibrary]);

  const cyclePreset = useCallback(async () => {
    if (isNativeEngine(activeEngineType) && nativePresetLibrary.length > 0) {
      await loadNativePresetByOffset(1);
      return;
    }
    if (!engineRef.current) return;
    let nextPresetName = engineRef.current.nextPreset();
    if (isPromiseLike(nextPresetName)) {
      nextPresetName = await nextPresetName;
    }
    if (nextPresetName) {
      setPresetName(nextPresetName);
    }
  }, [activeEngineType, loadNativePresetByOffset, nativePresetLibrary.length]);

  const cycleEngineType = useCallback(() => {
    const nextEngine = getNextEngine(activeEngineType);
    if (onEngineChange) {
      onEngineChange(nextEngine);
      return;
    }
    setEngineType(nextEngine);
  }, [activeEngineType, onEngineChange]);

  const previousNativeLibraryPreset = useCallback(async () => {
    if (nativePresetHistory.length > 0) {
      const [previousId, ...remainingHistory] = nativePresetHistory;
      const previousPreset = nativePresetLibrary.find((preset) => preset.id === previousId);
      setNativePresetHistory(remainingHistory);
      await loadNativePresetEntry(previousPreset, { pushHistory: false });
      return;
    }
    await loadNativePresetByOffset(-1);
  }, [
    loadNativePresetByOffset,
    loadNativePresetEntry,
    nativePresetHistory,
    nativePresetLibrary,
  ]);

  const randomNativeLibraryPreset = useCallback(async () => {
    if (visibleNativePresetLibrary.length === 0) return;
    const candidates = visibleNativePresetLibrary.filter(
      (preset) => preset.id !== activeNativePresetId,
    );
    const pool = candidates.length > 0 ? candidates : visibleNativePresetLibrary;
    const randomIndex = Math.floor(Math.random() * pool.length);
    await loadNativePresetEntry(pool[randomIndex]);
  }, [activeNativePresetId, loadNativePresetEntry, visibleNativePresetLibrary]);

  const toggleNativePresetFavorite = useCallback(() => {
    if (!activeNativePresetId) return;
    setNativeFavoritePresetIds((favoriteIds) => {
      const nextFavoriteIds = favoriteIds.includes(activeNativePresetId)
        ? favoriteIds.filter((id) => id !== activeNativePresetId)
        : [activeNativePresetId, ...favoriteIds];
      writeStoredNativePresetFavorites(nextFavoriteIds);
      return nextFavoriteIds;
    });
  }, [activeNativePresetId]);

  const toggleNativeLibraryMode = useCallback(() => {
    setNativeLibraryMode((current) => {
      const nextMode = current === 'favorites' ? 'all' : 'favorites';
      setLocalStorageItem(nativePresetLibraryModeStorageKey, nextMode);
      return nextMode;
    });
  }, []);

  const updateNativePresetSearch = useCallback((event) => {
    const nextSearch = event.target.value;
    setNativePresetSearch(nextSearch);
    if (nextSearch.trim()) {
      setLocalStorageItem(nativePresetSearchStorageKey, nextSearch);
    } else {
      removeLocalStorageItem(nativePresetSearchStorageKey);
    }
  }, []);

  const clearNativePresetSearch = useCallback(() => {
    setNativePresetSearch('');
    removeLocalStorageItem(nativePresetSearchStorageKey);
  }, []);

  const saveNativePlaylistFromVisibleBank = useCallback(() => {
    if (visibleNativePresetLibrary.length === 0) return;
    const defaultName = getNativePresetPlaylistName({
      mode: nativeLibraryMode,
      search: nativePresetSearch,
    });
    const nextName = window.prompt?.('Name this native MilkDrop playlist', defaultName);
    if (!nextName || !nextName.trim()) return;
    const playlist = {
      createdAt: new Date().toISOString(),
      id: getNativePresetPlaylistId(),
      name: nextName.trim(),
      presetIds: visibleNativePresetLibrary.map((preset) => preset.id),
    };
    setNativePresetPlaylists((playlists) => {
      const nextPlaylists = [
        playlist,
        ...playlists.filter((entry) => entry.name !== playlist.name),
      ].slice(0, nativePresetPlaylistLimit);
      writeStoredNativePresetPlaylists(nextPlaylists);
      return nextPlaylists;
    });
    setActiveNativePlaylistId(playlist.id);
    setLocalStorageItem(activeNativePresetPlaylistStorageKey, playlist.id);
  }, [nativeLibraryMode, nativePresetSearch, visibleNativePresetLibrary]);

  const selectNativePlaylist = useCallback((event) => {
    const playlistId = event.target.value;
    setActiveNativePlaylistId(playlistId);
    if (playlistId) {
      setLocalStorageItem(activeNativePresetPlaylistStorageKey, playlistId);
    } else {
      removeLocalStorageItem(activeNativePresetPlaylistStorageKey);
    }
  }, []);

  const clearActiveNativePlaylist = useCallback(() => {
    setActiveNativePlaylistId('');
    removeLocalStorageItem(activeNativePresetPlaylistStorageKey);
  }, []);

  const renameActiveNativePlaylist = useCallback(() => {
    const activePlaylist = nativePresetPlaylists.find(
      (playlist) => playlist.id === activeNativePlaylistId,
    );
    if (!activePlaylist) return;
    const nextName = window.prompt?.('Rename native MilkDrop playlist', activePlaylist.name);
    if (!nextName || !nextName.trim()) return;
    setNativePresetPlaylists((playlists) => {
      const nextPlaylists = playlists.map((playlist) =>
        (playlist.id === activePlaylist.id
          ? { ...playlist, name: nextName.trim(), updatedAt: new Date().toISOString() }
          : playlist));
      writeStoredNativePresetPlaylists(nextPlaylists);
      return nextPlaylists;
    });
  }, [activeNativePlaylistId, nativePresetPlaylists]);

  const removeActiveNativePlaylist = useCallback(() => {
    if (!activeNativePlaylistId) return;
    setNativePresetPlaylists((playlists) => {
      const nextPlaylists = playlists.filter((playlist) => playlist.id !== activeNativePlaylistId);
      writeStoredNativePresetPlaylists(nextPlaylists);
      return nextPlaylists;
    });
    setActiveNativePlaylistId('');
    removeLocalStorageItem(activeNativePresetPlaylistStorageKey);
  }, [activeNativePlaylistId]);

  useEffect(() => {
    if (!rendererEnabled || !audioElement || !canvasRef.current) return undefined;

    let cancelled = false;
    let resizeObserver = null;
    let createdEngine = null;

    (async () => {
      try {
        setError(null);
        setFallbackMode(false);
        let graph;
        if (audioElement.paused) {
          graph = getOrCreateAudioGraph(audioElement);
          await suspendAudioGraph(audioElement);
        } else {
          graph = await resumeAudioGraph(audioElement);
        }
        if (!graph) {
          setError(interfaceText("Web Audio is not available in this browser."));
          setFallbackMode(true);
          return;
        }

        if (activeEngineType === 'native-webgl2' && !supportsWebGl2()) {
          setError(interfaceText("Native MilkDrop WebGL2 needs WebGL2. Showing analyzer fallback."));
          setFallbackMode(true);
          return;
        }

        const createEngine = isNativeEngine(activeEngineType)
          ? createNativeMilkdropEngine
          : createButterchurnEngine;
        const engine = await createEngine({
          audioContext: graph.ctx,
          audioNode: graph.visualizerInput,
          canvas: canvasRef.current,
          pixelRatio: window.devicePixelRatio || 1,
          rendererBackend: getNativeRendererBackend(activeEngineType),
        });
        createdEngine = engine;
        if (cancelled) {
          engine.dispose();
          return;
        }

        engineRef.current = engine;
        engineAudioNodeRef.current = graph.visualizerInput;
        setEngineName(engine.name);
        setPresetName(engine.presetName);
        if (isNativeEngine(activeEngineType) && engine.setPresetAutomation) {
          engine.setPresetAutomation(nativeAutomationSettingsRef.current);
        }
        if (isNativeEngine(activeEngineType)) {
          refreshNativeFragmentSummary();
        }
        const storedNativePreset = isNativeEngine(activeEngineType) ? readStoredNativePreset() : null;
        if (storedNativePreset?.source && engine.loadPresetText) {
          let importedPresetName = engine.loadPresetText(
            storedNativePreset.source,
            storedNativePreset.fileName,
            { textureAssets: storedNativePreset.textureAssets },
          );
          if (isPromiseLike(importedPresetName)) {
            importedPresetName = await importedPresetName;
          }
          setActiveNativePresetId(storedNativePreset.id || '');
          setPresetName(importedPresetName);
          refreshNativeFragmentSummary();
        }
        sizeCanvas();

        if (typeof window.ResizeObserver === 'function' && containerRef.current) {
          resizeObserver = new window.ResizeObserver(() => sizeCanvas());
          resizeObserver.observe(containerRef.current);
        }

        startRendering();
      } catch (importError) {
        if (createdEngine) {
          try {
            createdEngine.dispose();
          } catch {
            // The renderer may have failed while the browser was tearing down its context.
          }
        }
        if (engineRef.current === createdEngine) {
          engineRef.current = null;
          engineAudioNodeRef.current = null;
        }
        // eslint-disable-next-line no-console
        console.error('Failed to load Milkdrop visualizer', importError);
        setError(getVisualizerErrorMessage(activeEngineType, importError));
        setFallbackMode(true);
      }
    })();

    return () => {
      cancelled = true;
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (engineRef.current && engineAudioNodeRef.current) {
        try {
          engineRef.current.dispose();
        } catch {
          // The engine may already have disconnected during canvas teardown.
        }
      }
      engineRef.current = null;
      engineAudioNodeRef.current = null;
      setEngineName('');
    };
  }, [rendererEnabled, audioElement, activeEngineType, refreshNativeFragmentSummary, renderLoop, sizeCanvas, startRendering]);

  useEffect(() => {
    if (engineOverride) return;
    setLocalStorageItem(visualizerEngineStorageKey, engineType);
  }, [engineOverride, engineType]);

  useEffect(() => {
    nativeAutomationSettingsRef.current = nativeAutomationSettings;
    writeStoredNativeAutomationSettings(nativeAutomationSettings);
    if (isNativeEngine(activeEngineType) && engineRef.current?.setPresetAutomation) {
      engineRef.current.setPresetAutomation(nativeAutomationSettings);
    }
  }, [activeEngineType, nativeAutomationSettings]);

  useEffect(() => {
    setNativeFavoritePresetIds((favoriteIds) => {
      const nextFavoriteIds = pruneNativePresetFavorites(favoriteIds, nativePresetLibrary);
      if (nextFavoriteIds.length !== favoriteIds.length) {
        writeStoredNativePresetFavorites(nextFavoriteIds);
        if (nextFavoriteIds.length === 0 && nativeLibraryMode === 'favorites') {
          setNativeLibraryMode('all');
          setLocalStorageItem(nativePresetLibraryModeStorageKey, 'all');
        }
        return nextFavoriteIds;
      }
      return favoriteIds;
    });
    setNativePresetHistory((history) => {
      const libraryIds = new Set(nativePresetLibrary.map((preset) => preset.id));
      return history.filter((id) => libraryIds.has(id));
    });
    setNativePresetPlaylists((playlists) => {
      const nextPlaylists = pruneNativePresetPlaylists(playlists, nativePresetLibrary);
      if (
        nextPlaylists.length !== playlists.length
        || nextPlaylists.some((playlist, index) =>
          playlist.presetIds.length !== playlists[index].presetIds.length)
      ) {
        writeStoredNativePresetPlaylists(nextPlaylists);
        if (
          activeNativePlaylistId
          && !nextPlaylists.some((playlist) => playlist.id === activeNativePlaylistId)
        ) {
          setActiveNativePlaylistId('');
          removeLocalStorageItem(activeNativePresetPlaylistStorageKey);
        }
        return nextPlaylists;
      }
      return playlists;
    });
  }, [activeNativePlaylistId, nativeLibraryMode, nativePresetLibrary]);

  useEffect(() => {
    sizeCanvas();
  }, [mode, sizeCanvas]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      const fsElement = document.fullscreenElement;
      if (mode === 'fullscreen' && !fsElement) {
        onModeChange('inline');
      }
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () =>
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, [mode, onModeChange]);

  const enterFullscreen = useCallback(async () => {
    const target = containerRef.current;
    if (!target || !target.requestFullscreen) {
      onModeChange('fullwindow');
      return;
    }
    try {
      await target.requestFullscreen();
      onModeChange('fullscreen');
    } catch {
      onModeChange('fullwindow');
    }
  }, [onModeChange]);

  const exitFullscreen = useCallback(async () => {
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch {
        // ignore; fullscreenchange handler will reset mode
      }
    }
    onModeChange('inline');
  }, [onModeChange]);

  const importNativePreset = useCallback(async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (files.length === 0 || !engineRef.current?.loadPresetText) return;

    setError(null);
    const imported = [];
    let activePresetEntry = null;
    let importedFragmentCount = 0;
    const skipped = [];
    const { skippedTextureAssets, textureAssets } = await readNativeTextureAssets(files);

    for (const file of files.filter(isNativePresetFile)) {
      try {
        const source = await file.text();
        const presetTextureAssets = selectNativePresetTextureAssets(source, textureAssets);
        const importedPresetName = engineRef.current.inspectPresetText
          ? engineRef.current.inspectPresetText(source, file.name).title
          : engineRef.current.loadPresetText(source, file.name);
        imported.push({
          fileName: file.name,
          id: getNativePresetFileId(file),
          source,
          textureAssets: presetTextureAssets,
          title: importedPresetName,
        });
      } catch (presetError) {
        // eslint-disable-next-line no-console
        console.error('Failed to import native MilkDrop preset', presetError);
        skipped.push({
          fileName: file.name,
          message: presetError?.message || interfaceText('Unsupported syntax or shader features may be present.'),
        });
      }
    }

    if (imported.length > 0) {
      const activePreset = imported[imported.length - 1];
      let activePresetName = engineRef.current.loadPresetText(
        activePreset.source,
        activePreset.fileName,
        { textureAssets: activePreset.textureAssets },
      );
      if (isPromiseLike(activePresetName)) {
        activePresetName = await activePresetName;
      }
      activePreset.title = activePresetName;
      activePresetEntry = activePreset;
      setLocalStorageItem(nativePresetStorageKey, JSON.stringify(activePreset));
      setActiveNativePresetId(activePreset.id);
      refreshNativeFragmentSummary();
      setNativePresetLibrary((library) => {
        const nextLibrary = imported.reduce(
          (next, entry) => upsertNativePresetLibraryEntry(next, entry),
          library,
        );
        writeStoredNativePresetLibrary(nextLibrary);
        return nextLibrary;
      });
      setPresetName(activePresetName);
      sizeCanvas();
    }

    for (const file of files.filter(isNativeFragmentFile)) {
      if (!engineRef.current?.loadPresetFragmentText) {
        skipped.push({
          fileName: file.name,
          message: interfaceText("Native fragment import is not available."),
        });
        continue;
      }
      try {
        const source = await file.text();
        const fragmentTextureAssets = selectNativePresetTextureAssets(source, textureAssets);
        const mergedTextureAssets = {
          ...(activePresetEntry?.textureAssets || {}),
          ...fragmentTextureAssets,
        };
        let result = engineRef.current.loadPresetFragmentText(source, file.name, {
          textureAssets: mergedTextureAssets,
        });
        if (isPromiseLike(result)) {
          result = await result;
        }
        const existingPreset = activePresetEntry || readStoredNativePreset();
        const mergedPreset = {
          fileName: existingPreset?.fileName || file.name,
          id: existingPreset?.id || `fragment:${getNativePresetFileId(file)}`,
          source: result.source,
          textureAssets: {
            ...(existingPreset?.textureAssets || {}),
            ...fragmentTextureAssets,
          },
          title: result.title,
        };
        activePresetEntry = mergedPreset;
        importedFragmentCount += 1;
        setLocalStorageItem(nativePresetStorageKey, JSON.stringify(mergedPreset));
        setActiveNativePresetId(mergedPreset.id);
        refreshNativeFragmentSummary();
        setNativePresetLibrary((library) => {
          const nextLibrary = upsertNativePresetLibraryEntry(library, mergedPreset);
          writeStoredNativePresetLibrary(nextLibrary);
          return nextLibrary;
        });
        setPresetName(result.title);
        sizeCanvas();
      } catch (presetError) {
        // eslint-disable-next-line no-console
        console.error('Failed to import native MilkDrop fragment', presetError);
        skipped.push({
          fileName: file.name,
          message: presetError?.message || interfaceText('Unsupported fragment syntax may be present.'),
        });
      }
    }

    const importMessage = getNativePresetImportMessage({
      importedCount: imported.length + importedFragmentCount,
      skipped,
      skippedTextureAssets,
    });
    if (importMessage) {
      setError(importMessage);
    }
  }, [refreshNativeFragmentSummary, sizeCanvas]);

  const exportNativeFragment = useCallback((type) => {
    if (!engineRef.current?.exportPresetFragment) return;
    try {
      const selectedIndex = type === 'wave' ? selectedNativeWaveIndex : selectedNativeShapeIndex;
      const exported = engineRef.current.exportPresetFragment(type, selectedIndex);
      if (!exported) {
        setError(interfaceText("No {type} fragment is available in the active native preset.", { "type": (type) }));
        return;
      }
      downloadTextFile(exported.fileName, exported.source);
      setError(null);
    } catch (exportError) {
      // eslint-disable-next-line no-console
      console.error('Failed to export native MilkDrop fragment', exportError);
      setError(exportError?.message || interfaceText('Native fragment export failed.'));
    }
  }, [selectedNativeShapeIndex, selectedNativeWaveIndex]);

  const exportNativePreset = useCallback(() => {
    if (!engineRef.current?.exportPresetText) return;
    try {
      const exported = engineRef.current.exportPresetText();
      if (!exported) {
        setError(interfaceText("No native preset is available to export."));
        return;
      }
      downloadTextFile(exported.fileName, exported.source);
      setError(null);
    } catch (exportError) {
      // eslint-disable-next-line no-console
      console.error('Failed to export native MilkDrop preset', exportError);
      setError(exportError?.message || interfaceText('Native preset export failed.'));
    }
  }, []);

  const removeNativeFragment = useCallback(async (type) => {
    if (!engineRef.current?.removePresetFragment) return;
    const selectedIndex = type === 'wave' ? selectedNativeWaveIndex : selectedNativeShapeIndex;
    try {
      const storedPreset = readStoredNativePreset();
      let result = engineRef.current.removePresetFragment(type, selectedIndex, {
        textureAssets: storedPreset?.textureAssets,
      });
      if (isPromiseLike(result)) {
        result = await result;
      }
      if (!result) {
        setError(interfaceText("No {type} fragment is available in the active native preset.", { "type": (type) }));
        return;
      }
      const editedPreset = {
        fileName: storedPreset?.fileName || 'edited-native.milk',
        id: storedPreset?.id || `edited:${Date.now().toString(36)}`,
        source: result.source,
        textureAssets: storedPreset?.textureAssets || {},
        title: result.title,
      };
      setLocalStorageItem(nativePresetStorageKey, JSON.stringify(editedPreset));
      setActiveNativePresetId(editedPreset.id);
      setNativePresetLibrary((library) => {
        const nextLibrary = upsertNativePresetLibraryEntry(library, editedPreset);
        writeStoredNativePresetLibrary(nextLibrary);
        return nextLibrary;
      });
      setPresetName(result.title);
      refreshNativeFragmentSummary();
      setError(null);
      sizeCanvas();
    } catch (removeError) {
      // eslint-disable-next-line no-console
      console.error('Failed to remove native MilkDrop fragment', removeError);
      setError(removeError?.message || interfaceText('Native fragment removal failed.'));
    }
  }, [
    refreshNativeFragmentSummary,
    selectedNativeShapeIndex,
    selectedNativeWaveIndex,
    sizeCanvas,
  ]);

  const applyNativeParameterEdit = useCallback(async () => {
    if (!engineRef.current?.updatePresetBaseValue) return;
    try {
      const storedPreset = readStoredNativePreset();
      let result = engineRef.current.updatePresetBaseValue(
        selectedNativeParameter,
        nativeParameterValue,
        {
          textureAssets: storedPreset?.textureAssets,
        },
      );
      if (isPromiseLike(result)) {
        result = await result;
      }
      if (!result) {
        setError(interfaceText("Native parameter editing is not available for this value."));
        return;
      }
      const editedPreset = {
        fileName: storedPreset?.fileName || 'edited-native.milk',
        id: storedPreset?.id || `edited:${Date.now().toString(36)}`,
        source: result.source,
        textureAssets: storedPreset?.textureAssets || {},
        title: result.title,
      };
      setLocalStorageItem(nativePresetStorageKey, JSON.stringify(editedPreset));
      setActiveNativePresetId(editedPreset.id);
      setNativePresetLibrary((library) => {
        const nextLibrary = upsertNativePresetLibraryEntry(library, editedPreset);
        writeStoredNativePresetLibrary(nextLibrary);
        return nextLibrary;
      });
      setPresetName(result.title);
      setNativeParameterValues(result.values || {});
      setNativeParameterDrafts({});
      setError(null);
      sizeCanvas();
    } catch (editError) {
      // eslint-disable-next-line no-console
      console.error('Failed to edit native MilkDrop parameter', editError);
      setError(editError?.message || interfaceText('Native parameter edit failed.'));
    }
  }, [nativeParameterValue, selectedNativeParameter, sizeCanvas]);

  const randomizeNativePresetParameters = useCallback(async () => {
    if (!engineRef.current?.randomizePresetParameters) return;
    try {
      const storedPreset = readStoredNativePreset();
      let result = engineRef.current.randomizePresetParameters({
        textureAssets: storedPreset?.textureAssets,
      });
      if (isPromiseLike(result)) {
        result = await result;
      }
      if (!result) {
        setError(interfaceText("Native parameter randomization is not available for this preset."));
        return;
      }
      const editedPreset = {
        fileName: storedPreset?.fileName || 'randomized-native.milk',
        id: storedPreset?.id || `randomized:${Date.now().toString(36)}`,
        source: result.source,
        textureAssets: storedPreset?.textureAssets || {},
        title: result.title,
      };
      setLocalStorageItem(nativePresetStorageKey, JSON.stringify(editedPreset));
      setActiveNativePresetId(editedPreset.id);
      setNativePresetLibrary((library) => {
        const nextLibrary = upsertNativePresetLibraryEntry(library, editedPreset);
        writeStoredNativePresetLibrary(nextLibrary);
        return nextLibrary;
      });
      setPresetName(result.title);
      setNativeParameterValues(result.values || {});
      setNativeParameterDrafts({});
      refreshNativeFragmentSummary();
      setError(null);
      sizeCanvas();
    } catch (randomizeError) {
      // eslint-disable-next-line no-console
      console.error('Failed to randomize native MilkDrop preset', randomizeError);
      setError(randomizeError?.message || interfaceText('Native parameter randomization failed.'));
    }
  }, [refreshNativeFragmentSummary, sizeCanvas]);

  const loadNativeLibraryPreset = useCallback((event) => {
    const preset = nativePresetLibrary.find((entry) => entry.id === event.target.value);
    void loadNativePresetEntry(preset);
  }, [loadNativePresetEntry, nativePresetLibrary]);

  const clearNativePresetLibrary = useCallback(() => {
    removeLocalStorageItem(nativePresetStorageKey);
    removeLocalStorageItem(nativePresetLibraryStorageKey);
    removeLocalStorageItem(nativePresetFavoritesStorageKey);
    removeLocalStorageItem(nativePresetLibraryModeStorageKey);
    removeLocalStorageItem(nativePresetSearchStorageKey);
    removeLocalStorageItem(nativePresetPlaylistsStorageKey);
    removeLocalStorageItem(activeNativePresetPlaylistStorageKey);
    setActiveNativePresetId('');
    setNativeFavoritePresetIds([]);
    setNativeFragmentSummary({ shapes: [], waves: [] });
    setNativeDebugSnapshot(null);
    setNativeParameterDrafts({});
    setNativeParameterValues({});
    setNativeLibraryMode('all');
    setNativePresetHistory([]);
    setNativePresetLibrary([]);
    setNativePresetSearch('');
    setNativePresetPlaylists([]);
    setActiveNativePlaylistId('');
    setError(null);
  }, []);

  const removeActiveNativePreset = useCallback(() => {
    if (!activeNativePresetId) return;
    setNativePresetLibrary((library) => {
      const nextLibrary = library.filter((preset) => preset.id !== activeNativePresetId);
      if (nextLibrary.length > 0) {
        writeStoredNativePresetLibrary(nextLibrary);
      } else {
        removeLocalStorageItem(nativePresetLibraryStorageKey);
      }
      const nextFavoriteIds = pruneNativePresetFavorites(nativeFavoritePresetIds, nextLibrary);
      setNativeFavoritePresetIds(nextFavoriteIds);
      writeStoredNativePresetFavorites(nextFavoriteIds);
      return nextLibrary;
    });
    setNativePresetHistory((history) => history.filter((id) => id !== activeNativePresetId));
    const storedNativePreset = readStoredNativePreset();
    if (storedNativePreset?.id === activeNativePresetId) {
      removeLocalStorageItem(nativePresetStorageKey);
    }
    setActiveNativePresetId('');
    setError(null);
  }, [activeNativePresetId, nativeFavoritePresetIds]);

  const updateNativeMouseState = useCallback((event) => {
    if (!isNativeEngine(activeEngineType) || !engineRef.current?.setMouseState) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect?.width || !rect?.height) return;
    const mouseX = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const mouseY = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    const previous = lastNativeMouseRef.current;
    lastNativeMouseRef.current = { x: mouseX, y: mouseY };
    engineRef.current.setMouseState({
      mouse_down: event.buttons > 0 ? 1 : 0,
      mouse_dx: mouseX - previous.x,
      mouse_dy: mouseY - previous.y,
      mouse_x: mouseX,
      mouse_y: mouseY,
    });
  }, [activeEngineType]);

  const clearNativeMouseState = useCallback(() => {
    if (!isNativeEngine(activeEngineType) || !engineRef.current?.setMouseState) return;
    engineRef.current.setMouseState({
      mouse_down: 0,
      mouse_dx: 0,
      mouse_dy: 0,
    });
  }, [activeEngineType]);

  if (mode === 'off') return null;

  const className = [
    'player-visualizer',
    `player-visualizer-${mode}`,
    compactControls ? 'player-visualizer-compact' : '',
  ].filter(Boolean).join(' ');
  const displayedError = compactControls && error
    ? error.split('.')[0]
    : error;

  return (
    <div
      className={className}
      data-testid="player-visualizer"
      onPointerDown={updateNativeMouseState}
      onPointerLeave={clearNativeMouseState}
      onPointerMove={updateNativeMouseState}
      onPointerUp={clearNativeMouseState}
      ref={containerRef}
    >
      <canvas
        className="player-visualizer-canvas"
        hidden={fallbackMode}
        key={activeEngineType}
        ref={canvasRef}
      />
      {fallbackMode ? (
        <SpectrumAnalyzer
          allowReducedMotionAnimation={allowReducedMotionAnimation}
          audioElement={audioElement}
          className="player-visualizer-fallback"
          mode="spectrum"
        />
      ) : null}
      {displayedError ? <div className="player-visualizer-error">{displayedError}</div> : null}
      <div className="player-visualizer-overlay">
        {motionSuppressed ? (
          <div className="player-visualizer-motion-status" data-testid="visualizer-motion-status">
            <span role="status"><LocalizedText source={"Animation is paused because reduced motion is enabled."} /></span>
            <Popup
              content={interfaceText("Run the visualizer until it is hidden, even though reduced motion is enabled.")}
              trigger={
                <Button
                  aria-label={interfaceText("Animate anyway")}
                  data-testid="visualizer-motion-override"
                  onClick={() => setAllowReducedMotionAnimation(true)}
                  size="mini"
                  type="button"
                 {...interfaceTextProps("Animate anyway")}>
                  <LocalizedText source={"Animate anyway"} /></Button>
              }
             {...interfaceTextProps("Run the visualizer until it is hidden, even though reduced motion is enabled.")}/>
          </div>
        ) : null}
        {mode !== 'inline' && (engineName || presetName) ? (
          <div className="player-visualizer-preset" title={presetName}>
            {[engineName, presetName].filter(Boolean).join(' · ')}
          </div>
          ) : null}
        {showNativeDebug && nativeDebugSnapshot ? (
          <div className="player-visualizer-debug" data-testid="visualizer-native-debug">
            <div title={nativeDebugSnapshot.title}>{nativeDebugSnapshot.title}</div>
            <div>
              {nativeDebugSnapshot.format}
              {' · '}
              {nativeDebugSnapshot.presetCount}
              {' '}
              <LocalizedText source={nativeDebugSnapshot.presetCount === 1 ? "preset" : "presets"} />
            </div>
            <div>
              <LocalizedText
                source="{shapes} shapes · {waves} waves · {sprites} sprites"
                values={{
                  shapes: nativeDebugSnapshot.shapes,
                  waves: nativeDebugSnapshot.waves,
                  sprites: nativeDebugSnapshot.sprites,
                }}
              />
            </div>
            <div>
              {nativeDebugSnapshot.shaderSections.warp ? <LocalizedText source={"warp"} /> : <LocalizedText source={"no warp"} />}
              {' / '}
              {nativeDebugSnapshot.shaderSections.comp ? <LocalizedText source={"comp"} /> : <LocalizedText source={"no comp"} />}
            </div>
            <div>
              {nativeFpsCap === 'full' ? <LocalizedText source={"uncapped"} /> : <LocalizedText source={"{nativeFpsCap} fps"} values={{ "nativeFpsCap": (nativeFpsCap) }} />}
              {' · '}
              {nativeFrameMs.toFixed(1)}
              {<LocalizedText source={"ms"} />}
            </div>
            <div>
              {nativeQualityPreset === 'custom'
                ? <LocalizedText source={"custom quality"} />
                : <LocalizedText
                  source="{quality} quality"
                  values={{ quality: nativeQualityPresets[nativeQualityPreset]?.label || interfaceText('Balanced') }}
                />}
              {' · '}
              {getNativeWebGpuDebugLabel(nativeDebugSnapshot.webGpu)}
            </div>
          </div>
        ) : null}
        <div
          className="player-visualizer-overlay-controls"
          onClick={(event) => event.stopPropagation()}
        >
          <input
            accept=".milk,.milk2,.shape,.wave,text/plain,image/png,image/jpeg,image/webp,image/gif"
            hidden
            multiple
            onChange={importNativePreset}
            ref={fileInputRef}
            type="file"
          />
          <input
            data-testid="visualizer-native-pack-input"
            directory=""
            hidden
            multiple
            onChange={importNativePreset}
            ref={directoryInputRef}
            type="file"
            webkitdirectory=""
          />
          <Popup
            content={interfaceText('Cycle visualizer engine to {engine}.', {
              engine: getEngineLabel(getNextEngine(activeEngineType)),
            })}
            trigger={
              <Button
                aria-label={interfaceText('Cycle visualizer engine to {engine}', {
                  engine: getEngineLabel(getNextEngine(activeEngineType)),
                })}
                data-testid="visualizer-switch-engine"
                icon
                onClick={cycleEngineType}
                size="mini"
              >
                <Icon name={getEngineIcon(activeEngineType)} />
              </Button>
            }
          />
          {isNativeEngine(activeEngineType) && !compactControls ? (
            <>
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={interfaceText("Filter imported native presets by title or file name. The current filter also scopes next and random preset jumps.")}
                  trigger={
                    <input
                      aria-label={interfaceText("Search native MilkDrop presets")}
                      className="player-visualizer-native-search"
                      data-testid="visualizer-native-preset-search"
                      onChange={updateNativePresetSearch}
                      placeholder={interfaceText("Search presets")}
                      type="search"
                      value={nativePresetSearch}
                     {...interfaceTextProps("Search native MilkDrop presets")}/>
                  }
                 {...interfaceTextProps("Filter imported native presets by title or file name. The current filter also scopes next and random preset jumps.")}/>
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={interfaceText("Clear the native preset search filter.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Clear native preset search")}
                      data-testid="visualizer-clear-native-preset-search"
                      disabled={!hasNativePresetSearch}
                      icon
                      onClick={clearNativePresetSearch}
                      size="mini"
                     {...interfaceTextProps("Clear native preset search")}>
                      <Icon name="remove" />
                    </Button>
                  }
                 {...interfaceTextProps("Clear the native preset search filter.")}/>
              ) : null}
              {nativePresetPlaylists.length > 0 ? (
                <Popup
                  content={interfaceText("Use a saved native playlist as the active preset bank.")}
                  trigger={
                    <select
                      aria-label={interfaceText("Native MilkDrop playlist")}
                      className="player-visualizer-native-library"
                      data-testid="visualizer-native-playlist"
                      onChange={selectNativePlaylist}
                      value={activeNativePlaylistId}
                     {...interfaceTextProps("Native MilkDrop playlist")}>
                      <option value=""><LocalizedText source={"All imported"} /></option>
                      {nativePresetPlaylists.map((playlist) => (
                        <option key={playlist.id} value={playlist.id}>
                          {playlist.name}
                        </option>
                      ))}
                    </select>
                  }
                 {...interfaceTextProps("Use a saved native playlist as the active preset bank.")}/>
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={interfaceText("Save the current visible native preset bank as a browser-local playlist.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Save visible native presets as playlist")}
                      data-testid="visualizer-save-native-playlist"
                      disabled={!canSaveNativePlaylist}
                      icon
                      onClick={saveNativePlaylistFromVisibleBank}
                      size="mini"
                     {...interfaceTextProps("Save visible native presets as playlist")}>
                      <Icon name="save outline" />
                    </Button>
                  }
                 {...interfaceTextProps("Save the current visible native preset bank as a browser-local playlist.")}/>
              ) : null}
              {activeNativePlaylistId ? (
                <Popup
                  content={interfaceText("Rename the active native playlist in this browser.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Rename active native playlist")}
                      data-testid="visualizer-rename-native-playlist"
                      icon
                      onClick={renameActiveNativePlaylist}
                      size="mini"
                     {...interfaceTextProps("Rename active native playlist")}>
                      <Icon name="edit outline" />
                    </Button>
                  }
                 {...interfaceTextProps("Rename the active native playlist in this browser.")}/>
              ) : null}
              {activeNativePlaylistId ? (
                <Popup
                  content={interfaceText("Return to the full imported native preset bank without deleting this playlist.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Clear active native playlist")}
                      data-testid="visualizer-clear-active-native-playlist"
                      icon
                      onClick={clearActiveNativePlaylist}
                      size="mini"
                     {...interfaceTextProps("Clear active native playlist")}>
                      <Icon name="list" />
                    </Button>
                  }
                 {...interfaceTextProps("Return to the full imported native preset bank without deleting this playlist.")}/>
              ) : null}
              {activeNativePlaylistId ? (
                <Popup
                  content={interfaceText("Delete the active native playlist from this browser.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Delete active native playlist")}
                      data-testid="visualizer-remove-native-playlist"
                      icon
                      onClick={removeActiveNativePlaylist}
                      size="mini"
                     {...interfaceTextProps("Delete active native playlist")}>
                      <Icon name="times circle outline" />
                    </Button>
                  }
                 {...interfaceTextProps("Delete the active native playlist from this browser.")}/>
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={
                    nativeLibraryMode === 'favorites'
                      ? interfaceText('Reload a favorite native preset from this browser.')
                      : interfaceText('Reload a previously imported native preset from this browser.')
                  }
                  trigger={
                    <select
                      aria-label={interfaceText("Native MilkDrop preset library")}
                      className="player-visualizer-native-library"
                      data-testid="visualizer-native-preset-library"
                      onChange={loadNativeLibraryPreset}
                      value={selectedNativePresetValue}
                     {...interfaceTextProps("Native MilkDrop preset library")}>
                      <option value="">
                        {visibleNativePresetLibrary.length === 0 ? <LocalizedText source={"No matches"} /> : (
                          nativeLibraryMode === 'favorites'
                            ? <LocalizedText source={"Favorites"} />
                            : <LocalizedText source={"Presets"} />
                        )}
                      </option>
                      {visibleNativePresetLibrary.map((preset) => (
                        <option key={preset.id} value={preset.id}>
                          {nativeFavoritePresetIds.includes(preset.id) ? <><LocalizedText source={"(favorite)"} />{' '}</> : ''}
                          {preset.title || preset.fileName}
                        </option>
                      ))}
                    </select>
                  }
                />
              ) : null}
              {nativePresetLibrary.length > 0 ? (
              <Popup
                content={interfaceText(activeNativePresetIsFavorite
                  ? 'Remove the active native preset from favorites.'
                  : 'Mark the active native preset as a favorite.')}
                  trigger={
                    <Button
                      aria-label={interfaceText(activeNativePresetIsFavorite
                        ? 'Unfavorite active native preset'
                        : 'Favorite active native preset')}
                      active={activeNativePresetIsFavorite}
                      data-testid="visualizer-toggle-native-favorite"
                      disabled={!activeNativePresetId}
                      icon
                      onClick={toggleNativePresetFavorite}
                      size="mini"
                    >
                      <Icon name={activeNativePresetIsFavorite ? 'star' : 'star outline'} />
                    </Button>
                  }
                />
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={
                    nativeLibraryMode === 'favorites'
                      ? interfaceText('Show all imported native presets.')
                      : interfaceText('Show only favorite native presets.')
                  }
                  trigger={
                    <Button
                      aria-label={
                        nativeLibraryMode === 'favorites'
                          ? interfaceText('Show all native presets')
                          : interfaceText('Show favorite native presets')
                      }
                      active={nativeLibraryMode === 'favorites'}
                      data-testid="visualizer-toggle-native-favorites-only"
                      disabled={nativeFavoritePresetIds.length === 0}
                      icon
                      onClick={toggleNativeLibraryMode}
                      size="mini"
                    >
                      <Icon name="filter" />
                    </Button>
                  }
                />
              ) : null}
              {nativePresetLibrary.length > 1 ? (
                <Popup
                  content={interfaceText("Return to the previous native preset, or move backward in the local preset library.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Previous native preset")}
                      data-testid="visualizer-previous-native-preset"
                      disabled={visibleNativePresetLibrary.length === 0}
                      icon
                      onClick={previousNativeLibraryPreset}
                      size="mini"
                     {...interfaceTextProps("Previous native preset")}>
                      <Icon name="step backward" />
                    </Button>
                  }
                 {...interfaceTextProps("Return to the previous native preset, or move backward in the local preset library.")}/>
              ) : null}
              {nativePresetLibrary.length > 1 ? (
                <Popup
                  content={interfaceText("Jump to a random imported native preset from this browser.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Random imported native preset")}
                      data-testid="visualizer-random-native-preset"
                      disabled={visibleNativePresetLibrary.length === 0}
                      icon
                      onClick={randomNativeLibraryPreset}
                      size="mini"
                     {...interfaceTextProps("Random imported native preset")}>
                      <Icon name="random" />
                    </Button>
                  }
                 {...interfaceTextProps("Jump to a random imported native preset from this browser.")}/>
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={interfaceText("Remove the selected native preset from this browser.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Remove selected native preset")}
                      data-testid="visualizer-remove-native-preset"
                      disabled={!activeNativePresetId}
                      icon
                      onClick={removeActiveNativePreset}
                      size="mini"
                     {...interfaceTextProps("Remove selected native preset")}>
                      <Icon name="minus circle" />
                    </Button>
                  }
                 {...interfaceTextProps("Remove the selected native preset from this browser.")}/>
              ) : null}
              {nativePresetLibrary.length > 0 ? (
                <Popup
                  content={interfaceText("Clear imported native presets from this browser.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Clear imported native presets")}
                      data-testid="visualizer-clear-native-preset-library"
                      icon
                      onClick={clearNativePresetLibrary}
                      size="mini"
                     {...interfaceTextProps("Clear imported native presets")}>
                      <Icon name="trash alternate outline" />
                    </Button>
                  }
                 {...interfaceTextProps("Clear imported native presets from this browser.")}/>
              ) : null}
              <Popup
                content={interfaceText("Import a local .milk or .milk2 preset into the native MilkDrop renderer.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Import native MilkDrop preset")}
                    data-testid="visualizer-import-native-preset"
                    icon
                    onClick={() => fileInputRef.current?.click()}
                    size="mini"
                   {...interfaceTextProps("Import native MilkDrop preset")}>
                    <Icon name="upload" />
                  </Button>
                }
               {...interfaceTextProps("Import a local .milk or .milk2 preset into the native MilkDrop renderer.")}/>
              <Popup
                content={interfaceText("Import a native MilkDrop preset folder with its local image assets.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Import native MilkDrop preset folder")}
                    data-testid="visualizer-import-native-preset-folder"
                    icon
                    onClick={() => directoryInputRef.current?.click()}
                    size="mini"
                   {...interfaceTextProps("Import native MilkDrop preset folder")}>
                    <Icon name="folder open outline" />
                  </Button>
                }
               {...interfaceTextProps("Import a native MilkDrop preset folder with its local image assets.")}/>
              <Popup
                content={interfaceText("Choose a global native MilkDrop parameter to edit on the active preset.")}
                trigger={
                  <select
                    aria-label={interfaceText("Native MilkDrop editable parameter")}
                    className="player-visualizer-native-library"
                    data-testid="visualizer-native-parameter"
                    onChange={selectNativeParameter}
                    value={selectedNativeParameter}
                   {...interfaceTextProps("Native MilkDrop editable parameter")}>
                    {nativeEditableParameters.map((parameter) => (
                      <option key={parameter.key} value={parameter.key}>
                        {parameter.label}
                      </option>
                    ))}
                  </select>
                }
               {...interfaceTextProps("Choose a global native MilkDrop parameter to edit on the active preset.")}/>
              <Popup
                content={interfaceText('Adjust {label} for the active native preset before applying the edited copy locally.', {
                  label: nativeParameter.label.toLowerCase(),
                })}
                trigger={
                  <input
                    aria-label={interfaceText("Adjust native MilkDrop {label}", { "label": (nativeParameter.label) })}
                    className="player-visualizer-native-range"
                    data-testid="visualizer-native-parameter-value"
                    max={nativeParameter.max}
                    min={nativeParameter.min}
                    onChange={updateNativeParameterDraft}
                    step={nativeParameter.step}
                    type="range"
                    value={nativeParameterValue}
                   {...interfaceTextProps("Adjust native MilkDrop {label}")}/>
                }
              />
              <Popup
                content={interfaceText("Apply the selected native MilkDrop parameter value and save the edited preset in this browser.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Apply native MilkDrop parameter edit")}
                    data-testid="visualizer-apply-native-parameter"
                    icon
                    onClick={applyNativeParameterEdit}
                    size="mini"
                   {...interfaceTextProps("Apply native MilkDrop parameter edit")}>
                    <Icon name="sliders horizontal" />
                  </Button>
                }
               {...interfaceTextProps("Apply the selected native MilkDrop parameter value and save the edited preset in this browser.")}/>
              <Popup
                content={interfaceText("Randomize the active native MilkDrop preset's common visual parameters and save the edited copy locally.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Randomize native MilkDrop visual parameters")}
                    data-testid="visualizer-randomize-native-parameters"
                    icon
                    onClick={randomizeNativePresetParameters}
                    size="mini"
                   {...interfaceTextProps("Randomize native MilkDrop visual parameters")}>
                    <Icon name="shuffle" />
                  </Button>
                }
               {...interfaceTextProps("Randomize the active native MilkDrop preset's common visual parameters and save the edited copy locally.")}/>
              <Popup
                content={interfaceText("Show or hide native MilkDrop debug details for the active preset.")}
                trigger={
                  <Button
                    aria-label={interfaceText(showNativeDebug
                      ? 'Hide native MilkDrop debug details'
                      : 'Show native MilkDrop debug details')}
                    active={showNativeDebug}
                    data-testid="visualizer-toggle-native-debug"
                    icon
                    onClick={() => setShowNativeDebug((current) => !current)}
                    size="mini"
                  >
                    <Icon name="bug" />
                  </Button>
                }
               {...interfaceTextProps("Show or hide native MilkDrop debug details for the active preset.")}/>
              <Popup
                content={interfaceText("Cap native MilkDrop rendering for lower GPU load, or leave it uncapped for maximum smoothness.")}
                trigger={
                  <select
                    aria-label={interfaceText("Native MilkDrop FPS cap")}
                    className="player-visualizer-native-library"
                    data-testid="visualizer-native-fps-cap"
                    onChange={updateNativeFpsCap}
                    value={nativeFpsCap}
                   {...interfaceTextProps("Native MilkDrop FPS cap")}>
                    <option value="full"><LocalizedText source={"Full FPS"} /></option>
                    <option value="60"><LocalizedText source={"60 FPS"} /></option>
                    <option value="30"><LocalizedText source={"30 FPS"} /></option>
                    <option value="24"><LocalizedText source={"24 FPS"} /></option>
                  </select>
                }
               {...interfaceTextProps("Cap native MilkDrop rendering for lower GPU load, or leave it uncapped for maximum smoothness.")}/>
              <Popup
                content={interfaceText("Choose a native MilkDrop quality preset. Efficient lowers GPU load, Balanced caps at 60 FPS, and Full leaves rendering uncapped.")}
                trigger={
                  <select
                    aria-label={interfaceText("Native MilkDrop quality preset")}
                    className="player-visualizer-native-library"
                    data-testid="visualizer-native-quality"
                    onChange={updateNativeQualityPreset}
                    value={nativeQualityPreset}
                   {...interfaceTextProps("Native MilkDrop quality preset")}>
                    <option value="balanced"><LocalizedText source={"Balanced"} /></option>
                    <option value="efficient"><LocalizedText source={"Efficient"} /></option>
                    <option value="full"><LocalizedText source={"Full"} /></option>
                    <option value="custom"><LocalizedText source={"Custom"} /></option>
                  </select>
                }
               {...interfaceTextProps("Choose a native MilkDrop quality preset. Efficient lowers GPU load, Balanced caps at 60 FPS, and Full leaves rendering uncapped.")}/>
              <Popup
                content={interfaceText("Export the active native MilkDrop preset text after any local edits.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Export active native MilkDrop preset")}
                    data-testid="visualizer-export-native-preset"
                    icon
                    onClick={exportNativePreset}
                    size="mini"
                   {...interfaceTextProps("Export active native MilkDrop preset")}>
                    <Icon name="file alternate outline" />
                  </Button>
                }
               {...interfaceTextProps("Export the active native MilkDrop preset text after any local edits.")}/>
              <Popup
                content={interfaceText("Choose which custom shape from the active native preset should be exported or removed.")}
                trigger={
                  <select
                    aria-label={interfaceText("Native MilkDrop shape fragment")}
                    className="player-visualizer-native-library"
                    data-testid="visualizer-native-shape-fragment"
                    disabled={!hasNativeShapes}
                    onChange={(event) => setSelectedNativeShapeIndex(Number(event.target.value))}
                    value={hasNativeShapes ? selectedNativeShapeIndex : 0}
                   {...interfaceTextProps("Native MilkDrop shape fragment")}>
                    {hasNativeShapes ? nativeFragmentSummary.shapes.map((shape) => (
                      <option key={shape.index} value={shape.index}>
                        {shape.label}
                      </option>
                    )) : (
                      <option value={0}><LocalizedText source={"No shapes"} /></option>
                    )}
                  </select>
                }
               {...interfaceTextProps("Choose which custom shape from the active native preset should be exported or removed.")}/>
              <Popup
                content={interfaceText("Export the selected custom shape in the active native preset as a .shape fragment.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Export native MilkDrop shape fragment")}
                    data-testid="visualizer-export-native-shape"
                    disabled={!hasNativeShapes}
                    icon
                    onClick={() => exportNativeFragment('shape')}
                    size="mini"
                   {...interfaceTextProps("Export native MilkDrop shape fragment")}>
                    <Icon name="download" />
                  </Button>
                }
               {...interfaceTextProps("Export the selected custom shape in the active native preset as a .shape fragment.")}/>
              <Popup
                content={interfaceText("Remove the selected custom shape from the active native preset and persist the edited copy locally.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Remove native MilkDrop shape fragment")}
                    data-testid="visualizer-remove-native-shape"
                    disabled={!hasNativeShapes}
                    icon
                    onClick={() => removeNativeFragment('shape')}
                    size="mini"
                   {...interfaceTextProps("Remove native MilkDrop shape fragment")}>
                    <Icon name="erase" />
                  </Button>
                }
               {...interfaceTextProps("Remove the selected custom shape from the active native preset and persist the edited copy locally.")}/>
              <Popup
                content={interfaceText("Choose which custom wave from the active native preset should be exported or removed.")}
                trigger={
                  <select
                    aria-label={interfaceText("Native MilkDrop wave fragment")}
                    className="player-visualizer-native-library"
                    data-testid="visualizer-native-wave-fragment"
                    disabled={!hasNativeWaves}
                    onChange={(event) => setSelectedNativeWaveIndex(Number(event.target.value))}
                    value={hasNativeWaves ? selectedNativeWaveIndex : 0}
                   {...interfaceTextProps("Native MilkDrop wave fragment")}>
                    {hasNativeWaves ? nativeFragmentSummary.waves.map((wave) => (
                      <option key={wave.index} value={wave.index}>
                        {wave.label}
                      </option>
                    )) : (
                      <option value={0}><LocalizedText source={"No waves"} /></option>
                    )}
                  </select>
                }
               {...interfaceTextProps("Choose which custom wave from the active native preset should be exported or removed.")}/>
              <Popup
                content={interfaceText("Export the selected custom wave in the active native preset as a .wave fragment.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Export native MilkDrop wave fragment")}
                    data-testid="visualizer-export-native-wave"
                    disabled={!hasNativeWaves}
                    icon
                    onClick={() => exportNativeFragment('wave')}
                    size="mini"
                   {...interfaceTextProps("Export native MilkDrop wave fragment")}>
                    <Icon name="download" />
                  </Button>
                }
               {...interfaceTextProps("Export the selected custom wave in the active native preset as a .wave fragment.")}/>
              <Popup
                content={interfaceText("Remove the selected custom wave from the active native preset and persist the edited copy locally.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Remove native MilkDrop wave fragment")}
                    data-testid="visualizer-remove-native-wave"
                    disabled={!hasNativeWaves}
                    icon
                    onClick={() => removeNativeFragment('wave')}
                    size="mini"
                   {...interfaceTextProps("Remove native MilkDrop wave fragment")}>
                    <Icon name="erase" />
                  </Button>
                }
               {...interfaceTextProps("Remove the selected custom wave from the active native preset and persist the edited copy locally.")}/>
              <Popup
                content={interfaceText('Native automatic preset changes: {mode}. Beat mode advances after repeated detected bass beats; timed mode advances on an interval.', {
                  mode: getNativeAutomationLabel(nativeAutomationMode),
                })}
                trigger={
                  <Button
                    aria-label={interfaceText('Native automatic preset changes: {mode}', {
                      mode: getNativeAutomationLabel(nativeAutomationMode),
                    })}
                    active={nativeAutomationMode !== 'off'}
                    data-testid="visualizer-native-automation"
                    icon
                    onClick={cycleNativeAutomationMode}
                    size="mini"
                  >
                    <Icon name={nativeAutomationMode === 'beat' ? 'heartbeat' : 'clock outline'} />
                  </Button>
                }
              />
              {nativeAutomationMode === 'beat' ? (
                <Popup
                  content={interfaceText("Choose how many detected bass beats should pass before native MilkDrop advances to another preset.")}
                  trigger={
                    <select
                      aria-label={interfaceText("Native MilkDrop beats per preset")}
                      className="player-visualizer-native-library"
                      data-testid="visualizer-native-automation-beats"
                      onChange={updateNativeAutomationBeats}
                      value={nativeAutomationSettings.beatsPerPreset}
                     {...interfaceTextProps("Native MilkDrop beats per preset")}>
                      <option value={4}><LocalizedText source={"4 beats"} /></option>
                      <option value={8}><LocalizedText source={"8 beats"} /></option>
                      <option value={16}><LocalizedText source={"16 beats"} /></option>
                    </select>
                  }
                 {...interfaceTextProps("Choose how many detected bass beats should pass before native MilkDrop advances to another preset.")}/>
              ) : null}
              {nativeAutomationMode === 'timed' ? (
                <Popup
                  content={interfaceText("Choose how long native MilkDrop should wait before timed preset changes.")}
                  trigger={
                    <select
                      aria-label={interfaceText("Native MilkDrop timed preset interval")}
                      className="player-visualizer-native-library"
                      data-testid="visualizer-native-automation-interval"
                      onChange={updateNativeAutomationInterval}
                      value={nativeAutomationSettings.timedIntervalSeconds}
                     {...interfaceTextProps("Native MilkDrop timed preset interval")}>
                      <option value={15}><LocalizedText source={"15 sec"} /></option>
                      <option value={30}><LocalizedText source={"30 sec"} /></option>
                      <option value={60}><LocalizedText source={"60 sec"} /></option>
                    </select>
                  }
                 {...interfaceTextProps("Choose how long native MilkDrop should wait before timed preset changes.")}/>
              ) : null}
            </>
          ) : null}
          <Popup
              content={interfaceText(nativeBankNavigationDisabled
                ? 'No imported native presets match the current filter.'
                : 'Load a different MilkDrop preset.')}
            trigger={
              <Button
                aria-label={interfaceText("Next visualizer preset")}
                data-testid="visualizer-next-preset"
                disabled={nativeBankNavigationDisabled}
                icon
                onClick={cyclePreset}
                size="mini"
               {...interfaceTextProps("Next visualizer preset")}>
                <Icon name="random" />
              </Button>
            }
          />
          {mode === 'inline' && !compactControls ? (
            <>
              <Popup
                content={interfaceText("Expand visualizer to fill the browser window.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Expand visualizer to full browser window")}
                    data-testid="visualizer-fullwindow"
                    icon
                    onClick={() => onModeChange('fullwindow')}
                    size="mini"
                   {...interfaceTextProps("Expand visualizer to full browser window")}>
                    <Icon name="expand arrows alternate" />
                  </Button>
                }
               {...interfaceTextProps("Expand visualizer to fill the browser window.")}/>
              <Popup
                content={interfaceText("Enter true fullscreen.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Enter fullscreen visualizer")}
                    data-testid="visualizer-fullscreen"
                    icon
                    onClick={enterFullscreen}
                    size="mini"
                   {...interfaceTextProps("Enter fullscreen visualizer")}>
                    <Icon name="expand" />
                  </Button>
                }
               {...interfaceTextProps("Enter true fullscreen.")}/>
            </>
          ) : mode === 'inline' ? null : (
            <>
              {mode === 'fullwindow' ? (
                <Popup
                  content={interfaceText("Enter true fullscreen.")}
                  trigger={
                    <Button
                      aria-label={interfaceText("Enter fullscreen visualizer")}
                      data-testid="visualizer-fullscreen"
                      icon
                      onClick={enterFullscreen}
                      size="mini"
                     {...interfaceTextProps("Enter fullscreen visualizer")}>
                      <Icon name="expand" />
                    </Button>
                  }
                 {...interfaceTextProps("Enter true fullscreen.")}/>
              ) : null}
              <Popup
                content={interfaceText("Return visualizer to the player bar.")}
                trigger={
                  <Button
                    aria-label={interfaceText("Collapse visualizer")}
                    data-testid="visualizer-collapse"
                    icon
                    onClick={exitFullscreen}
                    size="mini"
                   {...interfaceTextProps("Collapse visualizer")}>
                    <Icon name="compress" />
                  </Button>
                }
               {...interfaceTextProps("Return visualizer to the player bar.")}/>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Visualizer;
