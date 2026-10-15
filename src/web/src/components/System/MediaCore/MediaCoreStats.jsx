import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';


import { getRegionalLocale } from '../../../lib/regionalFormat';
import * as mediacore from '../../../lib/mediacore';
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { TooltipButton } from '../../Shared';
import {
  Card,
  Grid,
  Header,
  Icon,
  Label,
  Message,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);

const MediaCoreStats = () => {
  const [retrievalStats, setRetrievalStats] = useState(null);
  const [loadingRetrievalStats, setLoadingRetrievalStats] = useState(false);
  const [mediaCoreDashboard, setMediaCoreDashboard] = useState(null);
  const [contentRegistryStats, setContentRegistryStats] = useState(null);
  const [descriptorStats, setDescriptorStats] = useState(null);
  const [fuzzyMatchingStats, setFuzzyMatchingStats] = useState(null);
  const [ipldMappingStats, setIpldMappingStats] = useState(null);
  const [perceptualHashingStats, setPerceptualHashingStats] = useState(null);
  const [metadataPortabilityStats, setMetadataPortabilityStats] = useState(null);
  const [contentPublishingStats, setContentPublishingStats] = useState(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [loadingRegistryStats, setLoadingRegistryStats] = useState(false);
  const [loadingDescriptorStats, setLoadingDescriptorStats] = useState(false);
  const [loadingFuzzyStats, setLoadingFuzzyStats] = useState(false);
  const [loadingIpldStats, setLoadingIpldStats] = useState(false);
  const [loadingPerceptualStats, setLoadingPerceptualStats] = useState(false);
  const [loadingPortabilityStats, setLoadingPortabilityStats] = useState(false);
  const [loadingPublishingStats, setLoadingPublishingStats] = useState(false);

  const handleLoadRetrievalStats = async () => {
    try {
      setLoadingRetrievalStats(true);
      setRetrievalStats(null);
      const result = await mediacore.getRetrievalStats();
      setRetrievalStats(result);
    } catch (error_) {
      setRetrievalStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingRetrievalStats(false);
    }
  };

  const handleClearRetrievalCache = async () => {
    try {
      const result = await mediacore.clearRetrievalCache();
      await handleLoadRetrievalStats();
      toast.success(
        interfaceText("Cache cleared: {entriesCleared} entries, {bytesFreed} bytes freed", { "entriesCleared": (result.entriesCleared), "bytesFreed": (result.bytesFreed) }),
      );
    } catch (error_) {
      toast.error(interfaceText("Failed to clear cache: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  const handleLoadMediaCoreDashboard = async () => {
    try {
      setLoadingDashboard(true);
      setMediaCoreDashboard(null);
      const result = await mediacore.getMediaCoreDashboard();
      setMediaCoreDashboard(result);
    } catch (error_) {
      setMediaCoreDashboard({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingDashboard(false);
    }
  };

  const handleResetMediaCoreStats = async () => {
    if (
      !confirm(
        'Are you sure you want to reset all MediaCore statistics? This cannot be undone.',
      )
    ) {
      return;
    }

    try {
      await mediacore.resetMediaCoreStats();
      setMediaCoreDashboard(null);
      setContentRegistryStats(null);
      setDescriptorStats(null);
      setFuzzyMatchingStats(null);
      setIpldMappingStats(null);
      setPerceptualHashingStats(null);
      setMetadataPortabilityStats(null);
      setContentPublishingStats(null);
      toast.success(interfaceText("MediaCore statistics have been reset"));
    } catch (error_) {
      toast.error(interfaceText("Failed to reset stats: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  const handleLoadContentRegistryStats = async () => {
    try {
      setLoadingRegistryStats(true);
      setContentRegistryStats(null);
      const result = await mediacore.getContentRegistryStats();
      setContentRegistryStats(result);
    } catch (error_) {
      setContentRegistryStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingRegistryStats(false);
    }
  };

  const handleLoadDescriptorStats = async () => {
    try {
      setLoadingDescriptorStats(true);
      setDescriptorStats(null);
      const result = await mediacore.getDescriptorStats();
      setDescriptorStats(result);
    } catch (error_) {
      setDescriptorStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingDescriptorStats(false);
    }
  };

  const handleLoadFuzzyMatchingStats = async () => {
    try {
      setLoadingFuzzyStats(true);
      setFuzzyMatchingStats(null);
      const result = await mediacore.getFuzzyMatchingStats();
      setFuzzyMatchingStats(result);
    } catch (error_) {
      setFuzzyMatchingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingFuzzyStats(false);
    }
  };

  const handleLoadIpldMappingStats = async () => {
    try {
      setLoadingIpldStats(true);
      setIpldMappingStats(null);
      const result = await mediacore.getIpldMappingStats();
      setIpldMappingStats(result);
    } catch (error_) {
      setIpldMappingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingIpldStats(false);
    }
  };

  const handleLoadPerceptualHashingStats = async () => {
    try {
      setLoadingPerceptualStats(true);
      setPerceptualHashingStats(null);
      const result = await mediacore.getPerceptualHashingStats();
      setPerceptualHashingStats(result);
    } catch (error_) {
      setPerceptualHashingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingPerceptualStats(false);
    }
  };

  const handleLoadMetadataPortabilityStats = async () => {
    try {
      setLoadingPortabilityStats(true);
      setMetadataPortabilityStats(null);
      const result = await mediacore.getMetadataPortabilityStats();
      setMetadataPortabilityStats(result);
    } catch (error_) {
      setMetadataPortabilityStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingPortabilityStats(false);
    }
  };

  const handleLoadContentPublishingStats = async () => {
    try {
      setLoadingPublishingStats(true);
      setContentPublishingStats(null);
      const result = await mediacore.getContentPublishingStats();
      setContentPublishingStats(result);
    } catch (error_) {
      setContentPublishingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingPublishingStats(false);
    }
  };

  return (
    <>
      <Grid.Column width={16}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="chart line" />
              <LocalizedText source={"Retrieval Management"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Monitor retrieval performance and manage cache"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingRetrievalStats}
              fluid
              loading={loadingRetrievalStats}
              onClick={handleLoadRetrievalStats}
              tooltip="Load descriptor retrieval performance and cache statistics."
            >
              <LocalizedText source={"Load Stats"} /></TooltipButton>
            <details style={{ marginTop: '1em' }}>
              <summary><LocalizedText source={"Advanced retrieval cache controls"} /></summary>
              <Message
                size="small"
                warning
              >
                <LocalizedText source={"Clear the retrieval cache only after reviewing stats. This removes cached descriptor lookup results and can increase follow-up DHT retrieval traffic."} /></Message>
              <TooltipButton
                onClick={handleClearRetrievalCache}
                tooltip="Remove cached descriptor lookups. Later DHT retrievals may generate more peer traffic."
              >
                <LocalizedText source={"Clear Cache"} /></TooltipButton>
            </details>

            {retrievalStats && (
              <div style={{ marginTop: '1em' }}>
                {retrievalStats.error ? (
                  <Message error>
                    <p>{retrievalStats.error}</p>
                  </Message>
                ) : (
                  <Message>
                    <Message.Header><LocalizedText source={"Retrieval Statistics"} /></Message.Header>
                    <p>
                      <strong><LocalizedText source={"Total Retrievals:"} /></strong>{' '}
                      {retrievalStats.totalRetrievals}
                      <br />
                      <strong><LocalizedText source={"Cache Hits:"} /></strong> {retrievalStats.cacheHits}
                      <br />
                      <strong><LocalizedText source={"Cache Misses:"} /></strong>{' '}
                      {retrievalStats.cacheMisses}
                      <br />
                      <strong><LocalizedText source={"Hit Ratio:"} /></strong>{' '}
                      {(retrievalStats.cacheHitRatio * 100).toFixed(1)}%
                      <br />
                      <strong><LocalizedText source={"Avg Retrieval Time:"} /></strong>{' '}
                      {retrievalStats.averageRetrievalTime?.totalMilliseconds.toFixed(
                        0,
                      )}{' '}
                      <LocalizedText source={"ms"} /><br />
                      <strong><LocalizedText source={"Active Cache Entries:"} /></strong>{' '}
                      {retrievalStats.activeCacheEntries}
                      <br />
                      <strong><LocalizedText source={"Cache Size:"} /></strong>{' '}
                      {(retrievalStats.cacheSizeBytes / 1_024).toFixed(1)} KB
                    </p>
                  </Message>
                )}
              </div>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={16}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="chart bar" />
              <LocalizedText source={"MediaCore Statistics Dashboard"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Comprehensive overview of all MediaCore system performance and usage metrics"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <div className="ui fluid buttons">
              <TooltipButton
                disabled={loadingDashboard}
                loading={loadingDashboard}
                onClick={handleLoadMediaCoreDashboard}
                primary
                tooltip="Load overall MediaCore performance and usage metrics."
              >
                <LocalizedText source={"Load Full Dashboard"} /></TooltipButton>
            </div>
            <details style={{ marginTop: '1em' }}>
              <summary><LocalizedText source={"Advanced dashboard reset controls"} /></summary>
              <Message
                size="small"
                warning
              >
                <LocalizedText source={"Resetting clears accumulated MediaCore statistics. Load and review the dashboard first so operational context is not lost accidentally."} /></Message>
              <TooltipButton
                color="red"
                onClick={handleResetMediaCoreStats}
                tooltip="Clear all accumulated MediaCore statistics after confirming."
              >
                <LocalizedText source={"Reset All Stats"} /></TooltipButton>
            </details>

            {mediaCoreDashboard && !mediaCoreDashboard.error && (
              <div style={{ marginTop: '1em' }}>
                <Message info>
                  <Message.Header><LocalizedText source={"System Overview"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Uptime:"} /></strong>{' '}
                    {mediaCoreDashboard.uptime
                      ? `${Math.floor(mediaCoreDashboard.uptime.totalHours)}h ${mediaCoreDashboard.uptime.minutes}m`
                      : interfaceText('N/A')}
                    <br />
                    <strong><LocalizedText source={"Last Updated:"} /></strong>{' '}
                    {mediaCoreDashboard.timestamp
                      ? new Date(
                          mediaCoreDashboard.timestamp,
                        ).toLocaleString(getRegionalLocale())
                      : interfaceText('N/A')}
                  </p>
                </Message>

                {mediaCoreDashboard.systemResources && (
                  <Message>
                    <Message.Header><LocalizedText source={"System Resources"} /></Message.Header>
                    <p>
                      <strong><LocalizedText source={"Working Set:"} /></strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources.workingSetBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong><LocalizedText source={"Private Memory:"} /></strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources
                          .privateMemoryBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong><LocalizedText source={"GC Memory:"} /></strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources
                          .gcTotalMemoryBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong><LocalizedText source={"Thread Count:"} /></strong>{' '}
                      {mediaCoreDashboard.systemResources.threadCount}
                    </p>
                  </Message>
                )}
              </div>
            )}

            {mediaCoreDashboard?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p><LocalizedText source={"Failed to load dashboard:"} />{" "}{mediaCoreDashboard.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="database" />
              <LocalizedText source={"Content Registry"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Content ID mappings and domain statistics"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingRegistryStats}
              fluid
              loading={loadingRegistryStats}
              onClick={handleLoadContentRegistryStats}
              tooltip="Load Content Registry mapping totals and domain statistics."
            >
              <LocalizedText source={"Load Registry Stats"} /></TooltipButton>

            {contentRegistryStats && !contentRegistryStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message success>
                  <Message.Header><LocalizedText source={"Registry Overview"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Mappings:"} /></strong>{' '}
                    {contentRegistryStats.totalMappings}
                    <br />
                    <strong><LocalizedText source={"Domains:"} /></strong>{' '}
                    {contentRegistryStats.totalDomains}
                    <br />
                    <strong><LocalizedText source={"Avg Mappings/Domain:"} /></strong>{' '}
                    {contentRegistryStats.averageMappingsPerDomain.toFixed(1)}
                  </p>
                  {contentRegistryStats.mappingsByDomain &&
                    Object.keys(contentRegistryStats.mappingsByDomain)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong><LocalizedText source={"Mappings by Domain:"} /></strong>
                        {Object.entries(
                          contentRegistryStats.mappingsByDomain,
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
              </div>
            )}

            {contentRegistryStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{contentRegistryStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="search" />
              <LocalizedText source={"Descriptor Retrieval"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Cache performance and retrieval statistics"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingDescriptorStats}
              fluid
              loading={loadingDescriptorStats}
              onClick={handleLoadDescriptorStats}
              tooltip="Load descriptor retrieval and cache performance metrics."
            >
              <LocalizedText source={"Load Descriptor Stats"} /></TooltipButton>

            {descriptorStats && !descriptorStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Cache Performance"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Retrievals:"} /></strong>{' '}
                    {descriptorStats.totalRetrievals}
                    <br />
                    <strong><LocalizedText source={"Cache Hits:"} /></strong> {descriptorStats.cacheHits}
                    <br />
                    <strong><LocalizedText source={"Cache Misses:"} /></strong>{' '}
                    {descriptorStats.cacheMisses}
                    <br />
                    <strong><LocalizedText source={"Hit Ratio:"} /></strong>{' '}
                    {(descriptorStats.cacheHitRatio * 100).toFixed(1)}%
                    <br />
                    <strong><LocalizedText source={"Avg Retrieval Time:"} /></strong>{' '}
                    {descriptorStats.averageRetrievalTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /><br />
                    <strong><LocalizedText source={"Active Cache Entries:"} /></strong>{' '}
                    {descriptorStats.activeCacheEntries}
                    <br />
                    <strong><LocalizedText source={"Cache Size:"} /></strong>{' '}
                    {(descriptorStats.cacheSizeBytes / 1_024).toFixed(1)} KB
                  </p>
                </Message>
              </div>
            )}

            {descriptorStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{descriptorStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="magic" />
              <LocalizedText source={"Fuzzy Matching"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Similarity detection and accuracy metrics"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingFuzzyStats}
              fluid
              loading={loadingFuzzyStats}
              onClick={handleLoadFuzzyMatchingStats}
              tooltip="Load fuzzy-match totals, success rate, and accuracy metrics."
            >
              <LocalizedText source={"Load Fuzzy Stats"} /></TooltipButton>

            {fuzzyMatchingStats && !fuzzyMatchingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Matching Performance"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Matches:"} /></strong>{' '}
                    {fuzzyMatchingStats.totalMatches}
                    <br />
                    <strong><LocalizedText source={"Success Rate:"} /></strong>{' '}
                    {(fuzzyMatchingStats.successRate * 100).toFixed(1)}%
                    <br />
                    <strong><LocalizedText source={"Avg Confidence:"} /></strong>{' '}
                    {(fuzzyMatchingStats.averageConfidenceScore * 100).toFixed(1)}
                    %
                    <br />
                    <strong><LocalizedText source={"Avg Match Time:"} /></strong>{' '}
                    {fuzzyMatchingStats.averageMatchingTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /></p>
                  {fuzzyMatchingStats.accuracyByAlgorithm &&
                    Object.keys(fuzzyMatchingStats.accuracyByAlgorithm)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong><LocalizedText source={"Algorithm Accuracy:"} /></strong>
                        {Object.entries(
                          fuzzyMatchingStats.accuracyByAlgorithm,
                        ).map(([algorithm, stats]) => (
                          <div
                            key={algorithm}
                            style={{ margin: '0.2em 0' }}
                          >
                            <small>
                              {algorithm}<LocalizedText source={": F1="} />{stats.f1Score.toFixed(2)}<LocalizedText source={", Precision="} />{stats.precision.toFixed(2)}
                            </small>
                          </div>
                        ))}
                      </div>
                    )}
                </Message>
              </div>
            )}

            {fuzzyMatchingStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{fuzzyMatchingStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="hashtag" />
              <LocalizedText source={"Perceptual Hashing"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Hash computation performance and accuracy"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPerceptualStats}
              fluid
              loading={loadingPerceptualStats}
              onClick={handleLoadPerceptualHashingStats}
              tooltip="Load perceptual-hash computation and accuracy metrics."
            >
              <LocalizedText source={"Load Hashing Stats"} /></TooltipButton>

            {perceptualHashingStats && !perceptualHashingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Hashing Performance"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Hashes:"} /></strong>{' '}
                    {perceptualHashingStats.totalHashesComputed}
                    <br />
                    <strong><LocalizedText source={"Avg Computation Time:"} /></strong>{' '}
                    {perceptualHashingStats.averageComputationTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /><br />
                    <strong><LocalizedText source={"Overall Accuracy:"} /></strong>{' '}
                    {(perceptualHashingStats.overallAccuracy * 100).toFixed(1)}%
                    <br />
                    <strong><LocalizedText source={"Duplicates Detected:"} /></strong>{' '}
                    {perceptualHashingStats.duplicateHashesDetected}
                  </p>
                  {perceptualHashingStats.statsByAlgorithm &&
                    Object.keys(perceptualHashingStats.statsByAlgorithm)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong><LocalizedText source={"Algorithm Breakdown:"} /></strong>
                        {Object.entries(
                          perceptualHashingStats.statsByAlgorithm,
                        ).map(([algorithm, stats]) => (
                          <div
                            key={algorithm}
                            style={{ margin: '0.2em 0' }}
                          >
                            <small>
                              {algorithm}: {stats.hashesComputed} <LocalizedText source={"hashes,"} />{' '}
                              {stats.averageTime.totalMilliseconds.toFixed(0)}<LocalizedText source={"ms avg,"} />{" "}{stats.accuracy.toFixed(2)} <LocalizedText source={"accuracy"} /></small>
                          </div>
                        ))}
                      </div>
                    )}
                </Message>
              </div>
            )}

            {perceptualHashingStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{perceptualHashingStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="sitemap" />
              <LocalizedText source={"IPLD Mapping"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Graph structure and link statistics"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingIpldStats}
              fluid
              loading={loadingIpldStats}
              onClick={handleLoadIpldMappingStats}
              tooltip="Load IPLD node, link, and mapping statistics."
            >
              <LocalizedText source={"Load IPLD Stats"} /></TooltipButton>

            {ipldMappingStats && !ipldMappingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Graph Statistics"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Links:"} /></strong> {ipldMappingStats.totalLinks}
                    <br />
                    <strong><LocalizedText source={"Total Nodes:"} /></strong> {ipldMappingStats.totalNodes}
                    <br />
                    <strong><LocalizedText source={"Total Graphs:"} /></strong> {ipldMappingStats.totalGraphs}
                    <br />
                    <strong><LocalizedText source={"Connectivity Ratio:"} /></strong>{' '}
                    {(ipldMappingStats.graphConnectivityRatio * 100).toFixed(1)}
                    %
                    <br />
                    <strong><LocalizedText source={"Broken Links:"} /></strong>{' '}
                    {ipldMappingStats.brokenLinksDetected}
                    <br />
                    <strong><LocalizedText source={"Avg Traversal Time:"} /></strong>{' '}
                    {ipldMappingStats.averageTraversalTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /></p>
                </Message>
              </div>
            )}

            {ipldMappingStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{ipldMappingStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={8}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="exchange" />
              <LocalizedText source={"Metadata Portability"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"Export/import operations and conflict resolution"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPortabilityStats}
              fluid
              loading={loadingPortabilityStats}
              onClick={handleLoadMetadataPortabilityStats}
              tooltip="Load metadata export, import, and conflict-resolution metrics."
            >
              <LocalizedText source={"Load Portability Stats"} /></TooltipButton>

            {metadataPortabilityStats && !metadataPortabilityStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Portability Metrics"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Exports:"} /></strong>{' '}
                    {metadataPortabilityStats.totalExports}
                    <br />
                    <strong><LocalizedText source={"Total Imports:"} /></strong>{' '}
                    {metadataPortabilityStats.totalImports}
                    <br />
                    <strong><LocalizedText source={"Import Success Rate:"} /></strong>{' '}
                    {(metadataPortabilityStats.importSuccessRate * 100).toFixed(
                      1,
                    )}
                    %
                    <br />
                    <strong><LocalizedText source={"Data Transferred:"} /></strong>{' '}
                    {(metadataPortabilityStats.totalDataTransferred / 1_024).toFixed(
                      1,
                    )}{' '}
                    KB
                    <br />
                    <strong><LocalizedText source={"Avg Export Time:"} /></strong>{' '}
                    {metadataPortabilityStats.averageExportTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /><br />
                    <strong><LocalizedText source={"Avg Import Time:"} /></strong>{' '}
                    {metadataPortabilityStats.averageImportTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /></p>
                </Message>
              </div>
            )}

            {metadataPortabilityStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{metadataPortabilityStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>

      <Grid.Column width={16}>
        <Card fluid>
          <Card.Content>
            <Card.Header>
              <Icon name="cloud upload" />
              <LocalizedText source={"Content Publishing"} /></Card.Header>
            <Card.Description>
              <LocalizedText source={"DHT publishing performance and publication management"} /></Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPublishingStats}
              fluid
              loading={loadingPublishingStats}
              onClick={handleLoadContentPublishingStats}
              tooltip="Load Content Publishing and DHT publication performance metrics."
            >
              <LocalizedText source={"Load Publishing Stats"} /></TooltipButton>

            {contentPublishingStats && !contentPublishingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header><LocalizedText source={"Publishing Overview"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Published:"} /></strong>{' '}
                    {contentPublishingStats.totalPublished}
                    <br />
                    <strong><LocalizedText source={"Active Publications:"} /></strong>{' '}
                    {contentPublishingStats.activePublications}
                    <br />
                    <strong><LocalizedText source={"Expired Publications:"} /></strong>{' '}
                    {contentPublishingStats.expiredPublications}
                    <br />
                    <strong><LocalizedText source={"Success Rate:"} /></strong>{' '}
                    {(contentPublishingStats.publicationSuccessRate * 100).toFixed(
                      1,
                    )}
                    %
                    <br />
                    <strong><LocalizedText source={"Republished:"} /></strong>{' '}
                    {contentPublishingStats.republishedDescriptors}
                    <br />
                    <strong><LocalizedText source={"Failed:"} /></strong>{' '}
                    {contentPublishingStats.failedPublications}
                    <br />
                    <strong><LocalizedText source={"Avg Publish Time:"} /></strong>{' '}
                    {contentPublishingStats.averagePublishTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    <LocalizedText source={"ms"} /></p>
                </Message>
              </div>
            )}

            {contentPublishingStats?.error && (
              <Message
                error
                style={{ marginTop: '1em' }}
              >
                <p>{contentPublishingStats.error}</p>
              </Message>
            )}
          </Card.Content>
        </Card>
      </Grid.Column>
    </>
  );
};

export default MediaCoreStats;
