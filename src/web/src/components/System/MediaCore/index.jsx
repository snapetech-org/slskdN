import { getRegionalLocale } from '../../../lib/regionalFormat';
import * as mediacore from '../../../lib/mediacore';
import FeatureGateNotice from '../../Shared/FeatureGateNotice';
import useFeatureGates, { isFeatureEnabled } from '../../Shared/useFeatureGates';
import Button from './MediaCoreButton';
import MediaCorePods from './MediaCorePods';
import MediaCoreStats from './MediaCoreStats';
import PodWorkflowNotice from './PodWorkflowNotice';
import {
  contentExamples,
  podWorkflowFilterOptions,
  podWorkflowSections,
} from './mediaCoreWorkflows';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import {
  Card,
  Checkbox,
  Dropdown,
  Form,
  Grid,
  Header,
  Icon,
  Input,
  Label,
  List,
  Loader,
  Message,
  Segment,
  Statistic,
  TextArea,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const asObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};
const CONTENT_ID_STATS_INTERVAL_MS = 60_000;

export const areContentIdStatsEqual = (left, right) => {
  if (left === right) return true;
  if (!left || !right) return false;
  if (
    left.totalDomains !== right.totalDomains ||
    left.totalMappings !== right.totalMappings
  ) {
    return false;
  }

  const leftByDomain = asObject(left.mappingsByDomain);
  const rightByDomain = asObject(right.mappingsByDomain);
  const domains = Object.keys(leftByDomain);
  return (
    domains.length === Object.keys(rightByDomain).length &&
    domains.every((domain) => leftByDomain[domain] === rightByDomain[domain])
  );
};

