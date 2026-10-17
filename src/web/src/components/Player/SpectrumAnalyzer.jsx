import { getOrCreateAudioGraph, resumeAudioGraph, suspendAudioGraph } from './audioGraph';
import { interfaceText, interfaceTextProps } from '../../lib/interfaceLocale';
import React, { useCallback, useEffect, useRef } from 'react';
import usePrefersReducedMotion from '../../lib/usePrefersReducedMotion';

const minScopeGainPeak = 0.02;
const scopeTargetPeak = 0.78;
const maxScopeGain = 4;
const scopeDisplaySamples = 192;
const scopeReadIntervalMs = 45;
const drawIntervalMs = 33;

export const getFrequencyBars = (data, barCount) => {
  if (!data?.length || barCount <= 0) return [];

  const maxBin = data.length - 1;
  const minBin = Math.min(2, maxBin);
  const minLog = Math.log10(minBin + 1);
  const maxLog = Math.log10(maxBin + 1);

  return Array.from({ length: barCount }, (_, index) => {
    const startRatio = index / barCount;
    const endRatio = (index + 1) / barCount;
    const startBin = Math.floor(10 ** (minLog + (maxLog - minLog) * startRatio) - 1);
    const endBin = Math.max(
      startBin + 1,
      Math.floor(10 ** (minLog + (maxLog - minLog) * endRatio) - 1),
    );
    const clampedStart = Math.max(0, Math.min(maxBin, startBin));
    const clampedEnd = Math.max(clampedStart, Math.min(maxBin, endBin));
    let total = 0;
    let samples = 0;

    for (let bin = clampedStart; bin <= clampedEnd; bin += 1) {
      total += data[bin];
      samples += 1;
    }

    return samples ? total / samples : 0;
  });
};

export const getScopePoints = (data, width, height, previous = null) => {
  if (!data?.length || width <= 0 || height <= 0) return [];

  const midpoint = height / 2;
  const bucketSize = Math.max(1, Math.floor(data.length / scopeDisplaySamples));
  const normalized = [];

  for (let start = 0; start < data.length; start += bucketSize) {
    let total = 0;
    let samples = 0;
    const end = Math.min(data.length, start + bucketSize);

    for (let index = start; index < end; index += 1) {
      total += (data[index] - 128) / 128;
      samples += 1;
    }

    normalized.push(samples ? total / samples : 0);
  }

  const peak = normalized.reduce(
    (max, value) => Math.max(max, Math.abs(value)),
    0,
  );
  const gain = peak > minScopeGainPeak
    ? Math.min(maxScopeGain, Math.max(1, scopeTargetPeak / peak))
    : 1;

  return normalized.map((value, index) => {
    const prior = previous?.[index]?.normalized ?? value;
    const smoothed = prior * 0.72 + value * 0.28;

    return {
      normalized: smoothed,
      x: (index / (normalized.length - 1 || 1)) * width,
      y: midpoint - smoothed * gain * midpoint * 0.9,
    };
  });
};

export const getScopeLinePoints = (points) =>
  points.map(({ x, y }) => ({ x, y }));

const drawFrequencyBars = (ctx, data, width, height, options = {}) => {
  const { alpha = 1, maxHeightRatio = 1, topOffset = 0 } = options;
  const barCount = Math.min(72, Math.max(18, Math.floor(width / 6)));
  const bars = getFrequencyBars(data, barCount);
  const barWidth = width / bars.length;

  bars.forEach((value, index) => {
    const barHeight = (value / 255) * height * maxHeightRatio;
    const hue = 264 + (index / bars.length) * 24;
    ctx.fillStyle = `hsla(${hue}, 72%, 68%, ${alpha})`;
    ctx.fillRect(
      index * barWidth,
      topOffset + height - barHeight,
      Math.max(1, barWidth - 1),
      barHeight,
    );
  });
};

