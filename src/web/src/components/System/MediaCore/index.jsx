import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";


import { getRegionalLocale } from '../../../lib/regionalFormat';
import * as mediacore from '../../../lib/mediacore';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
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
  useInterfaceLanguage();
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
      setError(getApiErrorMessage(error_, { t: interfaceText }));
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
      setError(interfaceText("Failed to register: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      setResolvedContent({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setValidatedContent({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setDomainResults({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setTraversalResults({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setGraphResults({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setInboundResults({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("No valid audio samples provided"));
      }

      const result = await mediacore.computeAudioHash(
        samples,
        Number.parseInt(sampleRate),
        audioAlgorithm,
      );
      setAudioHashResult(result);
    } catch (error_) {
      setAudioHashResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("No valid pixel data provided"));
      }

      const result = await mediacore.computeImageHash(
        pixels,
        Number.parseInt(imageWidth),
        Number.parseInt(imageHeight),
        imageAlgorithm,
      );
      setImageHashResult(result);
    } catch (error_) {
      setImageHashResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setSimilarityResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setPerceptualSimilarityResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setFindSimilarResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setTextSimilarityResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setExportResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("Invalid JSON format for metadata package"));
      }

      const result = await mediacore.importMetadata(
        packageData,
        conflictStrategy,
        dryRun,
      );
      setImportResult(result);
    } catch (error_) {
      setImportResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("Invalid JSON format for metadata package"));
      }

      const result = await mediacore.analyzeMetadataConflicts(packageData);
      setConflictAnalysis(result);
    } catch (error_) {
      setConflictAnalysis({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setPublishResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setBatchPublishResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("At least one update field is required"));
      }

      const result = await mediacore.updateContentDescriptor(
        updateTargetId.trim(),
        updates,
      );
      setUpdateResult(result);
    } catch (error_) {
      setUpdateResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setRepublishResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setPublishingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setRetrievalResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setBatchRetrievalResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setQueryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        throw new Error(interfaceText("Invalid JSON format for descriptor"));
      }

      const result = await mediacore.verifyContentDescriptor(descriptor);
      setDescriptorVerificationResult(result);
    } catch (error_) {
      setDescriptorVerificationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
          <LocalizedText source={"Loading MediaCore statistics..."} /></Loader>
      </Segment>
    );
  }

  if (error && !stats) {
    return (
      <Message error>
        <Message.Header><LocalizedText source={"Failed to load MediaCore statistics"} /></Message.Header>
        <p>{error}</p>
      </Message>
    );
  }

  return (
    <div>
      <Header as="h2">
        <Icon name="database" />
        <LocalizedText source={"MediaCore ContentID Registry"} /></Header>

      {podsEnabled ? (
        <Segment>
          <Header as="h3">
            <Icon name="sitemap" />
            <LocalizedText source={"Pod Workflow Index"} /></Header>
        <Message warning>
          <LocalizedText source={"Pod workflows mix read-only diagnostics with operations that publish metadata, membership records, messages, opinions, or key material. Use this index to jump to the intended workflow before running an action."} /></Message>
        <Form>
          <Form.Field>
            <label><LocalizedText source={"Workflow focus"} /></label>
            <Dropdown
              aria-label={interfaceText("Pod workflow focus")}
              onChange={(_, { value }) => setPodWorkflowFilter(value)}
              options={podWorkflowFilterOptions}
              selection
              value={podWorkflowFilter}
             {...interfaceTextProps("Pod workflow focus")}/>
          </Form.Field>
        </Form>
        {podWorkflowFilter !== 'all' && (
          <Message
            info
            size="small"
          >
            <Message.Content>
              <Message.Header><LocalizedText source={"Focused pod workflow"} /></Message.Header>
              <LocalizedText
                source={"Showing {workflow}"}
                values={{ workflow: selectedPodWorkflow?.label || 'one pod workflow' }}
              />{' '}
              <LocalizedText source={". Choose \"Show all pod workflows\" or use the reset action to return to the complete MediaCore pod surface."} /><div style={{ marginTop: '0.75em' }}>
                <Button
                  tooltip={interfaceText("Show every Pod workflow card so you can browse the full set of available tasks.")}
                  basic
                  onClick={() => setPodWorkflowFilter('all')}
                  size="tiny"
                >
                  <LocalizedText source={"Show all pod workflows"} /></Button>
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
            <Message info><LocalizedText source={"Checking PodCore availability…"} /></Message>
          )}
        </Segment>
      )}

      <Grid stackable>
        {/* Statistics Overview */}
        <Grid.Column width={16}>
          <Segment>
            <Header as="h3"><LocalizedText source={"Registry Statistics"} /></Header>
            <Statistic.Group size="small">
              <Statistic>
                <Statistic.Value>{stats?.totalMappings || 0}</Statistic.Value>
                <Statistic.Label><LocalizedText source={"Total Mappings"} /></Statistic.Label>
              </Statistic>
              <Statistic>
                <Statistic.Value>{stats?.totalDomains || 0}</Statistic.Value>
                <Statistic.Label><LocalizedText source={"Domains"} /></Statistic.Label>
              </Statistic>
            </Statistic.Group>

            {Object.keys(asObject(stats?.mappingsByDomain)).length > 0 && (
                <div style={{ marginTop: '1em' }}>
                  <Header as="h4"><LocalizedText source={"Mappings by Domain"} /></Header>
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
                <LocalizedText source={"Register ContentID Mapping"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Map an external identifier to an internal ContentID"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Resolve and validate existing identifiers first. Registering a mapping changes the local ContentID registry and is grouped as an advanced operation."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced ContentID registration controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"External ID"} /></label>
                    <Input
                      onChange={(e) => setExternalId(e.target.value)}
                      placeholder={interfaceText("e.g., mb:recording:12345-6789-...")}
                      value={externalId}
                     {...interfaceTextProps("e.g., mb:recording:12345-6789-...")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Content ID"} /></label>
                    <Input
                      onChange={(e) => setDescriptorContentId(e.target.value)}
                      placeholder={interfaceText("e.g., content:mb:recording:12345-6789-...")}
                      value={descriptorContentId}
                     {...interfaceTextProps("e.g., content:mb:recording:12345-6789-...")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Add this external-ID-to-ContentID mapping to the local registry so later lookups can resolve it.")}
                    disabled={
                      !externalId.trim() ||
                      !descriptorContentId.trim() ||
                      registering
                    }
                    loading={registering}
                    onClick={handleRegister}
                    primary
                  >
                    <LocalizedText source={"Register Mapping"} /></Button>
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
                <LocalizedText source={"Resolve External ID"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Find the ContentID for an external identifier"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"External ID to Resolve"} /></label>
                  <Input
                    action={
                      <Button
                        tooltip={interfaceText("Look up this external ID in the local registry to find its associated ContentID.")}
                        disabled={!resolveId.trim() || resolving}
                        loading={resolving}
                        onClick={handleResolve}
                        primary
                      >
                        <LocalizedText source={"Resolve"} /></Button>
                    }
                    onChange={(e) => setResolveId(e.target.value)}
                    placeholder={interfaceText("Enter external ID to resolve...")}
                    value={resolveId}
                   {...interfaceTextProps("Enter external ID to resolve...")}/>
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
                      <Message.Header><LocalizedText source={"Resolved Successfully"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"External ID:"} /></strong>{' '}
                        {resolvedContent.externalId}
                        <br />
                        <strong><LocalizedText source={"Content ID:"} /></strong> {resolvedContent.contentId}
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
                <LocalizedText source={"ContentID Validation"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Validate ContentID format and extract components"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"ContentID to Validate"} /></label>
                  <Input
                    action={
                      <Button
                        tooltip={interfaceText("Check the ContentID format and extract its components before using it in another workflow.")}
                        disabled={!validateContentIdInput.trim() || validating}
                        loading={validating}
                        onClick={handleValidate}
                        primary
                      >
                        <LocalizedText source={"Validate"} /></Button>
                    }
                    onChange={(e) => setValidateContentIdInput(e.target.value)}
                    placeholder={interfaceText("e.g., content:audio:track:mb-12345")}
                    value={validateContentIdInput}
                   {...interfaceTextProps("e.g., content:audio:track:mb-12345")}/>
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
                      <Message.Header><LocalizedText source={"Valid ContentID"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Domain:"} /></strong> {validatedContent.domain}
                        <br />
                        <strong><LocalizedText source={"Type:"} /></strong> {validatedContent.type}
                        <br />
                        <strong>ID:</strong> {validatedContent.id}
                        <br />
                        <strong><LocalizedText source={"Audio:"} /></strong>{' '}
                        {validatedContent.isAudio ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />} |
                        <strong><LocalizedText source={"Video:"} /></strong>{' '}
                        {validatedContent.isVideo ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />} |
                        <strong><LocalizedText source={"Image:"} /></strong>{' '}
                        {validatedContent.isImage ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
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
                <LocalizedText source={"Domain Search"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Find ContentIDs by domain and optional type"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Domain"} /></label>
                    <Input
                      onChange={(e) => setDomain(e.target.value)}
                      placeholder={interfaceText("e.g., audio, video, image")}
                      value={domain}
                     {...interfaceTextProps("e.g., audio, video, image")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Type (optional)"} /></label>
                    <Input
                      onChange={(e) => setType(e.target.value)}
                      placeholder={interfaceText("e.g., track, movie, photo")}
                      value={type}
                     {...interfaceTextProps("e.g., track, movie, photo")}/>
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip={interfaceText("Search the local registry for ContentIDs in this domain and optional type so you can find registered items.")}
                  disabled={!domain.trim() || searchingDomain}
                  loading={searchingDomain}
                  onClick={handleDomainSearch}
                  primary
                >
                  <LocalizedText source={"Search Domain"} /></Button>
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
                          <LocalizedText
                            source="Found {count} content IDs"
                            values={{ count: asArray(domainResults.contentIds).length }}
                          /></strong>
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
              <LocalizedText source={"ContentID Examples"} /></Header>
            <p>
              <LocalizedText source={"Click any example to fill the read-only resolve and validation fields, plus the advanced registration fields."} /></p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5em' }}>
              {Object.entries(contentExamples).map(([domainName, types]) =>
                Object.entries(types).map(([typeName, example]) => (
                  <Button
                    tooltip={interfaceText("Fill the related fields with this sample ID pair so you can try resolve, validation, and registration without typing example values.")}
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
                <LocalizedText source={"IPLD Graph Traversal"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Traverse content relationships following specific link types"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Start ContentID"} /></label>
                    <Input
                      onChange={(e) => setTraverseContentId(e.target.value)}
                      placeholder={interfaceText("e.g., content:audio:track:mb-12345")}
                      value={traverseContentId}
                     {...interfaceTextProps("e.g., content:audio:track:mb-12345")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Link Type"} /></label>
                    <Input
                      onChange={(e) => setTraverseLinkName(e.target.value)}
                      placeholder={interfaceText("e.g., album, artist, artwork")}
                      value={traverseLinkName}
                     {...interfaceTextProps("e.g., album, artist, artwork")}/>
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip={interfaceText("Follow the selected link type from this ContentID to inspect connected content records.")}
                  disabled={
                    !traverseContentId.trim() ||
                    !traverseLinkName.trim() ||
                    traversing
                  }
                  loading={traversing}
                  onClick={handleTraverse}
                  primary
                >
                  <LocalizedText source={"Traverse Graph"} /></Button>
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
                        <strong><LocalizedText source={"Traversal completed:"} /></strong>{' '}
                        {traversalResults.completedTraversal ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                      </p>
                      <p>
                        <strong>
                          <LocalizedText source={"Visited"} />{" "}{asArray(traversalResults.visitedNodes).length}{' '}
                          <LocalizedText source={"nodes"} /></strong>
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
                                  {node.outgoingLinks?.length || 0} <LocalizedText source={"outgoing links"} /></List.Description>
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
                <LocalizedText source={"Content Graph"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Get the complete relationship graph for a ContentID"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"ContentID"} /></label>
                  <Input
                    action={
                      <Button
                        tooltip={interfaceText("Load the known relationship graph for this ContentID so you can review its linked records.")}
                        disabled={!graphContentId.trim() || gettingGraph}
                        loading={gettingGraph}
                        onClick={handleGetGraph}
                        primary
                      >
                        <LocalizedText source={"Get Graph"} /></Button>
                    }
                    onChange={(e) => setGraphContentId(e.target.value)}
                    placeholder={interfaceText("Enter ContentID to get its graph")}
                    value={graphContentId}
                   {...interfaceTextProps("Enter ContentID to get its graph")}/>
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
                        <strong><LocalizedText source={"Root:"} /></strong> {graphResults.rootContentId}
                      </p>
                      <p>
                        <strong><LocalizedText source={"Nodes:"} /></strong>{' '}
                        {asArray(graphResults.nodes).length}
                      </p>
                      <p>
                        <strong><LocalizedText source={"Paths:"} /></strong>{' '}
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
                                  {node.outgoingLinks?.length || 0} <LocalizedText source={"outgoing,"} />{' '}
                                  {node.incomingLinks?.length || 0} <LocalizedText source={"incoming"} /></List.Description>
                              </List.Content>
                            </List.Item>
                          ))}
                          {graphResults.nodes.length > 5 && (
                            <List.Item>
                              <List.Content>
                                <em>
                                  <LocalizedText source={"... and"} />{" "}{graphResults.nodes.length - 5} <LocalizedText source={"more nodes"} /></em>
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
                <LocalizedText source={"Inbound Links"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Find all content that links to a specific ContentID"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"Target ContentID"} /></label>
                  <Input
                    action={
                      <Button
                        tooltip={interfaceText("Find records that link to this ContentID so you can see where the item is referenced.")}
                        disabled={!inboundTargetId.trim() || findingInbound}
                        loading={findingInbound}
                        onClick={handleFindInbound}
                        primary
                      >
                        <LocalizedText source={"Find Links"} /></Button>
                    }
                    onChange={(e) => setInboundTargetId(e.target.value)}
                    placeholder={interfaceText("Find content that links to this ID")}
                    value={inboundTargetId}
                   {...interfaceTextProps("Find content that links to this ID")}/>
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
                          <LocalizedText
                            source="Found {count} inbound links"
                            values={{ count: asArray(inboundResults.inboundLinks).length }}
                          /></strong>
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
                <LocalizedText source={"Audio Perceptual Hash"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Compute perceptual hash for audio similarity detection"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Similarity review and hashing statistics are the default path. Raw sample hashing is a diagnostic operation for prepared sample arrays."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced raw audio hash controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label><LocalizedText source={"Algorithm"} /></label>
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
                      <label><LocalizedText source={"Sample Rate (Hz)"} /></label>
                      <Input
                        onChange={(e) => setSampleRate(e.target.value)}
                        type="number"
                        value={sampleRate}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label><LocalizedText source={"Audio Samples (comma-separated floats)"} /></label>
                    <TextArea
                      onChange={(e) => setAudioSamples(e.target.value)}
                      placeholder={interfaceText("0.1, -0.2, 0.3, ... (normalized -1.0 to 1.0)")}
                      rows={3}
                      value={audioSamples}
                     {...interfaceTextProps("0.1, -0.2, 0.3, ... (normalized -1.0 to 1.0)")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Compute the selected audio fingerprint from the supplied sample data so you can compare or identify audio.")}
                    disabled={!audioSamples.trim() || computingAudioHash}
                    loading={computingAudioHash}
                    onClick={handleComputeAudioHash}
                    primary
                  >
                    <LocalizedText source={"Compute Audio Hash"} /></Button>
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
                      <Message.Header><LocalizedText source={"Audio Hash Computed"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Algorithm:"} /></strong> {audioHashResult.algorithm}
                        <br />
                        <strong><LocalizedText source={"Hex Hash:"} /></strong> {audioHashResult.hex}
                        <br />
                        <strong><LocalizedText source={"Sample Count:"} /></strong>{' '}
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
                <LocalizedText source={"Image Perceptual Hash"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Compute perceptual hash for image similarity detection"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Similarity review and hashing statistics are the default path. Raw pixel hashing is a diagnostic operation for prepared image buffers."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced raw image hash controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label><LocalizedText source={"Algorithm"} /></label>
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
                      <label><LocalizedText source={"Dimensions"} /></label>
                      <Input
                        onChange={(e) => {
                          const [w, h] = e.target.value
                            .split('x')
                            .map((s) => Number.parseInt(s.trim()));
                          if (!isNaN(w)) setImageWidth(w);
                          if (!isNaN(h)) setImageHeight(h);
                        }}
                        placeholder={interfaceText("Width x Height")}
                        value={`${imageWidth}x${imageHeight}`}
                       {...interfaceTextProps("Width x Height")}/>
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label><LocalizedText source={"Pixel Data (comma-separated bytes 0-255)"} /></label>
                    <TextArea
                      onChange={(e) => setImagePixels(e.target.value)}
                      placeholder={interfaceText("255, 128, 64, ... (RGBA pixel data)")}
                      rows={3}
                      value={imagePixels}
                     {...interfaceTextProps("255, 128, 64, ... (RGBA pixel data)")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Compute the selected image fingerprint from the supplied pixel data so you can compare images.")}
                    disabled={!imagePixels.trim() || computingImageHash}
                    loading={computingImageHash}
                    onClick={handleComputeImageHash}
                    primary
                  >
                    <LocalizedText source={"Compute Image Hash"} /></Button>
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
                      <Message.Header><LocalizedText source={"Image Hash Computed"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Algorithm:"} /></strong> {imageHashResult.algorithm}
                        <br />
                        <strong><LocalizedText source={"Hex Hash:"} /></strong> {imageHashResult.hex}
                        <br />
                        <strong><LocalizedText source={"Dimensions:"} /></strong> {imageWidth} × {imageHeight}
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
                <LocalizedText source={"Hash Similarity Analysis"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Compare perceptual hashes to determine content similarity"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Hash A (hex)"} /></label>
                    <Input
                      onChange={(e) => setHashA(e.target.value)}
                      placeholder={interfaceText("First hash value (hexadecimal)")}
                      value={hashA}
                     {...interfaceTextProps("First hash value (hexadecimal)")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Hash B (hex)"} /></label>
                    <Input
                      onChange={(e) => setHashB(e.target.value)}
                      placeholder={interfaceText("Second hash value (hexadecimal)")}
                      value={hashB}
                     {...interfaceTextProps("Second hash value (hexadecimal)")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Similarity Threshold"} /></label>
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
                  tooltip={interfaceText("Compare these two hashes against the chosen threshold to see whether they are a likely match.")}
                  disabled={
                    !hashA.trim() || !hashB.trim() || computingSimilarity
                  }
                  loading={computingSimilarity}
                  onClick={handleComputeSimilarity}
                  primary
                >
                  <LocalizedText source={"Analyze Similarity"} /></Button>
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
                        <LocalizedText source={"Similarity Analysis Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Hamming Distance:"} /></strong>{' '}
                        {similarityResult.hammingDistance} <LocalizedText source={"bits"} /><br />
                        <strong><LocalizedText source={"Similarity Score:"} /></strong>{' '}
                        {(similarityResult.similarity * 100).toFixed(1)}%<br />
                        <strong><LocalizedText source={"Are Similar:"} /></strong>{' '}
                        {similarityResult.areSimilar ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />} <LocalizedText source={"(threshold:"} />{' '}
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
                <LocalizedText source={"Fuzzy Content Matching"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Find similar content using perceptual hashes and text analysis"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Pairwise perceptual and text similarity are the default review paths. Candidate search can scan registry entries, so it is grouped as an advanced similarity search."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced similarity candidate search controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"Target ContentID"} /></label>
                    <Input
                      onChange={(e) => setFindSimilarContentId(e.target.value)}
                      placeholder={interfaceText("ContentID to find matches for")}
                      value={findSimilarContentId}
                     {...interfaceTextProps("ContentID to find matches for")}/>
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label><LocalizedText source={"Min Confidence"} /></label>
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
                      <label><LocalizedText source={"Max Results"} /></label>
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
                    tooltip={interfaceText("Search for content similar to this ID using the selected confidence and result limits.")}
                    disabled={
                      !findSimilarContentId.trim() || findingSimilarContent
                    }
                    loading={findingSimilarContent}
                    onClick={handleFindSimilarContent}
                    primary
                  >
                    <LocalizedText source={"Find Similar Content"} /></Button>
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
                        <strong><LocalizedText source={"Target:"} /></strong>{' '}
                        {findSimilarResult.targetContentId}
                      </p>
                      <p>
                        <strong>
                          <LocalizedText source={"Searched"} />{" "}{findSimilarResult.totalCandidates}{' '}
                          <LocalizedText source={"candidates"} /></strong>
                      </p>
                      <p>
                        <strong>
                          <LocalizedText
                            source="Found {count} matches"
                            values={{ count: asArray(findSimilarResult.matches).length }}
                          /></strong>
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
                                  <LocalizedText source={"Confidence:"} />{' '}
                                  {(match.confidence * 100).toFixed(1)}<LocalizedText source={"% | Reason:"} />{" "}{match.reason}
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
                <LocalizedText source={"Perceptual Similarity"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Compare perceptual similarity between two ContentIDs"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"ContentID A"} /></label>
                    <Input
                      onChange={(e) => setPerceptualContentIdA(e.target.value)}
                      placeholder={interfaceText("First ContentID")}
                      value={perceptualContentIdA}
                     {...interfaceTextProps("First ContentID")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"ContentID B"} /></label>
                    <Input
                      onChange={(e) => setPerceptualContentIdB(e.target.value)}
                      placeholder={interfaceText("Second ContentID")}
                      value={perceptualContentIdB}
                     {...interfaceTextProps("Second ContentID")}/>
                  </Form.Field>
                </Form.Group>
                <Form.Field>
                  <label><LocalizedText source={"Similarity Threshold"} /></label>
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
                  tooltip={interfaceText("Compare these content IDs using their perceptual signatures and threshold to find similar media.")}
                  disabled={
                    !perceptualContentIdA.trim() ||
                    !perceptualContentIdB.trim() ||
                    computingPerceptualSimilarity
                  }
                  loading={computingPerceptualSimilarity}
                  onClick={handleComputePerceptualSimilarity}
                  primary
                >
                  <LocalizedText source={"Compute Similarity"} /></Button>
              </Form>

              {perceptualSimilarityResult && (
                <div style={{ marginTop: '1em' }}>
                  {perceptualSimilarityResult.error ? (
                    <Message error>
                      <p>{perceptualSimilarityResult.error}</p>
                    </Message>
                  ) : (
                    <Message info>
                      <Message.Header><LocalizedText source={"Similarity Analysis"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Content A:"} /></strong>{' '}
                        {perceptualSimilarityResult.contentIdA}
                        <br />
                        <strong><LocalizedText source={"Content B:"} /></strong>{' '}
                        {perceptualSimilarityResult.contentIdB}
                        <br />
                        <strong><LocalizedText source={"Similarity:"} /></strong>{' '}
                        {(perceptualSimilarityResult.similarity * 100).toFixed(
                          1,
                        )}
                        %<br />
                        <strong><LocalizedText source={"Are Similar:"} /></strong>{' '}
                        {perceptualSimilarityResult.isSimilar ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}{' '}
                        <LocalizedText source={"(threshold:"} />{' '}
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
                <LocalizedText source={"Text Similarity Analysis"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Compare text strings using Levenshtein distance and phonetic matching"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Text A"} /></label>
                    <Input
                      onChange={(e) => setTextSimilarityA(e.target.value)}
                      placeholder={interfaceText("First text string")}
                      value={textSimilarityA}
                     {...interfaceTextProps("First text string")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Text B"} /></label>
                    <Input
                      onChange={(e) => setTextSimilarityB(e.target.value)}
                      placeholder={interfaceText("Second text string")}
                      value={textSimilarityB}
                     {...interfaceTextProps("Second text string")}/>
                  </Form.Field>
                </Form.Group>
                <Button
                  tooltip={interfaceText("Compare the supplied text values to measure how closely their content matches.")}
                  disabled={
                    !textSimilarityA.trim() ||
                    !textSimilarityB.trim() ||
                    computingTextSimilarity
                  }
                  loading={computingTextSimilarity}
                  onClick={handleComputeTextSimilarity}
                  primary
                >
                  <LocalizedText source={"Analyze Text Similarity"} /></Button>
              </Form>

              {textSimilarityResult && (
                <div style={{ marginTop: '1em' }}>
                  {textSimilarityResult.error ? (
                    <Message error>
                      <p>{textSimilarityResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header><LocalizedText source={"Text Similarity Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Text A:"} /></strong> "{textSimilarityResult.textA}"
                        <br />
                        <strong><LocalizedText source={"Text B:"} /></strong> "{textSimilarityResult.textB}"
                        <br />
                        <strong><LocalizedText source={"Levenshtein Similarity:"} /></strong>{' '}
                        {(
                          textSimilarityResult.levenshteinSimilarity * 100
                        ).toFixed(1)}
                        %<br />
                        <strong><LocalizedText source={"Phonetic Similarity:"} /></strong>{' '}
                        {(
                          textSimilarityResult.phoneticSimilarity * 100
                        ).toFixed(1)}
                        %<br />
                        <strong><LocalizedText source={"Combined Similarity:"} /></strong>{' '}
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
                <LocalizedText source={"Export Metadata"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Export metadata for ContentIDs to a portable package"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"ContentIDs (one per line)"} /></label>
                  <TextArea
                    onChange={(e) => setExportContentIds(e.target.value)}
                    placeholder={interfaceText("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}
                    rows={4}
                    value={exportContentIds}
                   {...interfaceTextProps("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}/>
                </Form.Field>
                <Form.Field>
                  <Checkbox
                    checked={includeLinks}
                    label={interfaceText("Include IPLD links")}
                    onChange={(e, { checked }) => setIncludeLinks(checked)}
                   {...interfaceTextProps("Include IPLD links")}/>
                </Form.Field>
                <Button
                  tooltip={interfaceText("Build a metadata package for the selected ContentIDs and optional links so you can back it up or review it. This does not publish the package.")}
                  disabled={!exportContentIds.trim() || exportingMetadata}
                  loading={exportingMetadata}
                  onClick={handleExportMetadata}
                  primary
                >
                  <LocalizedText source={"Export Metadata"} /></Button>
              </Form>

              {exportResult && (
                <div style={{ marginTop: '1em' }}>
                  {exportResult.error ? (
                    <Message error>
                      <p>{exportResult.error}</p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header><LocalizedText source={"Export Successful"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Version:"} /></strong> {exportResult.version}
                        <br />
                        <strong><LocalizedText source={"Entries:"} /></strong>{' '}
                        {exportResult.metadata?.totalEntries || 0}
                        <br />
                        <strong><LocalizedText source={"Links:"} /></strong>{' '}
                        {exportResult.metadata?.totalLinks || 0}
                        <br />
                        <strong><LocalizedText source={"Checksum:"} /></strong>{' '}
                        {exportResult.metadata?.checksum?.slice(0, 16)}...
                      </p>
                      <details>
                        <summary><LocalizedText source={"View Package JSON"} /></summary>
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
                <LocalizedText source={"Import Metadata"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Import metadata from a portable package with conflict resolution"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"Conflict Resolution Strategy"} /></label>
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
                    label={interfaceText("Dry run (preview changes without applying)")}
                    onChange={(e, { checked }) => setDryRun(checked)}
                   {...interfaceTextProps("Dry run (preview changes without applying)")}/>
                </Form.Field>
                <Button
                  tooltip={interfaceText("Preview conflicts between this package and the local registry without importing changes; use this before choosing an import strategy.")}
                  disabled={!importPackage.trim() || analyzingConflicts}
                  loading={analyzingConflicts}
                  onClick={handleAnalyzeConflicts}
                  secondary
                >
                  <LocalizedText source={"Analyze Conflicts"} /></Button>
              </Form>

              {/* Import Package Input */}
              <Form style={{ marginTop: '1em' }}>
                <Form.Field>
                  <label><LocalizedText source={"Metadata Package (JSON)"} /></label>
                  <TextArea
                    onChange={(e) => setImportPackage(e.target.value)}
                    placeholder={interfaceText("Paste exported metadata package JSON here...")}
                    rows={6}
                    value={importPackage}
                   {...interfaceTextProps("Paste exported metadata package JSON here...")}/>
                </Form.Field>
              </Form>
              <details style={{ marginTop: '1em' }}>
                <summary><LocalizedText source={"Advanced metadata import controls"} /></summary>
                <Message warning size="small">
                  <LocalizedText source={"Importing applies package metadata to the local registry. Run conflict analysis first, then import only when the selected strategy is intentional."} /></Message>
                <Button
                  tooltip={
                    dryRun
                      ? interfaceText("Preview the changes this package would make to the local registry without applying them.")
                      : interfaceText("Import this package and apply its changes to the local registry. Review the conflict strategy before applying.")
                  }
                  disabled={!importPackage.trim() || importingMetadata}
                  loading={importingMetadata}
                  onClick={handleImportMetadata}
                  primary
                >
                  <LocalizedText source={"Import Metadata"} /></Button>
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
                      <Message.Header><LocalizedText source={"Conflict Analysis"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Total Entries:"} /></strong>{' '}
                        {conflictAnalysis.totalEntries}
                        <br />
                        <strong><LocalizedText source={"Conflicting:"} /></strong>{' '}
                        {conflictAnalysis.conflictingEntries}
                        <br />
                        <strong><LocalizedText source={"Clean:"} /></strong> {conflictAnalysis.cleanEntries}
                        <br />
                        <strong><LocalizedText source={"Recommended Strategy:"} /></strong>{' '}
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
                        <LocalizedText source={"Import"} />{' '}
                        {importResult.success
                          ? <LocalizedText source={"Successful"} />
                          : <LocalizedText source={"Completed with Issues"} />}
                      </Message.Header>
                      <p>
                        <strong><LocalizedText source={"Processed:"} /></strong>{' '}
                        {importResult.entriesProcessed}
                        <br />
                        <strong><LocalizedText source={"Imported:"} /></strong>{' '}
                        {importResult.entriesImported}
                        <br />
                        <strong><LocalizedText source={"Skipped:"} /></strong> {importResult.entriesSkipped}
                        <br />
                        <strong><LocalizedText source={"Conflicts Resolved:"} /></strong>{' '}
                        {importResult.conflictsResolved}
                        <br />
                        <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                        {importResult.duration?.TotalSeconds.toFixed(2)}<LocalizedText source={"s"} /></p>
                      {asArray(importResult.errors).length > 0 && (
                        <details>
                          <summary>
                            <LocalizedText source={"Errors ("} />{asArray(importResult.errors).length})
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
                <LocalizedText source={"Publish Content Descriptor"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Publish a content descriptor to the DHT with versioning support"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Descriptor publishing changes DHT-visible metadata. Retrieval and stats are the default workflow; publishing controls are grouped as advanced operations."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced descriptor publishing controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"ContentID"} /></label>
                    <Input
                      onChange={(e) => setPublishContentId(e.target.value)}
                      placeholder="content:audio:track:mb-12345"
                      value={publishContentId}
                    />
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label><LocalizedText source={"Codec"} /></label>
                      <Input
                        onChange={(e) => setPublishCodec(e.target.value)}
                        placeholder={interfaceText("mp3, flac, etc.")}
                        value={publishCodec}
                       {...interfaceTextProps("mp3, flac, etc.")}/>
                    </Form.Field>
                    <Form.Field>
                      <label><LocalizedText source={"Size (bytes)"} /></label>
                      <Input
                        onChange={(e) => setPublishSize(e.target.value)}
                        type="number"
                        value={publishSize}
                      />
                    </Form.Field>
                  </Form.Group>
                  <Button
                    tooltip={interfaceText("Publish a descriptor for this ContentID to the DHT so other participants can discover it. Review the supplied metadata before publishing.")}
                    disabled={!publishContentId.trim() || publishingDescriptor}
                    loading={publishingDescriptor}
                    onClick={handlePublishDescriptor}
                    primary
                  >
                    <LocalizedText source={"Publish Descriptor"} /></Button>
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
                      <Message.Header><LocalizedText source={"Published Successfully"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"ContentID:"} /></strong> {publishResult.contentId}
                        <br />
                        <strong><LocalizedText source={"Version:"} /></strong> {publishResult.version}
                        <br />
                        <strong>TTL:</strong> {publishResult.ttl?.totalMinutes}{' '}
                        <LocalizedText source={"minutes"} /><br />
                        <strong><LocalizedText source={"Was Updated:"} /></strong>{' '}
                        {publishResult.wasUpdated ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
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
                <LocalizedText source={"Batch Publish Descriptors"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Publish multiple content descriptors simultaneously"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Batch publishing can expose multiple descriptors at once. Keep retrieval and stats as the default path; use this only after checking each ContentID."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced batch publishing controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"ContentIDs (one per line)"} /></label>
                    <TextArea
                      onChange={(e) => setBatchContentIds(e.target.value)}
                      placeholder={interfaceText("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}
                      rows={6}
                      value={batchContentIds}
                     {...interfaceTextProps("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Publish one descriptor for each listed ContentID to the DHT. Review the full list because each entry creates a network write.")}
                    disabled={!batchContentIds.trim() || publishingBatch}
                    loading={publishingBatch}
                    onClick={handlePublishBatch}
                    primary
                  >
                    <LocalizedText source={"Publish Batch"} /></Button>
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
                      <Message.Header><LocalizedText source={"Batch Publish Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Total Requested:"} /></strong>{' '}
                        {batchPublishResult.totalRequested}
                        <br />
                        <strong><LocalizedText source={"Successfully Published:"} /></strong>{' '}
                        {batchPublishResult.successfullyPublished}
                        <br />
                        <strong><LocalizedText source={"Failed:"} /></strong>{' '}
                        {batchPublishResult.failedToPublish}
                        <br />
                        <strong><LocalizedText source={"Skipped:"} /></strong> {batchPublishResult.skipped}
                        <br />
                        <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                        {batchPublishResult.totalDuration?.totalSeconds.toFixed(
                          2,
                        )}
                        <LocalizedText source={"s"} /></p>
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
                <LocalizedText source={"Update Descriptor"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Update metadata for an existing published descriptor"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Descriptor updates alter an existing publication. Retrieve and verify the descriptor first, then use this advanced path only for deliberate metadata corrections."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced descriptor update controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"Target ContentID"} /></label>
                    <Input
                      onChange={(e) => setUpdateTargetId(e.target.value)}
                      placeholder={interfaceText("ContentID to update")}
                      value={updateTargetId}
                     {...interfaceTextProps("ContentID to update")}/>
                  </Form.Field>
                  <Form.Group widths="equal">
                    <Form.Field>
                      <label><LocalizedText source={"New Codec"} /></label>
                      <Input
                        onChange={(e) => setUpdateCodec(e.target.value)}
                        placeholder={interfaceText("Leave empty to keep current")}
                        value={updateCodec}
                       {...interfaceTextProps("Leave empty to keep current")}/>
                    </Form.Field>
                    <Form.Field>
                      <label><LocalizedText source={"New Size (bytes)"} /></label>
                      <Input
                        onChange={(e) => setUpdateSize(e.target.value)}
                        placeholder={interfaceText("Leave empty to keep current")}
                        value={updateSize}
                       {...interfaceTextProps("Leave empty to keep current")}/>
                    </Form.Field>
                  </Form.Group>
                  <Form.Field>
                    <label><LocalizedText source={"New Confidence (0.0-1.0)"} /></label>
                    <Input
                      onChange={(e) => setUpdateConfidence(e.target.value)}
                      placeholder={interfaceText("Leave empty to keep current")}
                      value={updateConfidence}
                     {...interfaceTextProps("Leave empty to keep current")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Update the selected descriptor in the DHT so participants see the new values. Verify the ContentID and fields before applying.")}
                    disabled={!updateTargetId.trim() || updatingDescriptor}
                    loading={updatingDescriptor}
                    onClick={handleUpdateDescriptor}
                    primary
                  >
                    <LocalizedText source={"Update Descriptor"} /></Button>
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
                      <Message.Header><LocalizedText source={"Update Successful"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"ContentID:"} /></strong> {updateResult.contentId}
                        <br />
                        <strong><LocalizedText source={"Version:"} /></strong> {updateResult.previousVersion}{' '}
                        → {updateResult.newVersion}
                        <br />
                        <strong><LocalizedText source={"Updates Applied:"} /></strong>{' '}
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
                <LocalizedText source={"Publishing Management"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Manage published descriptors and monitor publishing status"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Button.Group fluid>
                <Button
                  tooltip={interfaceText("Load local descriptor publication counts and timings so you can review recent publishing activity.")}
                  disabled={loadingStats}
                  loading={loadingStats}
                  onClick={handleLoadPublishingStats}
                >
                  <LocalizedText source={"Load Stats"} /></Button>
              </Button.Group>
              <details style={{ marginTop: '1em' }}>
                <summary><LocalizedText source={"Advanced descriptor republishing controls"} /></summary>
                <Message warning size="small">
                  <LocalizedText source={"Republish only after reviewing publishing statistics. This refreshes DHT-visible descriptor records that are close to expiry."} /></Message>
                <Button
                  tooltip={interfaceText("Republish descriptors nearing expiry so they remain discoverable. This performs DHT writes; run it when renewal is needed.")}
                  disabled={republishing}
                  loading={republishing}
                  onClick={handleRepublishExpiring}
                >
                  <LocalizedText source={"Republish Expiring"} /></Button>
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
                      <Message.Header><LocalizedText source={"Republish Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Checked:"} /></strong> {republishResult.totalChecked}
                        <br />
                        <strong><LocalizedText source={"Republished:"} /></strong>{' '}
                        {republishResult.republished}
                        <br />
                        <strong><LocalizedText source={"Failed:"} /></strong> {republishResult.failed}
                        <br />
                        <strong><LocalizedText source={"Still Valid:"} /></strong>{' '}
                        {republishResult.stillValid}
                        <br />
                        <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                        {republishResult.duration?.totalSeconds.toFixed(2)}<LocalizedText source={"s"} /></p>
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
                      <Message.Header><LocalizedText source={"Publishing Statistics"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Total Published:"} /></strong>{' '}
                        {publishingStats.totalPublishedDescriptors}
                        <br />
                        <strong><LocalizedText source={"Active Publications:"} /></strong>{' '}
                        {publishingStats.activePublications}
                        <br />
                        <strong><LocalizedText source={"Expiring Soon:"} /></strong>{' '}
                        {publishingStats.expiringSoon}
                        <br />
                        <strong><LocalizedText source={"Average TTL:"} /></strong>{' '}
                        {publishingStats.averageTtlHours?.toFixed(1)} <LocalizedText source={"hours"} /><br />
                        <strong><LocalizedText source={"Total Storage:"} /></strong>{' '}
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
                            <strong><LocalizedText source={"By Domain:"} /></strong>
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
                <LocalizedText source={"Retrieve Content Descriptor"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Retrieve content descriptors from the DHT by ContentID"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Cached single-descriptor retrieval is the default path. Force a fresh lookup only when cache state is suspect because it can trigger additional DHT traffic."} /></Message>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"ContentID"} /></label>
                  <Input
                    onChange={(e) => setRetrieveContentId(e.target.value)}
                    placeholder="content:audio:track:mb-12345"
                    value={retrieveContentId}
                  />
                </Form.Field>
                <Button
                  tooltip={interfaceText("Run one manual DHT lookup for this ContentID to inspect its published descriptor. Use the cache-bypass option only when a fresh read is needed.")}
                  disabled={!retrieveContentId.trim() || retrievingDescriptor}
                  loading={retrievingDescriptor}
                  onClick={handleRetrieveDescriptor}
                  primary
                >
                  <LocalizedText source={"Retrieve Descriptor"} /></Button>
              </Form>
              <details style={{ marginTop: '1em' }}>
                <summary><LocalizedText source={"Advanced fresh DHT retrieval controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <Checkbox
                      checked={bypassCache}
                      label={interfaceText("Bypass cache (force fresh retrieval)")}
                      onChange={(e, { checked }) => setBypassCache(checked)}
                     {...interfaceTextProps("Bypass cache (force fresh retrieval)")}/>
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
                        <LocalizedText source={"Content descriptor not found for:"} />{' '}
                        {retrievalResult.contentId || retrieveContentId}
                      </p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header><LocalizedText source={"Descriptor Retrieved"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"ContentID:"} /></strong>{' '}
                        {retrievalResult.descriptor?.contentId}
                        <br />
                        <strong><LocalizedText source={"From Cache:"} /></strong>{' '}
                        {retrievalResult.fromCache ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                        <br />
                        <strong><LocalizedText source={"Retrieved:"} /></strong>{' '}
                        {new Date(retrievalResult.retrievedAt).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                        {retrievalResult.retrievalDuration?.totalMilliseconds.toFixed(
                          0,
                        )}
                        <LocalizedText source={"ms"} /><br />
                        <strong><LocalizedText source={"Verified:"} /></strong>{' '}
                        {retrievalResult.verification?.isValid ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                        {asArray(retrievalResult.verification?.warnings).length > 0 && (
                          <span> <LocalizedText source={"(with warnings)"} /></span>
                        )}
                      </p>
                      <details>
                        <summary><LocalizedText source={"View Descriptor JSON"} /></summary>
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
                <LocalizedText source={"Batch Descriptor Retrieval"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Retrieve multiple content descriptors simultaneously"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Message info size="small">
                <LocalizedText source={"Use single-descriptor retrieval first. Batch retrieval can fan out across multiple descriptors and is grouped as an advanced DHT retrieval operation."} /></Message>
              <details>
                <summary><LocalizedText source={"Advanced batch DHT retrieval controls"} /></summary>
                <Form style={{ marginTop: '1em' }}>
                  <Form.Field>
                    <label><LocalizedText source={"ContentIDs (one per line)"} /></label>
                    <TextArea
                      onChange={(e) =>
                        setBatchRetrieveContentIds(e.target.value)
                      }
                      placeholder={interfaceText("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}
                      rows={6}
                      value={batchRetrieveContentIds}
                     {...interfaceTextProps("content:audio:track:mb-12345&#10;content:video:movie:imdb-tt0111161&#10;...")}/>
                  </Form.Field>
                  <Button
                    tooltip={interfaceText("Run a DHT lookup for each listed ContentID to inspect their descriptors. Keep the batch bounded because every ID adds network traffic.")}
                    disabled={!batchRetrieveContentIds.trim() || retrievingBatch}
                    loading={retrievingBatch}
                    onClick={handleRetrieveBatch}
                    primary
                  >
                    <LocalizedText source={"Retrieve Batch"} /></Button>
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
                      <Message.Header><LocalizedText source={"Batch Retrieval Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Requested:"} /></strong>{' '}
                        {batchRetrievalResult.requested}
                        <br />
                        <strong><LocalizedText source={"Found:"} /></strong> {batchRetrievalResult.found}
                        <br />
                        <strong><LocalizedText source={"Failed:"} /></strong> {batchRetrievalResult.failed}
                        <br />
                        <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                        {batchRetrievalResult.totalDuration?.totalSeconds.toFixed(
                          2,
                        )}
                        <LocalizedText source={"s"} /></p>
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
                <LocalizedText source={"Query by Domain"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Query content descriptors by domain and optional type"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Group widths="equal">
                  <Form.Field>
                    <label><LocalizedText source={"Domain"} /></label>
                    <Dropdown
                      onChange={(e, { value }) => setQueryDomain(value)}
                      options={[
                        { key: 'audio', text: interfaceText("Audio"), value: 'audio' },
                        { key: 'video', text: interfaceText("Video"), value: 'video' },
                        { key: 'image', text: interfaceText("Image"), value: 'image' },
                        { key: 'text', text: interfaceText("Text"), value: 'text' },
                        {
                          key: 'application',
                          text: interfaceText("Application"),
                          value: 'application',
                        },
                      ]}
                      selection
                      value={queryDomain}
                    />
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Type (optional)"} /></label>
                    <Input
                      onChange={(e) => setQueryType(e.target.value)}
                      placeholder={interfaceText("track, album, movie, etc.")}
                      value={queryType}
                     {...interfaceTextProps("track, album, movie, etc.")}/>
                  </Form.Field>
                  <Form.Field>
                    <label><LocalizedText source={"Max Results"} /></label>
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
                  tooltip={interfaceText("Search published descriptors by domain and type, up to the selected result limit. This is a manual DHT query.")}
                  disabled={!queryDomain.trim() || queryingDescriptors}
                  loading={queryingDescriptors}
                  onClick={handleQueryDescriptors}
                  primary
                >
                  <LocalizedText source={"Query Domain"} /></Button>
              </Form>

              {queryResult && (
                <div style={{ marginTop: '1em' }}>
                  {queryResult.error ? (
                    <Message error>
                      <p>{queryResult.error}</p>
                    </Message>
                  ) : (
                    <Message>
                      <Message.Header><LocalizedText source={"Query Results"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Domain:"} /></strong> {queryResult.domain}
                        {queryResult.type && (
                          <span>
                            {' '}
                            | <strong><LocalizedText source={"Type:"} /></strong> {queryResult.type}
                          </span>
                        )}
                        <br />
                        <strong><LocalizedText source={"Found:"} /></strong> {queryResult.totalFound}
                        <br />
                        <strong><LocalizedText source={"Query Time:"} /></strong>{' '}
                        {queryResult.queryDuration?.totalMilliseconds.toFixed(
                          0,
                        )}
                        <LocalizedText source={"ms"} /><br />
                        <strong><LocalizedText source={"Has More:"} /></strong>{' '}
                        {queryResult.hasMoreResults ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
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
                <LocalizedText source={"Descriptor Verification"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Verify descriptor signature and freshness"} /></Card.Description>
            </Card.Content>
            <Card.Content>
              <Form>
                <Form.Field>
                  <label><LocalizedText source={"Descriptor JSON"} /></label>
                  <TextArea
                    onChange={(e) => setVerifyDescriptor(e.target.value)}
                    placeholder={interfaceText("Paste descriptor JSON to verify...")}
                    rows={8}
                    value={verifyDescriptor}
                   {...interfaceTextProps("Paste descriptor JSON to verify...")}/>
                </Form.Field>
                <Button
                  tooltip={interfaceText("Check this descriptor’s signature and validity before importing or trusting its metadata.")}
                  disabled={!verifyDescriptor.trim() || verifyingDescriptor}
                  loading={verifyingDescriptor}
                  onClick={handleVerifyDescriptor}
                  primary
                >
                  <LocalizedText source={"Verify Descriptor"} /></Button>
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
                        <LocalizedText source={"Verification Result:"} />{' '}
                        {descriptorVerificationResult.isValid
                          ? <LocalizedText source={"Valid"} />
                          : <LocalizedText source={"Invalid"} />}
                      </Message.Header>
                      <p>
                        <strong><LocalizedText source={"Signature Valid:"} /></strong>{' '}
                        {descriptorVerificationResult.signatureValid
                          ? <LocalizedText source={"Yes"} />
                          : <LocalizedText source={"No"} />}
                        <br />
                        <strong><LocalizedText source={"Freshness Valid:"} /></strong>{' '}
                        {descriptorVerificationResult.freshnessValid
                          ? <LocalizedText source={"Yes"} />
                          : <LocalizedText source={"No"} />}
                        <br />
                        <strong><LocalizedText source={"Age:"} /></strong>{' '}
                        {descriptorVerificationResult.age?.totalMinutes.toFixed(
                          1,
                        )}{' '}
                        <LocalizedText source={"minutes"} /></p>
                      {asArray(descriptorVerificationResult.warnings).length > 0 && (
                        <div>
                          <strong><LocalizedText source={"Warnings:"} /></strong>
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
