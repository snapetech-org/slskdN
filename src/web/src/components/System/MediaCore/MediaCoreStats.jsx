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
      setRetrievalStats({ error: error_.message });
    } finally {
      setLoadingRetrievalStats(false);
    }
  };

  const handleClearRetrievalCache = async () => {
    try {
      const result = await mediacore.clearRetrievalCache();
      await handleLoadRetrievalStats();
      toast.success(
        `Cache cleared: ${result.entriesCleared} entries, ${result.bytesFreed} bytes freed`,
      );
    } catch (error_) {
      toast.error(`Failed to clear cache: ${error_.message}`);
    }
  };

  const handleLoadMediaCoreDashboard = async () => {
    try {
      setLoadingDashboard(true);
      setMediaCoreDashboard(null);
      const result = await mediacore.getMediaCoreDashboard();
      setMediaCoreDashboard(result);
    } catch (error_) {
      setMediaCoreDashboard({ error: error_.message });
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
      toast.success('MediaCore statistics have been reset');
    } catch (error_) {
      toast.error(`Failed to reset stats: ${error_.message}`);
    }
  };

  const handleLoadContentRegistryStats = async () => {
    try {
      setLoadingRegistryStats(true);
      setContentRegistryStats(null);
      const result = await mediacore.getContentRegistryStats();
      setContentRegistryStats(result);
    } catch (error_) {
      setContentRegistryStats({ error: error_.message });
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
      setDescriptorStats({ error: error_.message });
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
      setFuzzyMatchingStats({ error: error_.message });
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
      setIpldMappingStats({ error: error_.message });
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
      setPerceptualHashingStats({ error: error_.message });
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
      setMetadataPortabilityStats({ error: error_.message });
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
      setContentPublishingStats({ error: error_.message });
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
              Retrieval Management
            </Card.Header>
            <Card.Description>
              Monitor retrieval performance and manage cache
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingRetrievalStats}
              fluid
              loading={loadingRetrievalStats}
              onClick={handleLoadRetrievalStats}
              tooltip="Load descriptor retrieval performance and cache statistics."
            >
              Load Stats
            </TooltipButton>
            <details style={{ marginTop: '1em' }}>
              <summary>Advanced retrieval cache controls</summary>
              <Message
                size="small"
                warning
              >
                Clear the retrieval cache only after reviewing stats. This
                removes cached descriptor lookup results and can increase
                follow-up DHT retrieval traffic.
              </Message>
              <TooltipButton
                onClick={handleClearRetrievalCache}
                tooltip="Remove cached descriptor lookups. Later DHT retrievals may generate more peer traffic."
              >
                Clear Cache
              </TooltipButton>
            </details>

            {retrievalStats && (
              <div style={{ marginTop: '1em' }}>
                {retrievalStats.error ? (
                  <Message error>
                    <p>{retrievalStats.error}</p>
                  </Message>
                ) : (
                  <Message>
                    <Message.Header>Retrieval Statistics</Message.Header>
                    <p>
                      <strong>Total Retrievals:</strong>{' '}
                      {retrievalStats.totalRetrievals}
                      <br />
                      <strong>Cache Hits:</strong> {retrievalStats.cacheHits}
                      <br />
                      <strong>Cache Misses:</strong>{' '}
                      {retrievalStats.cacheMisses}
                      <br />
                      <strong>Hit Ratio:</strong>{' '}
                      {(retrievalStats.cacheHitRatio * 100).toFixed(1)}%
                      <br />
                      <strong>Avg Retrieval Time:</strong>{' '}
                      {retrievalStats.averageRetrievalTime?.totalMilliseconds.toFixed(
                        0,
                      )}{' '}
                      ms
                      <br />
                      <strong>Active Cache Entries:</strong>{' '}
                      {retrievalStats.activeCacheEntries}
                      <br />
                      <strong>Cache Size:</strong>{' '}
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
              MediaCore Statistics Dashboard
            </Card.Header>
            <Card.Description>
              Comprehensive overview of all MediaCore system performance and
              usage metrics
            </Card.Description>
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
                Load Full Dashboard
              </TooltipButton>
            </div>
            <details style={{ marginTop: '1em' }}>
              <summary>Advanced dashboard reset controls</summary>
              <Message
                size="small"
                warning
              >
                Resetting clears accumulated MediaCore statistics. Load and
                review the dashboard first so operational context is not lost
                accidentally.
              </Message>
              <TooltipButton
                color="red"
                onClick={handleResetMediaCoreStats}
                tooltip="Clear all accumulated MediaCore statistics after confirming."
              >
                Reset All Stats
              </TooltipButton>
            </details>

            {mediaCoreDashboard && !mediaCoreDashboard.error && (
              <div style={{ marginTop: '1em' }}>
                <Message info>
                  <Message.Header>System Overview</Message.Header>
                  <p>
                    <strong>Uptime:</strong>{' '}
                    {mediaCoreDashboard.uptime
                      ? `${Math.floor(mediaCoreDashboard.uptime.totalHours)}h ${mediaCoreDashboard.uptime.minutes}m`
                      : 'N/A'}
                    <br />
                    <strong>Last Updated:</strong>{' '}
                    {mediaCoreDashboard.timestamp
                      ? new Date(
                          mediaCoreDashboard.timestamp,
                        ).toLocaleString(getRegionalLocale())
                      : 'N/A'}
                  </p>
                </Message>

                {mediaCoreDashboard.systemResources && (
                  <Message>
                    <Message.Header>System Resources</Message.Header>
                    <p>
                      <strong>Working Set:</strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources.workingSetBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong>Private Memory:</strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources
                          .privateMemoryBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong>GC Memory:</strong>{' '}
                      {(
                        mediaCoreDashboard.systemResources
                          .gcTotalMemoryBytes /
                        1_024 /
                        1_024
                      ).toFixed(1)}{' '}
                      MB
                      <br />
                      <strong>Thread Count:</strong>{' '}
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
                <p>Failed to load dashboard: {mediaCoreDashboard.error}</p>
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
              Content Registry
            </Card.Header>
            <Card.Description>
              Content ID mappings and domain statistics
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingRegistryStats}
              fluid
              loading={loadingRegistryStats}
              onClick={handleLoadContentRegistryStats}
              tooltip="Load Content Registry mapping totals and domain statistics."
            >
              Load Registry Stats
            </TooltipButton>

            {contentRegistryStats && !contentRegistryStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message success>
                  <Message.Header>Registry Overview</Message.Header>
                  <p>
                    <strong>Total Mappings:</strong>{' '}
                    {contentRegistryStats.totalMappings}
                    <br />
                    <strong>Domains:</strong>{' '}
                    {contentRegistryStats.totalDomains}
                    <br />
                    <strong>Avg Mappings/Domain:</strong>{' '}
                    {contentRegistryStats.averageMappingsPerDomain.toFixed(1)}
                  </p>
                  {contentRegistryStats.mappingsByDomain &&
                    Object.keys(contentRegistryStats.mappingsByDomain)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong>Mappings by Domain:</strong>
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
              Descriptor Retrieval
            </Card.Header>
            <Card.Description>
              Cache performance and retrieval statistics
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingDescriptorStats}
              fluid
              loading={loadingDescriptorStats}
              onClick={handleLoadDescriptorStats}
              tooltip="Load descriptor retrieval and cache performance metrics."
            >
              Load Descriptor Stats
            </TooltipButton>

            {descriptorStats && !descriptorStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Cache Performance</Message.Header>
                  <p>
                    <strong>Total Retrievals:</strong>{' '}
                    {descriptorStats.totalRetrievals}
                    <br />
                    <strong>Cache Hits:</strong> {descriptorStats.cacheHits}
                    <br />
                    <strong>Cache Misses:</strong>{' '}
                    {descriptorStats.cacheMisses}
                    <br />
                    <strong>Hit Ratio:</strong>{' '}
                    {(descriptorStats.cacheHitRatio * 100).toFixed(1)}%
                    <br />
                    <strong>Avg Retrieval Time:</strong>{' '}
                    {descriptorStats.averageRetrievalTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                    <br />
                    <strong>Active Cache Entries:</strong>{' '}
                    {descriptorStats.activeCacheEntries}
                    <br />
                    <strong>Cache Size:</strong>{' '}
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
              Fuzzy Matching
            </Card.Header>
            <Card.Description>
              Similarity detection and accuracy metrics
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingFuzzyStats}
              fluid
              loading={loadingFuzzyStats}
              onClick={handleLoadFuzzyMatchingStats}
              tooltip="Load fuzzy-match totals, success rate, and accuracy metrics."
            >
              Load Fuzzy Stats
            </TooltipButton>

            {fuzzyMatchingStats && !fuzzyMatchingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Matching Performance</Message.Header>
                  <p>
                    <strong>Total Matches:</strong>{' '}
                    {fuzzyMatchingStats.totalMatches}
                    <br />
                    <strong>Success Rate:</strong>{' '}
                    {(fuzzyMatchingStats.successRate * 100).toFixed(1)}%
                    <br />
                    <strong>Avg Confidence:</strong>{' '}
                    {(fuzzyMatchingStats.averageConfidenceScore * 100).toFixed(1)}
                    %
                    <br />
                    <strong>Avg Match Time:</strong>{' '}
                    {fuzzyMatchingStats.averageMatchingTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                  </p>
                  {fuzzyMatchingStats.accuracyByAlgorithm &&
                    Object.keys(fuzzyMatchingStats.accuracyByAlgorithm)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong>Algorithm Accuracy:</strong>
                        {Object.entries(
                          fuzzyMatchingStats.accuracyByAlgorithm,
                        ).map(([algorithm, stats]) => (
                          <div
                            key={algorithm}
                            style={{ margin: '0.2em 0' }}
                          >
                            <small>
                              {algorithm}: F1={stats.f1Score.toFixed(2)},
                              Precision={stats.precision.toFixed(2)}
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
              Perceptual Hashing
            </Card.Header>
            <Card.Description>
              Hash computation performance and accuracy
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPerceptualStats}
              fluid
              loading={loadingPerceptualStats}
              onClick={handleLoadPerceptualHashingStats}
              tooltip="Load perceptual-hash computation and accuracy metrics."
            >
              Load Hashing Stats
            </TooltipButton>

            {perceptualHashingStats && !perceptualHashingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Hashing Performance</Message.Header>
                  <p>
                    <strong>Total Hashes:</strong>{' '}
                    {perceptualHashingStats.totalHashesComputed}
                    <br />
                    <strong>Avg Computation Time:</strong>{' '}
                    {perceptualHashingStats.averageComputationTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                    <br />
                    <strong>Overall Accuracy:</strong>{' '}
                    {(perceptualHashingStats.overallAccuracy * 100).toFixed(1)}%
                    <br />
                    <strong>Duplicates Detected:</strong>{' '}
                    {perceptualHashingStats.duplicateHashesDetected}
                  </p>
                  {perceptualHashingStats.statsByAlgorithm &&
                    Object.keys(perceptualHashingStats.statsByAlgorithm)
                      .length > 0 && (
                      <div style={{ marginTop: '0.5em' }}>
                        <strong>Algorithm Breakdown:</strong>
                        {Object.entries(
                          perceptualHashingStats.statsByAlgorithm,
                        ).map(([algorithm, stats]) => (
                          <div
                            key={algorithm}
                            style={{ margin: '0.2em 0' }}
                          >
                            <small>
                              {algorithm}: {stats.hashesComputed} hashes,{' '}
                              {stats.averageTime.totalMilliseconds.toFixed(0)}ms
                              avg, {stats.accuracy.toFixed(2)} accuracy
                            </small>
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
              IPLD Mapping
            </Card.Header>
            <Card.Description>
              Graph structure and link statistics
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingIpldStats}
              fluid
              loading={loadingIpldStats}
              onClick={handleLoadIpldMappingStats}
              tooltip="Load IPLD node, link, and mapping statistics."
            >
              Load IPLD Stats
            </TooltipButton>

            {ipldMappingStats && !ipldMappingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Graph Statistics</Message.Header>
                  <p>
                    <strong>Total Links:</strong> {ipldMappingStats.totalLinks}
                    <br />
                    <strong>Total Nodes:</strong> {ipldMappingStats.totalNodes}
                    <br />
                    <strong>Total Graphs:</strong> {ipldMappingStats.totalGraphs}
                    <br />
                    <strong>Connectivity Ratio:</strong>{' '}
                    {(ipldMappingStats.graphConnectivityRatio * 100).toFixed(1)}
                    %
                    <br />
                    <strong>Broken Links:</strong>{' '}
                    {ipldMappingStats.brokenLinksDetected}
                    <br />
                    <strong>Avg Traversal Time:</strong>{' '}
                    {ipldMappingStats.averageTraversalTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                  </p>
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
              Metadata Portability
            </Card.Header>
            <Card.Description>
              Export/import operations and conflict resolution
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPortabilityStats}
              fluid
              loading={loadingPortabilityStats}
              onClick={handleLoadMetadataPortabilityStats}
              tooltip="Load metadata export, import, and conflict-resolution metrics."
            >
              Load Portability Stats
            </TooltipButton>

            {metadataPortabilityStats && !metadataPortabilityStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Portability Metrics</Message.Header>
                  <p>
                    <strong>Total Exports:</strong>{' '}
                    {metadataPortabilityStats.totalExports}
                    <br />
                    <strong>Total Imports:</strong>{' '}
                    {metadataPortabilityStats.totalImports}
                    <br />
                    <strong>Import Success Rate:</strong>{' '}
                    {(metadataPortabilityStats.importSuccessRate * 100).toFixed(
                      1,
                    )}
                    %
                    <br />
                    <strong>Data Transferred:</strong>{' '}
                    {(metadataPortabilityStats.totalDataTransferred / 1_024).toFixed(
                      1,
                    )}{' '}
                    KB
                    <br />
                    <strong>Avg Export Time:</strong>{' '}
                    {metadataPortabilityStats.averageExportTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                    <br />
                    <strong>Avg Import Time:</strong>{' '}
                    {metadataPortabilityStats.averageImportTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                  </p>
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
              Content Publishing
            </Card.Header>
            <Card.Description>
              DHT publishing performance and publication management
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <TooltipButton
              disabled={loadingPublishingStats}
              fluid
              loading={loadingPublishingStats}
              onClick={handleLoadContentPublishingStats}
              tooltip="Load Content Publishing and DHT publication performance metrics."
            >
              Load Publishing Stats
            </TooltipButton>

            {contentPublishingStats && !contentPublishingStats.error && (
              <div style={{ marginTop: '1em' }}>
                <Message>
                  <Message.Header>Publishing Overview</Message.Header>
                  <p>
                    <strong>Total Published:</strong>{' '}
                    {contentPublishingStats.totalPublished}
                    <br />
                    <strong>Active Publications:</strong>{' '}
                    {contentPublishingStats.activePublications}
                    <br />
                    <strong>Expired Publications:</strong>{' '}
                    {contentPublishingStats.expiredPublications}
                    <br />
                    <strong>Success Rate:</strong>{' '}
                    {(contentPublishingStats.publicationSuccessRate * 100).toFixed(
                      1,
                    )}
                    %
                    <br />
                    <strong>Republished:</strong>{' '}
                    {contentPublishingStats.republishedDescriptors}
                    <br />
                    <strong>Failed:</strong>{' '}
                    {contentPublishingStats.failedPublications}
                    <br />
                    <strong>Avg Publish Time:</strong>{' '}
                    {contentPublishingStats.averagePublishTime?.totalMilliseconds.toFixed(
                      0,
                    )}{' '}
                    ms
                  </p>
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
