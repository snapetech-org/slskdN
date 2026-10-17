import React, { useEffect, useMemo, useRef, useState } from 'react';
import { interfaceText } from '../../lib/interfaceLocale';

const parseTimestamp = (value) => {
  const match = value.match(/^(\d+):(\d+(?:\.\d+)?)$/);
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
};

const parseLrc = (text) =>
  text
    .split('\n')
    .flatMap((line) => {
      const matches = [...line.matchAll(/\[(\d+:\d+(?:\.\d+)?)\]/g)];
      const lyric = line.replace(/\[[^\]]+\]/g, '').trim();
      return matches
        .map((match) => ({
          text: lyric,
          time: parseTimestamp(match[1]),
        }))
        .filter((entry) => entry.time !== null && entry.text);
    })
    .sort((a, b) => a.time - b.time);

const stripAudioExtension = (value) =>
  value.replace(/\.(aac|aiff?|alac|flac|m4a|mp3|ogg|opus|wav|webm)$/i, '');

const cleanTrackText = (value) =>
  stripAudioExtension(value || '')
    .replace(/[_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const isPlaceholderArtist = (value) =>
  !value || ['slskdn', 'unknown', 'local'].includes(value.trim().toLowerCase());

const getLyricsLookup = (current) => {
  if (!current) return null;

  const rawTitle = cleanTrackText(current.title || current.fileName || '');
  const rawArtist = (current.artist || '').trim();
  const filename = cleanTrackText(current.fileName || current.title || '');
  const filenameMatch = filename.match(/^(.+?)\s+-\s+(.+)$/);

  if (isPlaceholderArtist(rawArtist) && filenameMatch) {
    return {
      artist: filenameMatch[1].trim(),
      title: filenameMatch[2].trim(),
    };
  }

  if (!isPlaceholderArtist(rawArtist) && rawTitle) {
    return {
      artist: rawArtist,
      title: rawTitle,
    };
  }

  return null;
};

const lyricsFromResponse = (data) => {
  const synced = data?.syncedLyrics ? parseLrc(data.syncedLyrics) : [];
  if (synced.length) return synced;

  return (data?.plainLyrics || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((text, index) => ({ text, time: null, index }));
};

const firstLyricsCandidate = (data) => {
  if (Array.isArray(data)) {
    return data.find((item) => item?.syncedLyrics) || data.find((item) => item?.plainLyrics) || null;
  }

  return data;
};

const LyricsPane = ({ audioElement, current, visible }) => {
  const activeRef = useRef(null);
  const [lyrics, setLyrics] = useState([]);
  const [position, setPosition] = useState(0);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!visible) {
      setLyrics([]);
      return undefined;
    }

    const lookup = getLyricsLookup(current);
    if (!lookup) {
      setLyrics([]);
      setStatus(interfaceText('Lyrics need artist and title metadata'));
      return undefined;
    }

    const controller = new AbortController();
    const params = new URLSearchParams({
      artist_name: lookup.artist,
      track_name: lookup.title,
    });

    setLyrics([]);
    setStatus(interfaceText('Loading lyrics'));
    fetch(`https://lrclib.net/api/get?${params.toString()}`, {
      signal: controller.signal,
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.syncedLyrics || data?.plainLyrics) return data;

        return fetch(`https://lrclib.net/api/search?${params.toString()}`, {
          signal: controller.signal,
        })
          .then((response) => (response.ok ? response.json() : null))
          .then(firstLyricsCandidate);
      })
      .then((data) => {
        if (controller.signal.aborted) return;
        const parsed = lyricsFromResponse(data);
        setLyrics(parsed);
        setStatus(parsed.length ? '' : interfaceText('No lyrics found'));
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setLyrics([]);
          setStatus(interfaceText('Lyrics unavailable'));
        }
      });

    return () => controller.abort();
  }, [current?.artist, current?.fileName, current?.title, visible]);

  useEffect(() => {
    if (!audioElement || !visible) return undefined;

    const updatePosition = () => {
      if (!document.hidden) {
        setPosition(audioElement.currentTime || 0);
      }
    };
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        updatePosition();
      }
    };

    updatePosition();
    audioElement.addEventListener('loadedmetadata', updatePosition);
    audioElement.addEventListener('seeked', updatePosition);
    audioElement.addEventListener('timeupdate', updatePosition);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      audioElement.removeEventListener('loadedmetadata', updatePosition);
      audioElement.removeEventListener('seeked', updatePosition);
      audioElement.removeEventListener('timeupdate', updatePosition);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [audioElement, visible]);

  const activeIndex = useMemo(() => {
    let index = -1;
    lyrics.forEach((line, lineIndex) => {
      if (line.time !== null && line.time <= position) index = lineIndex;
    });
    return index;
  }, [lyrics, position]);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [activeIndex]);

  if (!visible) return null;

  return (
    <div className="player-lyrics" data-testid="player-lyrics">
      {status ? <div className="player-lyrics-status">{status}</div> : null}
      {lyrics.map((line, index) => (
        <div
          className={
            index === activeIndex
              ? 'player-lyrics-line player-lyrics-line-active'
              : 'player-lyrics-line'
          }
          key={`${line.time ?? line.index}-${line.text}`}
          ref={index === activeIndex ? activeRef : null}
        >
          {line.text}
        </div>
      ))}
    </div>
  );
};

export default LyricsPane;