const drawScopeLine = (ctx, points, width, height, options = {}) => {
  const {
    alpha = 1,
    baselineAlpha = 0.18,
    lineWidth = 2,
  } = options;
  const linePoints = getScopeLinePoints(points);

  ctx.strokeStyle = `rgba(173, 140, 242, ${baselineAlpha})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();

  ctx.shadowBlur = 8;
  ctx.shadowColor = `rgba(173, 140, 242, ${alpha * 0.45})`;
  ctx.strokeStyle = `rgba(202, 181, 250, ${alpha})`;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  linePoints.forEach(({ x, y }, index) => {
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.shadowBlur = 0;
};

const SpectrumAnalyzer = ({
  allowReducedMotionAnimation = false,
  audioElement,
  className = '',
  mode,
}) => {
  const prefersReducedMotion = usePrefersReducedMotion();
  const motionSuppressed = prefersReducedMotion && !allowReducedMotionAnimation;
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const playbackActiveRef = useRef(false);
  const sampleRef = useRef(null);
  const lastDrawRef = useRef(0);
  const scopeLastReadRef = useRef(0);
  const scopePointsRef = useRef(null);
  const motionSuppressedRef = useRef(motionSuppressed);
  motionSuppressedRef.current = motionSuppressed;

  const draw = useCallback(
    (analyser, timestamp = 0) => {
      rafRef.current = null;
      if (document.hidden || !playbackActiveRef.current || motionSuppressedRef.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      if (timestamp && timestamp - lastDrawRef.current < drawIntervalMs) {
        rafRef.current = window.requestAnimationFrame((nextTimestamp) =>
          draw(analyser, nextTimestamp));
        return;
      }
      lastDrawRef.current = timestamp;

      const rect = canvas.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      if (canvas.width !== width) canvas.width = width;
      if (canvas.height !== height) canvas.height = height;

      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#050608';
      ctx.fillRect(0, 0, width, height);

      if (mode === 'scope') {
        let points = scopePointsRef.current;
        const shouldRead = !points || !timestamp
          || timestamp - scopeLastReadRef.current >= scopeReadIntervalMs;

        if (shouldRead) {
          if (sampleRef.current?.length !== analyser.fftSize) {
            sampleRef.current = new Uint8Array(analyser.fftSize);
          }
          const data = sampleRef.current;
          analyser.getByteTimeDomainData(data);
          points = getScopePoints(data, width, height, scopePointsRef.current);
          scopePointsRef.current = points;
          scopeLastReadRef.current = timestamp;
        }

        drawScopeLine(ctx, points, width, height);
      } else {
        if (sampleRef.current?.length !== analyser.frequencyBinCount) {
          sampleRef.current = new Uint8Array(analyser.frequencyBinCount);
        }
        const data = sampleRef.current;
        analyser.getByteFrequencyData(data);
        drawFrequencyBars(ctx, data, width, height);
      }

      rafRef.current = window.requestAnimationFrame((nextTimestamp) =>
        draw(analyser, nextTimestamp));
    },
    [audioElement, mode],
  );

  useEffect(() => {
    if (!audioElement || mode === 'off' || motionSuppressed) return undefined;
    let cancelled = false;
    let analyser = null;
    let graphInitialization = null;
    playbackActiveRef.current = !audioElement.paused && !audioElement.ended &&
      audioElement.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA;

    const stopRendering = () => {
      if (rafRef.current !== null) window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };

    const startRendering = () => {
      if (
        cancelled || document.hidden || !playbackActiveRef.current || !analyser || rafRef.current !== null
      ) return;
      rafRef.current = window.requestAnimationFrame((timestamp) => draw(analyser, timestamp));
    };

    const initializeGraph = () => {
      if (cancelled || graphInitialization) return;
      graphInitialization = Promise.resolve().then(async () => {
        if (!audioElement.paused) return resumeAudioGraph(audioElement);
        const graph = getOrCreateAudioGraph(audioElement);
        await suspendAudioGraph(audioElement);
        return graph;
      });
      graphInitialization.then((graph) => {
        if (cancelled || !graph) return;
        analyser = graph.analyser;
        startRendering();
      });
    };

    const handlePlaying = () => {
      playbackActiveRef.current = true;
      if (analyser) startRendering();
      else initializeGraph();
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
    initializeGraph();

    return () => {
      cancelled = true;
      audioElement.removeEventListener('playing', handlePlaying);
      audioElement.removeEventListener('pause', handleStopped);
      audioElement.removeEventListener('waiting', handleStopped);
      audioElement.removeEventListener('stalled', handleStopped);
      audioElement.removeEventListener('ended', handleStopped);
      audioElement.removeEventListener('error', handleStopped);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      playbackActiveRef.current = false;
      stopRendering();
      scopeLastReadRef.current = 0;
      scopePointsRef.current = null;
      lastDrawRef.current = 0;
      sampleRef.current = null;
    };
  }, [audioElement, draw, mode, motionSuppressed]);

  if (mode === 'off') return null;

  return (
    <canvas
      aria-label={mode === 'scope' ? interfaceText('Oscilloscope') : interfaceText('Spectrum analyzer')}
      className={['player-spectrum', className].filter(Boolean).join(' ')}
      data-testid="player-spectrum"
      data-motion-suppressed={motionSuppressed ? 'true' : undefined}
      ref={canvasRef}
      {...interfaceTextProps(mode === 'scope' ? 'Oscilloscope' : 'Spectrum analyzer')}
    />
  );
};

export default SpectrumAnalyzer;