const MediaCore = () => {
  const { featureGates, ready: featureGatesReady } = useFeatureGates();
  const podsEnabled = featureGatesReady && isFeatureEnabled(featureGates, 'pods');
  const mountedRef = useRef(false);
  const statsLoadedRef = useRef(false);
  const statsInFlightRef = useRef(false);
  const statsIntervalRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [podWorkflowFilter, setPodWorkflowFilter] = useState('all');

  // Form state
  const [externalId, setExternalId] = useState('');
  const [descriptorContentId, setDescriptorContentId] = useState('');
  const [resolveId, setResolveId] = useState('');
  const [validateContentIdInput, setValidateContentIdInput] = useState('');
  const [domain, setDomain] = useState('');
  const [type, setType] = useState('');
  const [resolvedContent, setResolvedContent] = useState(null);
  const [validatedContent, setValidatedContent] = useState(null);
  const [domainResults, setDomainResults] = useState(null);
  const [traversalResults, setTraversalResults] = useState(null);
  const [graphResults, setGraphResults] = useState(null);
  const [inboundResults, setInboundResults] = useState(null);
  const [traverseContentId, setTraverseContentId] = useState('');
  const [traverseLinkName, setTraverseLinkName] = useState('');
  const [graphContentId, setGraphContentId] = useState('');
  const [inboundTargetId, setInboundTargetId] = useState('');
  const [registering, setRegistering] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [searchingDomain, setSearchingDomain] = useState(false);
  const [traversing, setTraversing] = useState(false);
  const [gettingGraph, setGettingGraph] = useState(false);
  const [findingInbound, setFindingInbound] = useState(false);
  const [audioSamples, setAudioSamples] = useState('');
  const [sampleRate, setSampleRate] = useState(44_100);
  const [audioAlgorithm, setAudioAlgorithm] = useState('ChromaPrint');
  const [imagePixels, setImagePixels] = useState('');
  const [imageWidth, setImageWidth] = useState(100);
  const [imageHeight, setImageHeight] = useState(100);
  const [imageAlgorithm, setImageAlgorithm] = useState('PHash');
  const [hashA, setHashA] = useState('');
  const [hashB, setHashB] = useState('');
  const [similarityThreshold, setSimilarityThreshold] = useState(0.8);
  const [audioHashResult, setAudioHashResult] = useState(null);
  const [imageHashResult, setImageHashResult] = useState(null);
  const [similarityResult, setSimilarityResult] = useState(null);
  const [supportedAlgorithms, setSupportedAlgorithms] = useState(null);
  const [computingAudioHash, setComputingAudioHash] = useState(false);
  const [computingImageHash, setComputingImageHash] = useState(false);
  const [computingSimilarity, setComputingSimilarity] = useState(false);
  const [perceptualContentIdA, setPerceptualContentIdA] = useState('');
  const [perceptualContentIdB, setPerceptualContentIdB] = useState('');
  const [perceptualThreshold, setPerceptualThreshold] = useState(0.7);
  const [findSimilarContentId, setFindSimilarContentId] = useState('');
  const [findSimilarMinConfidence, setFindSimilarMinConfidence] = useState(0.7);
  const [findSimilarMaxResults, setFindSimilarMaxResults] = useState(10);
  const [textSimilarityA, setTextSimilarityA] = useState('');
  const [textSimilarityB, setTextSimilarityB] = useState('');
  const [perceptualSimilarityResult, setPerceptualSimilarityResult] =
    useState(null);
  const [findSimilarResult, setFindSimilarResult] = useState(null);
  const [textSimilarityResult, setTextSimilarityResult] = useState(null);
  const [computingPerceptualSimilarity, setComputingPerceptualSimilarity] =
    useState(false);
  const [findingSimilarContent, setFindingSimilarContent] = useState(false);
  const [computingTextSimilarity, setComputingTextSimilarity] = useState(false);
  const [exportContentIds, setExportContentIds] = useState('');
  const [includeLinks, setIncludeLinks] = useState(true);
  const [importPackage, setImportPackage] = useState('');
  const [conflictStrategy, setConflictStrategy] = useState('Merge');
  const [dryRun, setDryRun] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [conflictAnalysis, setConflictAnalysis] = useState(null);
  const [availableStrategies, setAvailableStrategies] = useState(null);
  const [exportingMetadata, setExportingMetadata] = useState(false);
  const [importingMetadata, setImportingMetadata] = useState(false);
  const [analyzingConflicts, setAnalyzingConflicts] = useState(false);
  const [retrievalResult, setRetrievalResult] = useState(null);
  const [batchRetrievalResult, setBatchRetrievalResult] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [descriptorVerificationResult, setDescriptorVerificationResult] =
    useState(null);
  const [retrieveContentId, setRetrieveContentId] = useState('');
  const [batchRetrieveContentIds, setBatchRetrieveContentIds] = useState('');
  const [queryDomain, setQueryDomain] = useState('audio');
  const [queryType, setQueryType] = useState('');
  const [queryMaxResults, setQueryMaxResults] = useState(50);
  const [verifyDescriptor, setVerifyDescriptor] = useState('');
  const [bypassCache, setBypassCache] = useState(false);
  const [retrievingDescriptor, setRetrievingDescriptor] = useState(false);
  const [retrievingBatch, setRetrievingBatch] = useState(false);
  const [queryingDescriptors, setQueryingDescriptors] = useState(false);
  const [verifyingDescriptor, setVerifyingDescriptor] = useState(false);

  const [publishContentId, setPublishContentId] = useState('');
  const [publishCodec, setPublishCodec] = useState('mp3');
  const [publishSize, setPublishSize] = useState(1_024);
  const [batchContentIds, setBatchContentIds] = useState('');
  const [updateTargetId, setUpdateTargetId] = useState('');
  const [updateCodec, setUpdateCodec] = useState('');
  const [updateSize, setUpdateSize] = useState('');
  const [updateConfidence, setUpdateConfidence] = useState('');
  const [publishResult, setPublishResult] = useState(null);
  const [batchPublishResult, setBatchPublishResult] = useState(null);
  const [updateResult, setUpdateResult] = useState(null);
  const [republishResult, setRepublishResult] = useState(null);
  const [publishingStats, setPublishingStats] = useState(null);
  const [publishingDescriptor, setPublishingDescriptor] = useState(false);
  const [publishingBatch, setPublishingBatch] = useState(false);
  const [updatingDescriptor, setUpdatingDescriptor] = useState(false);
  const [republishing, setRepublishing] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);

  const fetchStats = useCallback(async () => {
    if (document.hidden || statsInFlightRef.current) {
      return;
    }

    statsInFlightRef.current = true;
    try {
      if (!statsLoadedRef.current) {
        setLoading(true);
      }
      setError(null);
      const data = await mediacore.getContentIdStats();
      if (!mountedRef.current) return;
      if (document.hidden) return;
      statsLoadedRef.current = true;
      setStats((current) =>
        areContentIdStatsEqual(current, data) ? current : data,
      );
    } catch (error_) {
      if (!mountedRef.current) return;
      if (document.hidden) return;
      setError(error_.message);
    } finally {
      statsInFlightRef.current = false;
      if (mountedRef.current && !document.hidden) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    const stopPolling = () => {
      if (statsIntervalRef.current) {
        window.clearInterval(statsIntervalRef.current);
        statsIntervalRef.current = null;
      }
    };
    const startPolling = () => {
      if (document.hidden || statsIntervalRef.current) {
        return;
      }

      fetchStats();
      statsIntervalRef.current = window.setInterval(
        fetchStats,
        CONTENT_ID_STATS_INTERVAL_MS,
      );
    };
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
      mountedRef.current = false;
    };
  }, [fetchStats]);

  const handleRegister = async () => {
    if (!externalId.trim() || !descriptorContentId.trim()) return;

    try {
      setRegistering(true);
      await mediacore.registerContentId(
        externalId.trim(),
        descriptorContentId.trim(),
      );
      setExternalId('');
      setDescriptorContentId('');

      // Refresh stats
      const data = await mediacore.getContentIdStats();
      setStats(data);
    } catch (error_) {
      setError(`Failed to register: ${error_.message}`);
    } finally {
      setRegistering(false);
    }
  };

  const handleResolve = async () => {
    if (!resolveId.trim()) return;

    try {
      setResolving(true);
      setResolvedContent(null);
      const result = await mediacore.resolveContentId(resolveId.trim());
      setResolvedContent(result);
    } catch (error_) {
      setResolvedContent({ error: error_.message });
    } finally {
      setResolving(false);
    }
  };

  const handleValidate = async () => {
    if (!validateContentIdInput.trim()) return;

    try {
      setValidating(true);
      setValidatedContent(null);
      const result = await mediacore.validateContentId(
        validateContentIdInput.trim(),
      );
      setValidatedContent(result);
    } catch (error_) {
      setValidatedContent({ error: error_.message });
    } finally {
      setValidating(false);
    }
  };

  const handleDomainSearch = async () => {
    if (!domain.trim()) return;

    try {
      setSearchingDomain(true);
      setDomainResults(null);
      const result = type.trim()
        ? await mediacore.findContentIdsByDomainAndType(
            domain.trim(),
            type.trim(),
          )
        : await mediacore.findContentIdsByDomain(domain.trim());
      setDomainResults(result);
    } catch (error_) {
      setDomainResults({ error: error_.message });
    } finally {
      setSearchingDomain(false);
    }
  };

  const fillExample = (domain, type) => {
    const example = contentExamples[domain]?.[type];
    if (example) {
      setExternalId(example.external);
      setResolveId(example.external);
      setDescriptorContentId(example.content);
      setValidateContentIdInput(example.content);
    }
  };

  const handleTraverse = async () => {
    if (!traverseContentId.trim() || !traverseLinkName.trim()) return;

    try {
      setTraversing(true);
      setTraversalResults(null);
      const result = await mediacore.traverseContentGraph(
        traverseContentId.trim(),
        traverseLinkName.trim(),
      );
      setTraversalResults(result);
    } catch (error_) {
      setTraversalResults({ error: error_.message });
    } finally {
      setTraversing(false);
    }
  };

  const handleGetGraph = async () => {
    if (!graphContentId.trim()) return;

    try {
      setGettingGraph(true);
      setGraphResults(null);
      const result = await mediacore.getContentGraph(graphContentId.trim());
      setGraphResults(result);
    } catch (error_) {
      setGraphResults({ error: error_.message });
    } finally {
      setGettingGraph(false);
    }
  };

  const handleFindInbound = async () => {
    if (!inboundTargetId.trim()) return;

    try {
      setFindingInbound(true);
      setInboundResults(null);
      const result = await mediacore.findInboundLinks(inboundTargetId.trim());
      setInboundResults(result);
    } catch (error_) {
      setInboundResults({ error: error_.message });
    } finally {
      setFindingInbound(false);
    }
  };

  const loadSupportedAlgorithms = async () => {
    try {
      const result = await mediacore.getSupportedHashAlgorithms();
      setSupportedAlgorithms(result);
    } catch (error_) {
      console.error('Failed to load hash algorithms:', error_);
    }
  };

  const handleComputeAudioHash = async () => {
    if (!audioSamples.trim()) return;

    try {
      setComputingAudioHash(true);
      setAudioHashResult(null);

      // Parse comma-separated float values
      const samples = audioSamples
        .split(',')
        .map((s) => Number.parseFloat(s.trim()))
        .filter((n) => !isNaN(n));

      if (samples.length === 0) {
        throw new Error('No valid audio samples provided');
      }

      const result = await mediacore.computeAudioHash(
        samples,
        Number.parseInt(sampleRate),
        audioAlgorithm,
      );
      setAudioHashResult(result);
    } catch (error_) {
      setAudioHashResult({ error: error_.message });
    } finally {
      setComputingAudioHash(false);
    }
  };

  const handleComputeImageHash = async () => {
    if (!imagePixels.trim()) return;

    try {
      setComputingImageHash(true);
      setImageHashResult(null);

      // Parse comma-separated byte values (0-255)
      const pixels = imagePixels
        .split(',')
        .map((s) => Number.parseInt(s.trim()))
        .filter((n) => !isNaN(n) && n >= 0 && n <= 255);

      if (pixels.length === 0) {
        throw new Error('No valid pixel data provided');
      }

      const result = await mediacore.computeImageHash(
        pixels,
        Number.parseInt(imageWidth),
        Number.parseInt(imageHeight),
        imageAlgorithm,
      );
      setImageHashResult(result);
    } catch (error_) {
      setImageHashResult({ error: error_.message });
    } finally {
      setComputingImageHash(false);
    }
  };

  const handleComputeSimilarity = async () => {
    if (!hashA.trim() || !hashB.trim()) return;

    try {
      setComputingSimilarity(true);
      setSimilarityResult(null);
      const result = await mediacore.computeHashSimilarity(
        hashA.trim(),
        hashB.trim(),
        Number.parseFloat(similarityThreshold),
      );
      setSimilarityResult(result);
    } catch (error_) {
      setSimilarityResult({ error: error_.message });
    } finally {
      setComputingSimilarity(false);
    }
  };

  const handleComputePerceptualSimilarity = async () => {
    if (!perceptualContentIdA.trim() || !perceptualContentIdB.trim()) return;

    try {
      setComputingPerceptualSimilarity(true);
      setPerceptualSimilarityResult(null);
      const result = await mediacore.computePerceptualSimilarity(
        perceptualContentIdA.trim(),
        perceptualContentIdB.trim(),
        Number.parseFloat(perceptualThreshold),
      );
      setPerceptualSimilarityResult(result);
    } catch (error_) {
      setPerceptualSimilarityResult({ error: error_.message });
    } finally {
      setComputingPerceptualSimilarity(false);
    }
  };

  const handleFindSimilarContent = async () => {
    if (!findSimilarContentId.trim()) return;

    try {
      setFindingSimilarContent(true);
      setFindSimilarResult(null);
      const result = await mediacore.findSimilarContent(
        findSimilarContentId.trim(),
        {
          maxResults: Number.parseInt(findSimilarMaxResults),
          minConfidence: Number.parseFloat(findSimilarMinConfidence),
        },
      );
      setFindSimilarResult(result);
    } catch (error_) {
      setFindSimilarResult({ error: error_.message });
    } finally {
      setFindingSimilarContent(false);
    }
  };

  const handleComputeTextSimilarity = async () => {
    if (!textSimilarityA.trim() || !textSimilarityB.trim()) return;

    try {
      setComputingTextSimilarity(true);
      setTextSimilarityResult(null);
      const result = await mediacore.computeTextSimilarity(
        textSimilarityA.trim(),
        textSimilarityB.trim(),
      );
      setTextSimilarityResult(result);
    } catch (error_) {
      setTextSimilarityResult({ error: error_.message });
    } finally {
      setComputingTextSimilarity(false);
    }
  };

  const handleExportMetadata = async () => {
    const contentIds = exportContentIds
      .split('\n')
      .map((id) => id.trim())
      .filter(Boolean);
    if (!contentIds.length) return;

    try {
      setExportingMetadata(true);
      setExportResult(null);
      const result = await mediacore.exportMetadata(contentIds, includeLinks);
      setExportResult(result);
    } catch (error_) {
      setExportResult({ error: error_.message });
    } finally {
      setExportingMetadata(false);
    }
  };

  const handleImportMetadata = async () => {
    if (!importPackage.trim()) return;

    try {
      setImportingMetadata(true);
      setImportResult(null);

      let packageData;
      try {
        packageData = JSON.parse(importPackage.trim());
      } catch {
        throw new Error('Invalid JSON format for metadata package');
      }

      const result = await mediacore.importMetadata(
        packageData,
        conflictStrategy,
        dryRun,
      );
      setImportResult(result);
    } catch (error_) {
      setImportResult({ error: error_.message });
    } finally {
      setImportingMetadata(false);
    }
  };

  const handleAnalyzeConflicts = async () => {
    if (!importPackage.trim()) return;

    try {
      setAnalyzingConflicts(true);
      setConflictAnalysis(null);

      let packageData;
      try {
        packageData = JSON.parse(importPackage.trim());
      } catch {
        throw new Error('Invalid JSON format for metadata package');
      }

      const result = await mediacore.analyzeMetadataConflicts(packageData);
      setConflictAnalysis(result);
    } catch (error_) {
      setConflictAnalysis({ error: error_.message });
    } finally {
      setAnalyzingConflicts(false);
    }
  };

  const handlePublishDescriptor = async () => {
    if (!publishContentId.trim()) return;

    try {
      setPublishingDescriptor(true);
      setPublishResult(null);

      const descriptor = {
        codec: publishCodec.trim(),
        confidence: 0.8,
        contentId: publishContentId.trim(),
        sizeBytes: Number.parseInt(publishSize),
      };

      const result = await mediacore.publishContentDescriptor(descriptor);
      setPublishResult(result);
    } catch (error_) {
      setPublishResult({ error: error_.message });
    } finally {
      setPublishingDescriptor(false);
    }
  };

  const handlePublishBatch = async () => {
    const contentIds = batchContentIds
      .split('\n')
      .map((id) => id.trim())
      .filter(Boolean);
    if (!contentIds.length) return;

    try {
      setPublishingBatch(true);
      setBatchPublishResult(null);

      // Create mock descriptors for each ContentID
      const descriptors = contentIds.map((contentId) => ({
        // 1MB mock
        codec: 'mock',

        confidence: 0.8,
        contentId,
        sizeBytes: 1_024 * 1_024,
      }));

      const result =
        await mediacore.publishContentDescriptorsBatch(descriptors);
      setBatchPublishResult(result);
    } catch (error_) {
      setBatchPublishResult({ error: error_.message });
    } finally {
      setPublishingBatch(false);
    }
  };

  const handleUpdateDescriptor = async () => {
    if (!updateTargetId.trim()) return;

    try {
      setUpdatingDescriptor(true);
      setUpdateResult(null);

      const updates = {};
      if (updateCodec.trim()) updates.newCodec = updateCodec.trim();
      if (updateSize.trim()) updates.newSizeBytes = Number.parseInt(updateSize);
      if (updateConfidence.trim())
        updates.newConfidence = Number.parseFloat(updateConfidence);

      if (Object.keys(updates).length === 0) {
        throw new Error('At least one update field is required');
      }

      const result = await mediacore.updateContentDescriptor(
        updateTargetId.trim(),
        updates,
      );
      setUpdateResult(result);
    } catch (error_) {
      setUpdateResult({ error: error_.message });
    } finally {
      setUpdatingDescriptor(false);
    }
  };

  const handleRepublishExpiring = async () => {
    try {
      setRepublishing(true);
      setRepublishResult(null);
      const result = await mediacore.republishExpiringDescriptors();
      setRepublishResult(result);
    } catch (error_) {
      setRepublishResult({ error: error_.message });
    } finally {
      setRepublishing(false);
    }
  };

  const handleLoadPublishingStats = async () => {
    try {
      setLoadingStats(true);
      setPublishingStats(null);
      const result = await mediacore.getPublishingStats();
      setPublishingStats(result);
    } catch (error_) {
      setPublishingStats({ error: error_.message });
    } finally {
      setLoadingStats(false);
    }
  };

  const handleRetrieveDescriptor = async () => {
    if (!retrieveContentId.trim()) return;

    try {
      setRetrievingDescriptor(true);
      setRetrievalResult(null);
      const result = await mediacore.retrieveContentDescriptor(
        retrieveContentId.trim(),
        bypassCache,
      );
      setRetrievalResult(result);
    } catch (error_) {
      setRetrievalResult({ error: error_.message });
    } finally {
      setRetrievingDescriptor(false);
    }
  };

  const handleRetrieveBatch = async () => {
    const contentIds = batchRetrieveContentIds
      .split('\n')
      .map((id) => id.trim())
      .filter(Boolean);
    if (!contentIds.length) return;

    try {
      setRetrievingBatch(true);
      setBatchRetrievalResult(null);
      const result =
        await mediacore.retrieveContentDescriptorsBatch(contentIds);
      setBatchRetrievalResult(result);
    } catch (error_) {
      setBatchRetrievalResult({ error: error_.message });
    } finally {
      setRetrievingBatch(false);
    }
  };

  const handleQueryDescriptors = async () => {
    if (!queryDomain.trim()) return;

    try {
      setQueryingDescriptors(true);
      setQueryResult(null);
      const result = await mediacore.queryDescriptorsByDomain(
        queryDomain.trim(),
        queryType.trim() || null,
        Number.parseInt(queryMaxResults),
      );
      setQueryResult(result);
    } catch (error_) {
      setQueryResult({ error: error_.message });
    } finally {
      setQueryingDescriptors(false);
    }
  };

  const handleVerifyDescriptor = async () => {
    if (!verifyDescriptor.trim()) return;

    try {
      setVerifyingDescriptor(true);
      setDescriptorVerificationResult(null);

      let descriptor;
      try {
        descriptor = JSON.parse(verifyDescriptor.trim());
      } catch {
        throw new Error('Invalid JSON format for descriptor');
      }

      const result = await mediacore.verifyContentDescriptor(descriptor);
      setDescriptorVerificationResult(result);
    } catch (error_) {
      setDescriptorVerificationResult({ error: error_.message });
    } finally {
      setVerifyingDescriptor(false);
    }
  };

  // PodCore handlers

  useEffect(() => {
    loadSupportedAlgorithms();
    loadAvailableStrategies();
  }, []);

  const loadAvailableStrategies = async () => {
    try {
      const result = await mediacore.getConflictStrategies();
      setAvailableStrategies(result);
    } catch (error_) {
      console.error('Failed to load conflict strategies:', error_);
    }
  };

  const isPodWorkflowVisible = (sectionId) =>
    podWorkflowFilter === 'all' || podWorkflowFilter === sectionId;
  const selectedPodWorkflow = podWorkflowSections.find(
    (section) => section.href.slice(1) === podWorkflowFilter,
  );

  if (loading && !stats) {
    return (
      <Segment>
        <Loader
          active
          inline="centered"
        >
          Loading MediaCore statistics...
        </Loader>
      </Segment>
    );
  }

  if (error && !stats) {
    return (
      <Message error>
        <Message.Header>Failed to load MediaCore statistics</Message.Header>
        <p>{error}</p>
      </Message>
    );
  }

  return (
    <div>
      <Header as="h2">
        <Icon name="database" />
        MediaCore ContentID Registry
      </Header>

      {podsEnabled ? (
        <Segment>
          <Header as="h3">
            <Icon name="sitemap" />
            Pod Workflow Index
        </Header>
        <Message warning>
          Pod workflows mix read-only diagnostics with operations that publish
          metadata, membership records, messages, opinions, or key material.
          Use this index to jump to the intended workflow before running an
          action.
        </Message>
        <Form>
          <Form.Field>
            <label>Workflow focus</label>
            <Dropdown
              aria-label="Pod workflow focus"
              onChange={(_, { value }) => setPodWorkflowFilter(value)}
              options={podWorkflowFilterOptions}
              selection
              value={podWorkflowFilter}
            />
          </Form.Field>
        </Form>
        {podWorkflowFilter !== 'all' && (
          <Message
            info
            size="small"
          >
            <Message.Content>
              <Message.Header>Focused pod workflow</Message.Header>
              Showing {selectedPodWorkflow?.label || 'one pod workflow'}. Choose
              "Show all pod workflows" or use the reset action to return to the
              complete MediaCore pod surface.
              <div style={{ marginTop: '0.75em' }}>
                <Button
                  tooltip="Show every Pod workflow card so you can browse the full set of available tasks."
                  basic
                  onClick={() => setPodWorkflowFilter('all')}
                  size="tiny"
                >
                  Show all pod workflows
                </Button>
              </div>
            </Message.Content>
          </Message>
        )}
        <Card.Group itemsPerRow={3} stackable>
          {podWorkflowSections.map((section) => (
            <Card
              as="a"
              color={podWorkflowFilter === section.href.slice(1) ? 'blue' : undefined}
              href={`${window.location.pathname}${section.href}`}
              key={section.href}
              onClick={() => setPodWorkflowFilter(section.href.slice(1))}
              raised={podWorkflowFilter === section.href.slice(1)}
            >
              <Card.Content>
                <Card.Header>{section.label}</Card.Header>
                <Card.Meta>{section.risk}</Card.Meta>
                <Card.Description>{section.description}</Card.Description>
              </Card.Content>
            </Card>
          ))}
          </Card.Group>
        </Segment>
      ) : (
        <Segment>
          {featureGatesReady ? (
            <FeatureGateNotice
              configurationKeys={['feature.Pods']}
              featureGate={featureGates.pods}
              featureName="Pods"
            />
          ) : (
            <Message info>Checking PodCore availability…</Message>
          )}
        </Segment>
      )}

      <Grid stackable>
        {/* Statistics Overview */}
        <Grid.Column width={16}>
          <Segment>
            <Header as="h3">Registry Statistics</Header>
            <Statistic.Group size="small">
              <Statistic>
                <Statistic.Value>{stats?.totalMappings || 0}</Statistic.Value>
                <Statistic.Label>Total Mappings</Statistic.Label>
              </Statistic>
              <Statistic>
                <Statistic.Value>{stats?.totalDomains || 0}</Statistic.Value>
                <Statistic.Label>Domains</Statistic.Label>
              </Statistic>
            </Statistic.Group>

            {Object.keys(asObject(stats?.mappingsByDomain)).length > 0 && (
                <div style={{ marginTop: '1em' }}>
                  <Header as="h4">Mappings by Domain</Header>
                  <List horizontal>
                    {Object.entries(asObject(stats?.mappingsByDomain)).map(
                      ([domain, count]) => (
                        <List.Item key={domain}>
                          <Label>
                            {domain}
                            <Label.Detail>{count}</Label.Detail>
                          </Label>
                        </List.Item>
                      ),
                    )}
                  </List>
                </div>
              )}
          </Segment>
        </Grid.Column>

        {/* Register New Mapping */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="plus" />
                Register ContentID Mapping
              </Card.Header>
              <Card.Description>
                Map an external identifier to an internal ContentID
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Resolve and validate existing identifiers first. Registering a
                mapping changes the local ContentID registry and is grouped as
                an advanced operation.
              </Message>
              <details>
                <summary>Advanced ContentID registration controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>External ID</label>
                    <Input
                      onChange={(e) => setExternalId(e.target.value)}
                      placeholder="e.g., mb:recording:12345-6789-..."
                      value={externalId}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Content ID</label>
                    <Input
                      onChange={(e) => setDescriptorContentId(e.target.value)}
                      placeholder="e.g., content:mb:recording:12345-6789-..."
                      value={descriptorContentId}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Add this external-ID-to-ContentID mapping to the local registry so later lookups can resolve it."
                    disabled={
                      !externalId.trim() ||
                      !descriptorContentId.trim() ||
                      registering
                    }
                    loading={registering}
                    onClick={handleRegister}
                    primary
                  >
                    Register Mapping
                  </Button>
                </Form>
              </details>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Resolve External ID */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="search" />
                Resolve External ID
              </Card.Header>
              <Card.Description>
                Find the ContentID for an external identifier
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>External ID to Resolve</label>
                  <Input
                    action={
                      <Button
                        tooltip="Look up this external ID in the local registry to find its associated ContentID."
                        disabled={!resolveId.trim() || resolving}
                        loading={resolving}
                        onClick={handleResolve}
                        primary
                      >
                        Resolve
                      </Button>
                    }
                    onChange={(e) => setResolveId(e.target.value)}
                    placeholder="Enter external ID to resolve..."
                    value={resolveId}
                  />
                </Form.Field>
              </Form>

              {resolvedContent && (
                <div style={{ marginTop: '1em' }}>
                  {resolvedContent.error ? (
                    <Message error>
                      <p>{resolvedContent.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Resolved Successfully</Message.Header>
                      <p>
                        <strong>External ID:</strong>{' '}
                        {resolvedContent.externalId}
                        <br />
                        <strong>Content ID:</strong> {resolvedContent.contentId}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* ContentID Validation */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="check circle" />
                ContentID Validation
              </Card.Header>
              <Card.Description>
                Validate ContentID format and extract components
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>ContentID to Validate</label>
                  <Input
                    action={
                      <Button
                        tooltip="Check the ContentID format and extract its components before using it in another workflow."
                        disabled={!validateContentIdInput.trim() || validating}
                        loading={validating}
                        onClick={handleValidate}
                        primary
                      >
                        Validate
                      </Button>
                    }
                    onChange={(e) => setValidateContentIdInput(e.target.value)}
                    placeholder="e.g., content:audio:track:mb-12345"
                    value={validateContentIdInput}
                  />
                </Form.Field>
              </Form>

              {validatedContent && (
                <div style={{ marginTop: '1em' }}>
                  {validatedContent.error ? (
                    <Message error>
                      <p>{validatedContent.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Valid ContentID</Message.Header>
                      <p>
                        <strong>Domain:</strong> {validatedContent.domain}
                        <br />
                        <strong>Type:</strong> {validatedContent.type}
                        <br />
                        <strong>ID:</strong> {validatedContent.id}
                        <br />
                        <strong>Audio:</strong>{' '}
                        {validatedContent.isAudio ? 'Yes' : 'No'} |
                        <strong>Video:</strong>{' '}
                        {validatedContent.isVideo ? 'Yes' : 'No'} |
                        <strong>Image:</strong>{' '}
                        {validatedContent.isImage ? 'Yes' : 'No'}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Domain Search */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="search plus" />
                Domain Search
              </Card.Header>
              <Card.Description>
                Find ContentIDs by domain and optional type
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>Domain</label>
                    <Input
                      onChange={(e) => setDomain(e.target.value)}
                      placeholder="e.g., audio, video, image"
                      value={domain}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Type (optional)</label>
                    <Input
                      onChange={(e) => setType(e.target.value)}
                      placeholder="e.g., track, movie, photo"
                      value={type}
                    />
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip="Search the local registry for ContentIDs in this domain and optional type so you can find registered items."
                  disabled={!domain.trim() || searchingDomain}
                  loading={searchingDomain}
                  onClick={handleDomainSearch}
                  primary
                >
                  Search Domain
                </Button>
              </Form>

              {domainResults && (
                <div style={{ marginTop: '1em' }}>
                  {domainResults.error ? (
                    <Message error>
                      <p>{domainResults.error}</p>
                    </Message>
                  ) : (
                    <div>
                      <p>
                        <strong>
                          Found {asArray(domainResults.contentIds).length}{' '}
                          ContentIDs
                        </strong>
                      </p>
                      {asArray(domainResults.contentIds).length > 0 && (
                        <List
                          divided
                          relaxed
                          style={{ maxHeight: '200px', overflow: 'auto' }}
                        >
                          {asArray(domainResults.contentIds).map((id, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <code>{id}</code>
                              </List.Content>
                            </List.Item>
                          ))}
                        </List>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Examples */}
        <Grid.Column width={16}>
          <Segment>
            <Header as="h3">
              <Icon name="lightbulb" />
              ContentID Examples
            </Header>
            <p>
              Click any example to fill the read-only resolve and validation
              fields, plus the advanced registration fields.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5em' }}>
              {Object.entries(contentExamples).map(([domainName, types]) =>
                Object.entries(types).map(([typeName, example]) => (
                  <Button
                    tooltip="Fill the related fields with this sample ID pair so you can try resolve, validation, and registration without typing example values."
                    key={`${domainName}-${typeName}`}
                    onClick={() => fillExample(domainName, typeName)}
                    size="small"
                  >
                    {domainName}:{typeName}
                  </Button>
                )),
              )}
            </div>
          </Segment>
        </Grid.Column>

        {/* IPLD Graph Traversal */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="sitemap" />
                IPLD Graph Traversal
              </Card.Header>
              <Card.Description>
                Traverse content relationships following specific link types
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>Start ContentID</label>
                    <Input
                      onChange={(e) => setTraverseContentId(e.target.value)}
                      placeholder="e.g., content:audio:track:mb-12345"
                      value={traverseContentId}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Link Type</label>
                    <Input
                      onChange={(e) => setTraverseLinkName(e.target.value)}
                      placeholder="e.g., album, artist, artwork"
                      value={traverseLinkName}
                    />
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip="Follow the selected link type from this ContentID to inspect connected content records."
                  disabled={
                    !traverseContentId.trim() ||
                    !traverseLinkName.trim() ||
                    traversing
                  }
                  loading={traversing}
                  onClick={handleTraverse}
                  primary
                >
                  Traverse Graph
                </Button>
              </Form>

              {traversalResults && (
                <div style={{ marginTop: '1em' }}>
                  {traversalResults.error ? (
                    <Message error>
                      <p>{traversalResults.error}</p>
                    </Message>
                  ) : (
                    <div>
                      <p>
                        <strong>Traversal completed:</strong>{' '}
                        {traversalResults.completedTraversal ? 'Yes' : 'No'}
                      </p>
                      <p>
                        <strong>
                          Visited {asArray(traversalResults.visitedNodes).length}{' '}
                          nodes
                        </strong>
                      </p>
                      {asArray(traversalResults.visitedNodes).length > 0 && (
                        <List
                          divided
                          relaxed
                          style={{ maxHeight: '150px', overflow: 'auto' }}
                        >
                          {asArray(traversalResults.visitedNodes).map((node, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <List.Header>{node.contentId}</List.Header>
                                <List.Description>
                                  {node.outgoingLinks?.length || 0} outgoing
                                  links
                                </List.Description>
                              </List.Content>
                            </List.Item>
                          ))}
                        </List>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Content Graph */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="share alternate" />
                Content Graph
              </Card.Header>
              <Card.Description>
                Get the complete relationship graph for a ContentID
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>ContentID</label>
                  <Input
                    action={
                      <Button
                        tooltip="Load the known relationship graph for this ContentID so you can review its linked records."
                        disabled={!graphContentId.trim() || gettingGraph}
                        loading={gettingGraph}
                        onClick={handleGetGraph}
                        primary
                      >
                        Get Graph
                      </Button>
                    }
                    onChange={(e) => setGraphContentId(e.target.value)}
                    placeholder="Enter ContentID to get its graph"
                    value={graphContentId}
                  />
                </Form.Field>
              </Form>

              {graphResults && (
                <div style={{ marginTop: '1em' }}>
                  {graphResults.error ? (
                    <Message error>
                      <p>{graphResults.error}</p>
                    </Message>
                  ) : (
                    <div>
                      <p>
                        <strong>Root:</strong> {graphResults.rootContentId}
                      </p>
                      <p>
                        <strong>Nodes:</strong>{' '}
                        {asArray(graphResults.nodes).length}
                      </p>
                      <p>
                        <strong>Paths:</strong>{' '}
                        {graphResults.paths?.length || 0}
                      </p>
                      {asArray(graphResults.nodes).length > 0 && (
                        <List
                          divided
                          relaxed
                          style={{ maxHeight: '150px', overflow: 'auto' }}
                        >
                          {asArray(graphResults.nodes).slice(0, 5).map((node, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <List.Header style={{ fontSize: '0.9em' }}>
                                  {node.contentId}
                                </List.Header>
                                <List.Description style={{ fontSize: '0.8em' }}>
                                  {node.outgoingLinks?.length || 0} outgoing,{' '}
                                  {node.incomingLinks?.length || 0} incoming
                                </List.Description>
                              </List.Content>
                            </List.Item>
                          ))}
                          {graphResults.nodes.length > 5 && (
                            <List.Item>
                              <List.Content>
                                <em>
                                  ... and {graphResults.nodes.length - 5} more
                                  nodes
                                </em>
                              </List.Content>
                            </List.Item>
                          )}
                        </List>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Inbound Links */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="arrow left" />
                Inbound Links
              </Card.Header>
              <Card.Description>
                Find all content that links to a specific ContentID
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>Target ContentID</label>
                  <Input
                    action={
                      <Button
                        tooltip="Find records that link to this ContentID so you can see where the item is referenced."
                        disabled={!inboundTargetId.trim() || findingInbound}
                        loading={findingInbound}
                        onClick={handleFindInbound}
                        primary
                      >
                        Find Links
                      </Button>
                    }
                    onChange={(e) => setInboundTargetId(e.target.value)}
                    placeholder="Find content that links to this ID"
                    value={inboundTargetId}
                  />
                </Form.Field>
              </Form>

              {inboundResults && (
                <div style={{ marginTop: '1em' }}>
                  {inboundResults.error ? (
                    <Message error>
                      <p>{inboundResults.error}</p>
                    </Message>
                  ) : (
                    <div>
                      <p>
                        <strong>
                          Found {asArray(inboundResults.inboundLinks).length}{' '}
                          inbound links
                        </strong>
                      </p>
                      {asArray(inboundResults.inboundLinks).length > 0 && (
                        <List
                          divided
                          relaxed
                          style={{ maxHeight: '150px', overflow: 'auto' }}
                        >
                          {asArray(inboundResults.inboundLinks).map((link, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <code style={{ fontSize: '0.9em' }}>
                                  {link}
                                </code>
                              </List.Content>
                            </List.Item>
                          ))}
                        </List>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Perceptual Hash - Audio */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="sound" />
                Audio Perceptual Hash
              </Card.Header>
              <Card.Description>
                Compute perceptual hash for audio similarity detection
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Similarity review and hashing statistics are the default path.
                Raw sample hashing is a diagnostic operation for prepared sample
                arrays.
              </Message>
              <details>
                <summary>Advanced raw audio hash controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label>Algorithm</label>
                      <Dropdown
                        onChange={(e, { value }) => setAudioAlgorithm(value)}
                        options={
                          asArray(supportedAlgorithms?.algorithms).map((alg) => ({
                            key: alg,
                            text: alg,
                            value: alg,
                          }))
                        }
                        selection
                        value={audioAlgorithm}
                      />
                    </Form.Field>
                    <Form.Field>
                      <label>Sample Rate (Hz)</label>
                      <Input
                        onChange={(e) => setSampleRate(e.target.value)}
                        type="number"
                        value={sampleRate}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label>Audio Samples (comma-separated floats)</label>
                    <TextArea
                      onChange={(e) => setAudioSamples(e.target.value)}
                      placeholder="0.1, -0.2, 0.3, ... (normalized -1.0 to 1.0)"
                      rows={3}
                      value={audioSamples}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Compute the selected audio fingerprint from the supplied sample data so you can compare or identify audio."
                    disabled={!audioSamples.trim() || computingAudioHash}
                    loading={computingAudioHash}
                    onClick={handleComputeAudioHash}
                    primary
                  >
                    Compute Audio Hash
                  </Button>
                </Form>
              </details>

              {audioHashResult && (
                <div style={{ marginTop: '1em' }}>
                  {audioHashResult.error ? (
                    <Message error>
                      <p>{audioHashResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Audio Hash Computed</Message.Header>
                      <p>
                        <strong>Algorithm:</strong> {audioHashResult.algorithm}
                        <br />
                        <strong>Hex Hash:</strong> {audioHashResult.hex}
                        <br />
                        <strong>Sample Count:</strong>{' '}
                        {audioSamples.split(',').filter((s) => s.trim()).length}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Perceptual Hash - Image */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="image" />
                Image Perceptual Hash
              </Card.Header>
              <Card.Description>
                Compute perceptual hash for image similarity detection
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Similarity review and hashing statistics are the default path.
                Raw pixel hashing is a diagnostic operation for prepared image
                buffers.
              </Message>
              <details>
                <summary>Advanced raw image hash controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label>Algorithm</label>
                      <Dropdown
                        onChange={(e, { value }) => setImageAlgorithm(value)}
                        options={
                          asArray(supportedAlgorithms?.algorithms)
                            .filter((alg) => alg !== 'ChromaPrint')
                            .map((alg) => ({
                              key: alg,
                              text: alg,
                              value: alg,
                            }))
                        }
                        selection
                        value={imageAlgorithm}
                      />
                    </Form.Field>
                    <Form.Field>
                      <label>Dimensions</label>
                      <Input
                        onChange={(e) => {
                          const [w, h] = e.target.value
                            .split('x')
                            .map((s) => Number.parseInt(s.trim()));
                          if (!isNaN(w)) setImageWidth(w);
                          if (!isNaN(h)) setImageHeight(h);
                        }}
                        placeholder="Width x Height"
                        value={`${imageWidth}x${imageHeight}`}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label>Pixel Data (comma-separated bytes 0-255)</label>
                    <TextArea
                      onChange={(e) => setImagePixels(e.target.value)}
                      placeholder="255, 128, 64, ... (RGBA pixel data)"
                      rows={3}
                      value={imagePixels}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Compute the selected image fingerprint from the supplied pixel data so you can compare images."
                    disabled={!imagePixels.trim() || computingImageHash}
                    loading={computingImageHash}
                    onClick={handleComputeImageHash}
                    primary
                  >
                    Compute Image Hash
                  </Button>
                </Form>
              </details>

              {imageHashResult && (
                <div style={{ marginTop: '1em' }}>
                  {imageHashResult.error ? (
                    <Message error>
                      <p>{imageHashResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Image Hash Computed</Message.Header>
                      <p>
                        <strong>Algorithm:</strong> {imageHashResult.algorithm}
                        <br />
                        <strong>Hex Hash:</strong> {imageHashResult.hex}
                        <br />
                        <strong>Dimensions:</strong> {imageWidth}x{imageHeight}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Hash Similarity Analysis */}
        <Grid.Column width={16}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="balance scale" />
                Hash Similarity Analysis
              </Card.Header>
              <Card.Description>
                Compare perceptual hashes to determine content similarity
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>Hash A (hex)</label>
                    <Input
                      onChange={(e) => setHashA(e.target.value)}
                      placeholder="First hash value (hexadecimal)"
                      value={hashA}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Hash B (hex)</label>
                    <Input
                      onChange={(e) => setHashB(e.target.value)}
                      placeholder="Second hash value (hexadecimal)"
                      value={hashB}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Similarity Threshold</label>
                    <Input
                      max="1"
                      min="0"
                      onChange={(e) => setSimilarityThreshold(e.target.value)}
                      step="0.1"
                      type="number"
                      value={similarityThreshold}
                    />
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip="Compare these two hashes against the chosen threshold to see whether they are a likely match."
                  disabled={
                    !hashA.trim() || !hashB.trim() || computingSimilarity
                  }
                  loading={computingSimilarity}
                  onClick={handleComputeSimilarity}
                  primary
                >
                  Analyze Similarity
                </Button>
              </Form>

              {similarityResult && (
                <div style={{ marginTop: '1em' }}>
                  {similarityResult.error ? (
                    <Message error>
                      <p>{similarityResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>
                        Similarity Analysis Results
                      </Message.Header>
                      <p>
                        <strong>Hamming Distance:</strong>{' '}
                        {similarityResult.hammingDistance} bits
                        <br />
                        <strong>Similarity Score:</strong>{' '}
                        {(similarityResult.similarity * 100).toFixed(1)}%<br />
                        <strong>Are Similar:</strong>{' '}
                        {similarityResult.areSimilar ? 'Yes' : 'No'} (threshold:{' '}
                        {(similarityResult.threshold * 100).toFixed(1)}%)
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Fuzzy Content Matching */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="magic" />
                Fuzzy Content Matching
              </Card.Header>
              <Card.Description>
                Find similar content using perceptual hashes and text analysis
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Pairwise perceptual and text similarity are the default review
                paths. Candidate search can scan registry entries, so it is
                grouped as an advanced similarity search.
              </Message>
              <details>
                <summary>Advanced similarity candidate search controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>Target ContentID</label>
                    <Input
                      onChange={(e) => setFindSimilarContentId(e.target.value)}
                      placeholder="ContentID to find matches for"
                      value={findSimilarContentId}
                    />
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label>Min Confidence</label>
                      <Input
                        max="1"
                        min="0"
                        onChange={(e) =>
                          setFindSimilarMinConfidence(e.target.value)
                        }
                        step="0.1"
                        type="number"
                        value={findSimilarMinConfidence}
                      />
                    </Form.Field>
                    <Form.Field>
                      <label>Max Results</label>
                      <Input
                        max="50"
                        min="1"
                        onChange={(e) =>
                          setFindSimilarMaxResults(e.target.value)
                        }
                        type="number"
                        value={findSimilarMaxResults}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Button
                    tooltip="Search for content similar to this ID using the selected confidence and result limits."
                    disabled={
                      !findSimilarContentId.trim() || findingSimilarContent
                    }
                    loading={findingSimilarContent}
                    onClick={handleFindSimilarContent}
                    primary
                  >
                    Find Similar Content
                  </Button>
                </Form>
              </details>

              {findSimilarResult && (
                <div style={{ marginTop: '1em' }}>
                  {findSimilarResult.error ? (
                    <Message error>
                      <p>{findSimilarResult.error}</p>
                    </Message>
                  ) : (
                    <div>
                      <p>
                        <strong>Target:</strong>{' '}
                        {findSimilarResult.targetContentId}
                      </p>
                      <p>
                        <strong>
                          Searched {findSimilarResult.totalCandidates}{' '}
                          candidates
                        </strong>
                      </p>
                      <p>
                        <strong>
                          Found {asArray(findSimilarResult.matches).length} matches
                        </strong>
                      </p>
                      {asArray(findSimilarResult.matches).length > 0 && (
                        <List
                          divided
                          relaxed
                          style={{ maxHeight: '200px', overflow: 'auto' }}
                        >
                          {asArray(findSimilarResult.matches).map((match, index) => (
                            <List.Item key={index}>
                              <List.Content>
                                <List.Header style={{ fontSize: '0.9em' }}>
                                  {match.candidateContentId}
                                </List.Header>
                                <List.Description>
                                  Confidence:{' '}
                                  {(match.confidence * 100).toFixed(1)}% |
                                  Reason: {match.reason}
                                </List.Description>
                              </List.Content>
                            </List.Item>
                          ))}
                        </List>
                      )}
                    </div>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Perceptual Similarity */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="chart bar" />
                Perceptual Similarity
              </Card.Header>
              <Card.Description>
                Compare perceptual similarity between two ContentIDs
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>ContentID A</label>
                    <Input
                      onChange={(e) => setPerceptualContentIdA(e.target.value)}
                      placeholder="First ContentID"
                      value={perceptualContentIdA}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>ContentID B</label>
                    <Input
                      onChange={(e) => setPerceptualContentIdB(e.target.value)}
                      placeholder="Second ContentID"
                      value={perceptualContentIdB}
                    />
                  </Form.Field>
                </Form.Group>
                <Form.Field>
                  <label>Similarity Threshold</label>
                  <Input
                    max="1"
                    min="0"
                    onChange={(e) => setPerceptualThreshold(e.target.value)}
                    step="0.1"
                    type="number"
                    value={perceptualThreshold}
                  />
                </Form.Field>
                <Button
                  tooltip="Compare these content IDs using their perceptual signatures and threshold to find similar media."
                  disabled={
                    !perceptualContentIdA.trim() ||
                    !perceptualContentIdB.trim() ||
                    computingPerceptualSimilarity
                  }
                  loading={computingPerceptualSimilarity}
                  onClick={handleComputePerceptualSimilarity}
                  primary
                >
                  Compute Similarity
                </Button>
              </Form>

              {perceptualSimilarityResult && (
                <div style={{ marginTop: '1em' }}>
                  {perceptualSimilarityResult.error ? (
                    <Message error>
                      <p>{perceptualSimilarityResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>Similarity Analysis</Message.Header>
                      <p>
                        <strong>Content A:</strong>{' '}
                        {perceptualSimilarityResult.contentIdA}
                        <br />
                        <strong>Content B:</strong>{' '}
                        {perceptualSimilarityResult.contentIdB}
                        <br />
                        <strong>Similarity:</strong>{' '}
                        {(perceptualSimilarityResult.similarity * 100).toFixed(
                          1,
                        )}
                        %<br />
                        <strong>Are Similar:</strong>{' '}
                        {perceptualSimilarityResult.isSimilar ? 'Yes' : 'No'}{' '}
                        (threshold:{' '}
                        {(perceptualSimilarityResult.threshold * 100).toFixed(
                          1,
                        )}
                        %)
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Text Similarity */}
        <Grid.Column width={16}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="font" />
                Text Similarity Analysis
              </Card.Header>
              <Card.Description>
                Compare text strings using Levenshtein distance and phonetic
                matching
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>Text A</label>
                    <Input
                      onChange={(e) => setTextSimilarityA(e.target.value)}
                      placeholder="First text string"
                      value={textSimilarityA}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Text B</label>
                    <Input
                      onChange={(e) => setTextSimilarityB(e.target.value)}
                      placeholder="Second text string"
                      value={textSimilarityB}
                    />
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip="Compare the supplied text values to measure how closely their content matches."
                  disabled={
                    !textSimilarityA.trim() ||
                    !textSimilarityB.trim() ||
                    computingTextSimilarity
                  }
                  loading={computingTextSimilarity}
                  onClick={handleComputeTextSimilarity}
                  primary
                >
                  Analyze Text Similarity
                </Button>
              </Form>

              {textSimilarityResult && (
                <div style={{ marginTop: '1em' }}>
                  {textSimilarityResult.error ? (
                    <Message error>
                      <p>{textSimilarityResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Text Similarity Results</Message.Header>
                      <p>
                        <strong>Text A:</strong> "{textSimilarityResult.textA}"
                        <br />
                        <strong>Text B:</strong> "{textSimilarityResult.textB}"
                        <br />
                        <strong>Levenshtein Similarity:</strong>{' '}
                        {(
                          textSimilarityResult.levenshteinSimilarity * 100
                        ).toFixed(1)}
                        %<br />
                        <strong>Phonetic Similarity:</strong>{' '}
                        {(
                          textSimilarityResult.phoneticSimilarity * 100
                        ).toFixed(1)}
                        %<br />
                        <strong>Combined Similarity:</strong>{' '}
                        {(
                          textSimilarityResult.combinedSimilarity * 100
                        ).toFixed(1)}
                        %
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Metadata Portability - Export */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="download" />
                Export Metadata
              </Card.Header>
              <Card.Description>
                Export metadata for ContentIDs to a portable package
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>ContentIDs (one per line)</label>
                  <TextArea
                    onChange={(e) => setExportContentIds(e.target.value)}
                    placeholder="content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;..."
                    rows={4}
                    value={exportContentIds}
                  />
                </Form.Field>
                <Form.Field>
                  <Checkbox
                    checked={includeLinks}
                    label="Include IPLD links"
                    onChange={(e, { checked }) => setIncludeLinks(checked)}
                  />
                </Form.Field>
                <Button
                  tooltip="Build a metadata package for the selected ContentIDs and optional links so you can back it up or review it. This does not publish the package."
                  disabled={!exportContentIds.trim() || exportingMetadata}
                  loading={exportingMetadata}
                  onClick={handleExportMetadata}
                  primary
                >
                  Export Metadata
                </Button>
              </Form>

              {exportResult && (
                <div style={{ marginTop: '1em' }}>
                  {exportResult.error ? (
                    <Message error>
                      <p>{exportResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Export Successful</Message.Header>
                      <p>
                        <strong>Version:</strong> {exportResult.version}
                        <br />
                        <strong>Entries:</strong>{' '}
                        {exportResult.metadata?.totalEntries || 0}
                        <br />
                        <strong>Links:</strong>{' '}
                        {exportResult.metadata?.totalLinks || 0}
                        <br />
                        <strong>Checksum:</strong>{' '}
                        {exportResult.metadata?.checksum?.slice(0, 16)}...
                      </p>
                      <details>
                        <summary>View Package JSON</summary>
                        <pre
                          style={{
                            fontSize: '0.8em',
                            maxHeight: '200px',
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(exportResult, null, 2)}
                        </pre>
                      </details>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Metadata Portability - Import */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="upload" />
                Import Metadata
              </Card.Header>
              <Card.Description>
                Import metadata from a portable package with conflict resolution
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>Conflict Resolution Strategy</label>
                  <Dropdown
                    onChange={(e, { value }) => setConflictStrategy(value)}
                      options={
                      asArray(availableStrategies?.strategies).map((s) => ({
                        description: s.description,
                        key: s.strategy,
                        text: s.name,
                        value: s.strategy,
                      }))
                    }
                    selection
                    value={conflictStrategy}
                  />
                </Form.Field>
                <Form.Field>
                  <Checkbox
                    checked={dryRun}
                    label="Dry run (preview changes without applying)"
                    onChange={(e, { checked }) => setDryRun(checked)}
                  />
                </Form.Field>
                <Button
                  tooltip="Preview conflicts between this package and the local registry without importing changes; use this before choosing an import strategy."
                  disabled={!importPackage.trim() || analyzingConflicts}
                  loading={analyzingConflicts}
                  onClick={handleAnalyzeConflicts}
                  secondary
                >
                  Analyze Conflicts
                </Button>
              </Form>

              {/* Import Package Input */}
              <Form style={{ marginTop: '1em' }}>
                <Form.Field>
                  <label>Metadata Package (JSON)</label>
                  <TextArea
                    onChange={(e) => setImportPackage(e.target.value)}
                    placeholder="Paste exported metadata package JSON here..."
                    rows={6}
                    value={importPackage}
                  />
                </Form.Field>
              </Form>
              <details style={{ marginTop: '1em' }}>
                <summary>Advanced metadata import controls</summary>
                <Message warning size="small">
                  Importing applies package metadata to the local registry. Run
                  conflict analysis first, then import only when the selected
                  strategy is intentional.
                </Message>
                <Button
                  tooltip={
                    dryRun
                      ? 'Preview the changes this package would make to the local registry without applying them.'
                      : 'Import this package and apply its changes to the local registry. Review the conflict strategy before applying.'
                  }
                  disabled={!importPackage.trim() || importingMetadata}
                  loading={importingMetadata}
                  onClick={handleImportMetadata}
                  primary
                >
                  Import Metadata
                </Button>
              </details>

              {/* Results */}
              {conflictAnalysis && (
                <div style={{ marginTop: '1em' }}>
                  {conflictAnalysis.error ? (
                    <Message error>
                      <p>{conflictAnalysis.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>Conflict Analysis</Message.Header>
                      <p>
                        <strong>Total Entries:</strong>{' '}
                        {conflictAnalysis.totalEntries}
                        <br />
                        <strong>Conflicting:</strong>{' '}
                        {conflictAnalysis.conflictingEntries}
                        <br />
                        <strong>Clean:</strong> {conflictAnalysis.cleanEntries}
                        <br />
                        <strong>Recommended Strategy:</strong>{' '}
                        {Object.entries(
                          conflictAnalysis.recommendedStrategies || {},
                        ).sort(([, a], [, b]) => b - a)[0]?.[0] || 'Merge'}
                      </p>
                    </Message>
                  )}
                </div>
              )}

              {importResult && (
                <div style={{ marginTop: '1em' }}>
                  {importResult.error ? (
                    <Message error>
                      <p>{importResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>
                        Import{' '}
                        {importResult.success
                          ? 'Successful'
                          : 'Completed with Issues'}
                      </Message.Header>
                      <p>
                        <strong>Processed:</strong>{' '}
                        {importResult.entriesProcessed}
                        <br />
                        <strong>Imported:</strong>{' '}
                        {importResult.entriesImported}
                        <br />
                        <strong>Skipped:</strong> {importResult.entriesSkipped}
                        <br />
                        <strong>Conflicts Resolved:</strong>{' '}
                        {importResult.conflictsResolved}
                        <br />
                        <strong>Duration:</strong>{' '}
                        {importResult.duration?.TotalSeconds.toFixed(2)}s
                      </p>
                      {asArray(importResult.errors).length > 0 && (
                        <details>
                          <summary>
                            Errors ({asArray(importResult.errors).length})
                          </summary>
                          <List bulleted>
                            {asArray(importResult.errors).map((error, index) => (
                              <List.Item key={index}>{error}</List.Item>
                            ))}
                          </List>
                        </details>
                      )}
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Content Descriptor Publishing */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="cloud upload" />
                Publish Content Descriptor
              </Card.Header>
              <Card.Description>
                Publish a content descriptor to the DHT with versioning support
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Descriptor publishing changes DHT-visible metadata. Retrieval
                and stats are the default workflow; publishing controls are
                grouped as advanced operations.
              </Message>
              <details>
                <summary>Advanced descriptor publishing controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>ContentID</label>
                    <Input
                      onChange={(e) => setPublishContentId(e.target.value)}
                      placeholder="content:audio:track:mb-12345"
                      value={publishContentId}
                    />
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label>Codec</label>
                      <Input
                        onChange={(e) => setPublishCodec(e.target.value)}
                        placeholder="mp3, flac, etc."
                        value={publishCodec}
                      />
                    </Form.Field>
                    <Form.Field>
                      <label>Size (bytes)</label>
                      <Input
                        onChange={(e) => setPublishSize(e.target.value)}
                        type="number"
                        value={publishSize}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Button
                    tooltip="Publish a descriptor for this ContentID to the DHT so other participants can discover it. Review the supplied metadata before publishing."
                    disabled={!publishContentId.trim() || publishingDescriptor}
                    loading={publishingDescriptor}
                    onClick={handlePublishDescriptor}
                    primary
                  >
                    Publish Descriptor
                  </Button>
                </Form>
              </details>

              {publishResult && (
                <div style={{ marginTop: '1em' }}>
                  {publishResult.error ? (
                    <Message error>
                      <p>{publishResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Published Successfully</Message.Header>
                      <p>
                        <strong>ContentID:</strong> {publishResult.contentId}
                        <br />
                        <strong>Version:</strong> {publishResult.version}
                        <br />
                        <strong>TTL:</strong> {publishResult.ttl?.totalMinutes}{' '}
                        minutes
                        <br />
                        <strong>Was Updated:</strong>{' '}
                        {publishResult.wasUpdated ? 'Yes' : 'No'}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Batch Publishing */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="list" />
                Batch Publish Descriptors
              </Card.Header>
              <Card.Description>
                Publish multiple content descriptors simultaneously
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Batch publishing can expose multiple descriptors at once. Keep
                retrieval and stats as the default path; use this only after
                checking each ContentID.
              </Message>
              <details>
                <summary>Advanced batch publishing controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>ContentIDs (one per line)</label>
                    <TextArea
                      onChange={(e) => setBatchContentIds(e.target.value)}
                      placeholder="content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;..."
                      rows={6}
                      value={batchContentIds}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Publish one descriptor for each listed ContentID to the DHT. Review the full list because each entry creates a network write."
                    disabled={!batchContentIds.trim() || publishingBatch}
                    loading={publishingBatch}
                    onClick={handlePublishBatch}
                    primary
                  >
                    Publish Batch
                  </Button>
                </Form>
              </details>

              {batchPublishResult && (
                <div style={{ marginTop: '1em' }}>
                  {batchPublishResult.error ? (
                    <Message error>
                      <p>{batchPublishResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>Batch Publish Results</Message.Header>
                      <p>
                        <strong>Total Requested:</strong>{' '}
                        {batchPublishResult.totalRequested}
                        <br />
                        <strong>Successfully Published:</strong>{' '}
                        {batchPublishResult.successfullyPublished}
                        <br />
                        <strong>Failed:</strong>{' '}
                        {batchPublishResult.failedToPublish}
                        <br />
                        <strong>Skipped:</strong> {batchPublishResult.skipped}
                        <br />
                        <strong>Duration:</strong>{' '}
                        {batchPublishResult.totalDuration?.totalSeconds.toFixed(
                          2,
                        )}
                        s
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Descriptor Updates */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="edit" />
                Update Descriptor
              </Card.Header>
              <Card.Description>
                Update metadata for an existing published descriptor
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Descriptor updates alter an existing publication. Retrieve and
                verify the descriptor first, then use this advanced path only
                for deliberate metadata corrections.
              </Message>
              <details>
                <summary>Advanced descriptor update controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>Target ContentID</label>
                    <Input
                      onChange={(e) => setUpdateTargetId(e.target.value)}
                      placeholder="ContentID to update"
                      value={updateTargetId}
                    />
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label>New Codec</label>
                      <Input
                        onChange={(e) => setUpdateCodec(e.target.value)}
                        placeholder="Leave empty to keep current"
                        value={updateCodec}
                      />
                    </Form.Field>
                    <Form.Field>
                      <label>New Size (bytes)</label>
                      <Input
                        onChange={(e) => setUpdateSize(e.target.value)}
                        placeholder="Leave empty to keep current"
                        value={updateSize}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label>New Confidence (0.0-1.0)</label>
                    <Input
                      onChange={(e) => setUpdateConfidence(e.target.value)}
                      placeholder="Leave empty to keep current"
                      value={updateConfidence}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Update the selected descriptor in the DHT so participants see the new values. Verify the ContentID and fields before applying."
                    disabled={!updateTargetId.trim() || updatingDescriptor}
                    loading={updatingDescriptor}
                    onClick={handleUpdateDescriptor}
                    primary
                  >
                    Update Descriptor
                  </Button>
                </Form>
              </details>

              {updateResult && (
                <div style={{ marginTop: '1em' }}>
                  {updateResult.error ? (
                    <Message error>
                      <p>{updateResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Update Successful</Message.Header>
                      <p>
                        <strong>ContentID:</strong> {updateResult.contentId}
                        <br />
                        <strong>Version:</strong> {updateResult.previousVersion}{' '}
                        → {updateResult.newVersion}
                        <br />
                        <strong>Updates Applied:</strong>{' '}
                        {updateResult.appliedUpdates?.join(', ') || 'none'}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Publishing Management */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="cogs" />
                Publishing Management
              </Card.Header>
              <Card.Description>
                Manage published descriptors and monitor publishing status
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Button.Group fluid>
                <Button
                  tooltip="Load local descriptor publication counts and timings so you can review recent publishing activity."
                  disabled={loadingStats}
                  loading={loadingStats}
                  onClick={handleLoadPublishingStats}
                >
                  Load Stats
                </Button>
              </Button.Group>
              <details style={{ marginTop: '1em' }}>
                <summary>Advanced descriptor republishing controls</summary>
                <Message warning size="small">
                  Republish only after reviewing publishing statistics. This
                  refreshes DHT-visible descriptor records that are close to
                  expiry.
                </Message>
                <Button
                  tooltip="Republish descriptors nearing expiry so they remain discoverable. This performs DHT writes; run it when renewal is needed."
                  disabled={republishing}
                  loading={republishing}
                  onClick={handleRepublishExpiring}
                >
                  Republish Expiring
                </Button>
              </details>

              {/* Republish Results */}
              {republishResult && (
                <div style={{ marginTop: '1em' }}>
                  {republishResult.error ? (
                    <Message error>
                      <p>{republishResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>Republish Results</Message.Header>
                      <p>
                        <strong>Checked:</strong> {republishResult.totalChecked}
                        <br />
                        <strong>Republished:</strong>{' '}
                        {republishResult.republished}
                        <br />
                        <strong>Failed:</strong> {republishResult.failed}
                        <br />
                        <strong>Still Valid:</strong>{' '}
                        {republishResult.stillValid}
                        <br />
                        <strong>Duration:</strong>{' '}
                        {republishResult.duration?.totalSeconds.toFixed(2)}s
                      </p>
                    </Message>
                  )}
                </div>
              )}

              {/* Publishing Stats */}
              {publishingStats && (
                <div style={{ marginTop: '1em' }}>
                  {publishingStats.error ? (
                    <Message error>
                      <p>{publishingStats.error}</p>
                    </Message>
                  ) : (
                    <Message>
                      <Message.Header>Publishing Statistics</Message.Header>
                      <p>
                        <strong>Total Published:</strong>{' '}
                        {publishingStats.totalPublishedDescriptors}
                        <br />
                        <strong>Active Publications:</strong>{' '}
                        {publishingStats.activePublications}
                        <br />
                        <strong>Expiring Soon:</strong>{' '}
                        {publishingStats.expiringSoon}
                        <br />
                        <strong>Average TTL:</strong>{' '}
                        {publishingStats.averageTtlHours?.toFixed(1)} hours
                        <br />
                        <strong>Total Storage:</strong>{' '}
                        {(
                          publishingStats.totalStorageBytes /
                          1_024 /
                          1_024
                        )?.toFixed(1)}{' '}
                        MB
                      </p>
                      {publishingStats.publicationsByDomain &&
                        Object.keys(publishingStats.publicationsByDomain)
                          .length > 0 && (
                          <div style={{ marginTop: '0.5em' }}>
                            <strong>By Domain:</strong>
                            {Object.entries(
                              publishingStats.publicationsByDomain,
                            ).map(([domain, count]) => (
                              <Label
                                key={domain}
                                size="tiny"
                                style={{ margin: '0.1em' }}
                              >
                                {domain}: {count}
                              </Label>
                            ))}
                          </div>
                        )}
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Descriptor Retrieval */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="search" />
                Retrieve Content Descriptor
              </Card.Header>
              <Card.Description>
                Retrieve content descriptors from the DHT by ContentID
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Cached single-descriptor retrieval is the default path. Force a
                fresh lookup only when cache state is suspect because it can
                trigger additional DHT traffic.
              </Message>
              <Form>
                <Form.Field>
                  <label>ContentID</label>
                  <Input
                    onChange={(e) => setRetrieveContentId(e.target.value)}
                    placeholder="content:audio:track:mb-12345"
                    value={retrieveContentId}
                  />
                </Form.Field>
                <Button
                  tooltip="Run one manual DHT lookup for this ContentID to inspect its published descriptor. Use the cache-bypass option only when a fresh read is needed."
                  disabled={!retrieveContentId.trim() || retrievingDescriptor}
                  loading={retrievingDescriptor}
                  onClick={handleRetrieveDescriptor}
                  primary
                >
                  Retrieve Descriptor
                </Button>
              </Form>
              <details style={{ marginTop: '1em' }}>
                <summary>Advanced fresh DHT retrieval controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <Checkbox
                      checked={bypassCache}
                      label="Bypass cache (force fresh retrieval)"
                      onChange={(e, { checked }) => setBypassCache(checked)}
                    />
                  </Form.Field>
                </Form>
              </details>

              {retrievalResult && (
                <div style={{ marginTop: '1em' }}>
                  {retrievalResult.error ? (
                    <Message error>
                      <p>{retrievalResult.error}</p>
                    </Message>
                  ) : !retrievalResult.found ? (
                    <Message warning>
                      <p>
                        Content descriptor not found for:{' '}
                        {retrievalResult.contentId || retrieveContentId}
                      </p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>Descriptor Retrieved</Message.Header>
                      <p>
                        <strong>ContentID:</strong>{' '}
                        {retrievalResult.descriptor?.contentId}
                        <br />
                        <strong>From Cache:</strong>{' '}
                        {retrievalResult.fromCache ? 'Yes' : 'No'}
                        <br />
                        <strong>Retrieved:</strong>{' '}
                        {new Date(retrievalResult.retrievedAt).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong>Duration:</strong>{' '}
                        {retrievalResult.retrievalDuration?.totalMilliseconds.toFixed(
                          0,
                        )}
                        ms
                        <br />
                        <strong>Verified:</strong>{' '}
                        {retrievalResult.verification?.isValid ? 'Yes' : 'No'}
                        {asArray(retrievalResult.verification?.warnings).length > 0 && (
                          <span> (with warnings)</span>
                        )}
                      </p>
                      <details>
                        <summary>View Descriptor JSON</summary>
                        <pre
                          style={{
                            fontSize: '0.8em',
                            maxHeight: '200px',
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(retrievalResult.descriptor, null, 2)}
                        </pre>
                      </details>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Batch Retrieval */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="list alternate" />
                Batch Descriptor Retrieval
              </Card.Header>
              <Card.Description>
                Retrieve multiple content descriptors simultaneously
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                Use single-descriptor retrieval first. Batch retrieval can fan
                out across multiple descriptors and is grouped as an advanced
                DHT retrieval operation.
              </Message>
              <details>
                <summary>Advanced batch DHT retrieval controls</summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label>ContentIDs (one per line)</label>
                    <TextArea
                      onChange={(e) =>
                        setBatchRetrieveContentIds(e.target.value)
                      }
                      placeholder="content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;..."
                      rows={6}
                      value={batchRetrieveContentIds}
                    />
                  </Form.Field>
                  <Button
                    tooltip="Run a DHT lookup for each listed ContentID to inspect their descriptors. Keep the batch bounded because every ID adds network traffic."
                    disabled={!batchRetrieveContentIds.trim() || retrievingBatch}
                    loading={retrievingBatch}
                    onClick={handleRetrieveBatch}
                    primary
                  >
                    Retrieve Batch
                  </Button>
                </Form>
              </details>

              {batchRetrievalResult && (
                <div style={{ marginTop: '1em' }}>
                  {batchRetrievalResult.error ? (
                    <Message error>
                      <p>{batchRetrievalResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header>Batch Retrieval Results</Message.Header>
                      <p>
                        <strong>Requested:</strong>{' '}
                        {batchRetrievalResult.requested}
                        <br />
                        <strong>Found:</strong> {batchRetrievalResult.found}
                        <br />
                        <strong>Failed:</strong> {batchRetrievalResult.failed}
                        <br />
                        <strong>Duration:</strong>{' '}
                        {batchRetrievalResult.totalDuration?.totalSeconds.toFixed(
                          2,
                        )}
                        s
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Domain Query */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="filter" />
                Query by Domain
              </Card.Header>
              <Card.Description>
                Query content descriptors by domain and optional type
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label>Domain</label>
                    <Dropdown
                      onChange={(e, { value }) => setQueryDomain(value)}
                      options={[
                        { key: 'audio', text: 'Audio', value: 'audio' },
                        { key: 'video', text: 'Video', value: 'video' },
                        { key: 'image', text: 'Image', value: 'image' },
                        { key: 'text', text: 'Text', value: 'text' },
                        {
                          key: 'application',
                          text: 'Application',
                          value: 'application',
                        },
                      ]}
                      selection
                      value={queryDomain}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Type (optional)</label>
                    <Input
                      onChange={(e) => setQueryType(e.target.value)}
                      placeholder="track, album, movie, etc."
                      value={queryType}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label>Max Results</label>
                    <Input
                      max="1000"
                      min="1"
                      onChange={(e) => setQueryMaxResults(e.target.value)}
                      type="number"
                      value={queryMaxResults}
                    />
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip="Search published descriptors by domain and type, up to the selected result limit. This is a manual DHT query."
                  disabled={!queryDomain.trim() || queryingDescriptors}
                  loading={queryingDescriptors}
                  onClick={handleQueryDescriptors}
                  primary
                >
                  Query Domain
                </Button>
              </Form>

              {queryResult && (
                <div style={{ marginTop: '1em' }}>
                  {queryResult.error ? (
                    <Message error>
                      <p>{queryResult.error}</p>
                    </Message>
                  ) : (
                    <Message>
                      <Message.Header>Query Results</Message.Header>
                      <p>
                        <strong>Domain:</strong> {queryResult.domain}
                        {queryResult.type && (
                          <span>
                            {' '}
                            | <strong>Type:</strong> {queryResult.type}
                          </span>
                        )}
                        <br />
                        <strong>Found:</strong> {queryResult.totalFound}
                        <br />
                        <strong>Query Time:</strong>{' '}
                        {queryResult.queryDuration?.totalMilliseconds.toFixed(
                          0,
                        )}
                        ms
                        <br />
                        <strong>Has More:</strong>{' '}
                        {queryResult.hasMoreResults ? 'Yes' : 'No'}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Descriptor Verification */}
        <Grid.Column width={8}>
          <Card fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="shield" />
                Descriptor Verification
              </Card.Header>
              <Card.Description>
                Verify descriptor signature and freshness
              </Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label>Descriptor JSON</label>
                  <TextArea
                    onChange={(e) => setVerifyDescriptor(e.target.value)}
                    placeholder="Paste descriptor JSON to verify..."
                    rows={8}
                    value={verifyDescriptor}
                  />
                </Form.Field>
                <Button
                  tooltip="Check this descriptor’s signature and validity before importing or trusting its metadata."
                  disabled={!verifyDescriptor.trim() || verifyingDescriptor}
                  loading={verifyingDescriptor}
                  onClick={handleVerifyDescriptor}
                  primary
                >
                  Verify Descriptor
                </Button>
              </Form>

              {descriptorVerificationResult && (
                <div style={{ marginTop: '1em' }}>
                  {descriptorVerificationResult.error ? (
                    <Message error>
                      <p>{descriptorVerificationResult.error}</p>
                    </Message>
                  ) : (
                    <Message
                      success={descriptorVerificationResult.isValid}
                      warning={!descriptorVerificationResult.isValid}
                    >
                      <Message.Header>
                        Verification Result:{' '}
                        {descriptorVerificationResult.isValid
                          ? 'Valid'
                          : 'Invalid'}
                      </Message.Header>
                      <p>
                        <strong>Signature Valid:</strong>{' '}
                        {descriptorVerificationResult.signatureValid
                          ? 'Yes'
                          : 'No'}
                        <br />
                        <strong>Freshness Valid:</strong>{' '}
                        {descriptorVerificationResult.freshnessValid
                          ? 'Yes'
                          : 'No'}
                        <br />
                        <strong>Age:</strong>{' '}
                        {descriptorVerificationResult.age?.totalMinutes.toFixed(
                          1,
                        )}{' '}
                        minutes
                      </p>
                      {asArray(descriptorVerificationResult.warnings).length > 0 && (
                        <div>
                          <strong>Warnings:</strong>
                          <List bulleted>
                            {asArray(descriptorVerificationResult.warnings).map(
                              (warning, index) => (
                                <List.Item key={index}>{warning}</List.Item>
                              ),
                            )}
                          </List>
                        </div>
                      )}
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* MediaCore Statistics */}
        <MediaCoreStats />


        {/* PodCore Operations */}
        {podsEnabled && (
          <MediaCorePods
            isPodWorkflowVisible={isPodWorkflowVisible}
            supportedAlgorithms={supportedAlgorithms}
          />
        )}
      </Grid>
    </div>
  );
};

export default MediaCore;
