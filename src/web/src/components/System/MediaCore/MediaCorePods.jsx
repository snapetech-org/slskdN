import { getRegionalLocale } from '../../../lib/regionalFormat';
// <copyright file="MediaCorePods.jsx" company="slskdN Team">
//     Copyright (c) slskdN Team. All rights reserved.
// </copyright>
import * as mediacore from '../../../lib/mediacore';
import Button from './MediaCoreButton';
import PodWorkflowNotice from './PodWorkflowNotice';
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import {
  Card,
  Form,
  Grid,
  Header,
  Icon,
  Input,
  Label,
  List,
  Message,
  Segment,
  Statistic,
  TextArea,
} from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const asObject = (value) =>
  value && typeof value === 'object' && !Array.isArray(value) ? value : {};

const MediaCorePods = ({ isPodWorkflowVisible, supportedAlgorithms }) => {
  // PodCore DHT states
  const [podToPublish, setPodToPublish] = useState('');
  const [publishingPod, setPublishingPod] = useState(false);
  const [podPublishingResult, setPodPublishingResult] = useState(null);
  const [podMetadataToRetrieve, setPodMetadataToRetrieve] = useState('');
  const [retrievingPodMetadata, setRetrievingPodMetadata] = useState(false);
  const [podMetadataResult, setPodMetadataResult] = useState(null);
  const [podToUnpublish, setPodToUnpublish] = useState('');
  const [unpublishingPod, setUnpublishingPod] = useState(false);
  const [podUnpublishResult, setPodUnpublishResult] = useState(null);
  const [podPublishingStats, setPodPublishingStats] = useState(null);
  const [loadingPodStats, setLoadingPodStats] = useState(false);

  // Pod Membership states
  const [membershipRecord, setMembershipRecord] = useState('');
  const [publishingMembership, setPublishingMembership] = useState(false);
  const [membershipPublishResult, setMembershipPublishResult] = useState(null);
  const [membershipPodId, setMembershipPodId] = useState('');
  const [membershipPeerId, setMembershipPeerId] = useState('');
  const [gettingMembership, setGettingMembership] = useState(false);
  const [membershipResult, setMembershipResult] = useState(null);
  const [verifyingMembershipStatus, setVerifyingMembershipStatus] =
    useState(false);
  const [membershipVerification, setMembershipVerification] = useState(null);
  const [banningMember, setBanningMember] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [banResult, setBanResult] = useState(null);
  const [changingRole, setChangingRole] = useState(false);
  const [newRole, setNewRole] = useState('member');
  const [roleChangeResult, setRoleChangeResult] = useState(null);
  const [membershipStats, setMembershipStats] = useState(null);
  const [loadingMembershipStats, setLoadingMembershipStats] = useState(false);

  // Pod Membership Verification states
  const [verifyPodId, setVerifyPodId] = useState('');
  const [verifyPeerId, setVerifyPeerId] = useState('');
  const [verifyingMembership, setVerifyingMembership] = useState(false);
  const [membershipVerificationResult, setMembershipVerificationResult] =
    useState(null);
  const [membershipMessageToVerify, setMembershipMessageToVerify] =
    useState('');
  const [verifyingMessage, setVerifyingMessage] = useState(false);
  const [messageVerificationResult, setMessageVerificationResult] =
    useState(null);
  const [roleCheckPodId, setRoleCheckPodId] = useState('');
  const [roleCheckPeerId, setRoleCheckPeerId] = useState('');
  const [requiredRole, setRequiredRole] = useState('member');
  const [checkingRole, setCheckingRole] = useState(false);
  const [roleCheckResult, setRoleCheckResult] = useState(null);
  const [verificationStats, setVerificationStats] = useState(null);
  const [loadingVerificationStats, setLoadingVerificationStats] =
    useState(false);

  // Pod Discovery states
  const [podToRegister, setPodToRegister] = useState('');
  const [registeringPod, setRegisteringPod] = useState(false);
  const [podRegistrationResult, setPodRegistrationResult] = useState(null);
  const [podToUnregister, setPodToUnregister] = useState('');
  const [unregisteringPod, setUnregisteringPod] = useState(false);
  const [podUnregistrationResult, setPodUnregistrationResult] = useState(null);
  const [discoverByName, setDiscoverByName] = useState('');
  const [discoveringByName, setDiscoveringByName] = useState(false);
  const [nameDiscoveryResult, setNameDiscoveryResult] = useState(null);
  const [discoverByTag, setDiscoverByTag] = useState('');
  const [discoveringByTag, setDiscoveringByTag] = useState(false);
  const [tagDiscoveryResult, setTagDiscoveryResult] = useState(null);
  const [discoverTags, setDiscoverTags] = useState('');
  const [discoveringByTags, setDiscoveringByTags] = useState(false);
  const [tagsDiscoveryResult, setTagsDiscoveryResult] = useState(null);
  const [discoverLimit, setDiscoverLimit] = useState(50);
  const [discoveringAll, setDiscoveringAll] = useState(false);
  const [allDiscoveryResult, setAllDiscoveryResult] = useState(null);
  const [discoverByContent, setDiscoverByContent] = useState('');
  const [discoveringByContent, setDiscoveringByContent] = useState(false);
  const [contentDiscoveryResult, setContentDiscoveryResult] = useState(null);
  const [discoveryStats, setDiscoveryStats] = useState(null);
  const [loadingDiscoveryStats, setLoadingDiscoveryStats] = useState(false);

  // Pod Join/Leave states
  const [joinRequestData, setJoinRequestData] = useState('');
  const [requestingJoin, setRequestingJoin] = useState(false);
  const [joinRequestResult, setJoinRequestResult] = useState(null);
  const [acceptanceData, setAcceptanceData] = useState('');
  const [acceptingJoin, setAcceptingJoin] = useState(false);
  const [acceptanceResult, setAcceptanceResult] = useState(null);
  const [leaveRequestData, setLeaveRequestData] = useState('');
  const [requestingLeave, setRequestingLeave] = useState(false);
  const [leaveRequestResult, setLeaveRequestResult] = useState(null);
  const [acceptingLeave, setAcceptingLeave] = useState(false);
  const [leaveAcceptanceResult, setLeaveAcceptanceResult] = useState(null);
  const [pendingPodId, setPendingPodId] = useState('');
  const [loadingPendingRequests, setLoadingPendingRequests] = useState(false);
  const [pendingJoinRequests, setPendingJoinRequests] = useState(null);
  const [pendingLeaveRequests, setPendingLeaveRequests] = useState(null);

  // Pod Message Routing states
  const [routeMessageData, setRouteMessageData] = useState('');
  const [routingMessage, setRoutingMessage] = useState(false);
  const [routingResult, setRoutingResult] = useState(null);
  const [routeToPeersMessage, setRouteToPeersMessage] = useState('');
  const [routeToPeersIds, setRouteToPeersIds] = useState('');
  const [routingToPeers, setRoutingToPeers] = useState(false);
  const [routingToPeersResult, setRoutingToPeersResult] = useState(null);
  const [routingStats, setRoutingStats] = useState(null);
  const [loadingRoutingStats, setLoadingRoutingStats] = useState(false);
  const [checkMessageId, setCheckMessageId] = useState('');
  const [checkPodId, setCheckPodId] = useState('');
  const [checkingMessageSeen, setCheckingMessageSeen] = useState(false);
  const [messageSeenResult, setMessageSeenResult] = useState(null);

  // Pod Message Signing states
  const [messageToSign, setMessageToSign] = useState('');
  const [privateKeyForSigning, setPrivateKeyForSigning] = useState('');
  const [signingMessage, setSigningMessage] = useState(false);
  const [signedMessageResult, setSignedMessageResult] = useState(null);
  const [messageToVerify, setMessageToVerify] = useState('');
  const [verifyingSignature, setVerifyingSignature] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [generatingKeyPair, setGeneratingKeyPair] = useState(false);
  const [generatedKeyPair, setGeneratedKeyPair] = useState(null);
  const [signingStats, setSigningStats] = useState(null);
  const [loadingSigningStats, setLoadingSigningStats] = useState(false);

  // Pod Message Storage states
  const [storageStats, setStorageStats] = useState(null);
  const [storageStatsLoading, setStorageStatsLoading] = useState(false);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [rebuildIndexLoading, setRebuildIndexLoading] = useState(false);
  const [vacuumLoading, setVacuumLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // Pod Message Backfill states
  const [backfillStats, setBackfillStats] = useState(null);
  const [backfillStatsLoading, setBackfillStatsLoading] = useState(false);
  const [syncBackfillLoading, setSyncBackfillLoading] = useState(false);
  const [lastSeenTimestamps, setLastSeenTimestamps] = useState(null);
  const [backfillPodId, setBackfillPodId] = useState('');

  // Pod Channel Management states
  const [channels, setChannels] = useState([]);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [createChannelLoading, setCreateChannelLoading] = useState(false);
  const [updateChannelLoading, setUpdateChannelLoading] = useState(false);
  const [deleteChannelLoading, setDeleteChannelLoading] = useState(false);
  const [channelPodId, setChannelPodId] = useState('');
  const [newChannelName, setNewChannelName] = useState('');
  const [newChannelKind, setNewChannelKind] = useState('General');
  const [editingChannel, setEditingChannel] = useState(null);
  const [editChannelName, setEditChannelName] = useState('');

  // Pod Content Linking states
  const [contentId, setContentId] = useState('');
  const [contentValidation, setContentValidation] = useState(null);
  const [contentMetadata, setContentMetadata] = useState(null);
  const [contentSearchQuery, setContentSearchQuery] = useState('');
  const [contentSearchResults, setContentSearchResults] = useState([]);
  const [contentValidationLoading, setContentValidationLoading] =
    useState(false);
  const [contentMetadataLoading, setContentMetadataLoading] = useState(false);
  const [contentSearchLoading, setContentSearchLoading] = useState(false);
  const [createPodLoading, setCreatePodLoading] = useState(false);
  const [newPodName, setNewPodName] = useState('');
  const [newPodVisibility, setNewPodVisibility] = useState('Unlisted');

  // Pod Opinion Management states
  const [opinionPodId, setOpinionPodId] = useState('');
  const [opinionContentId, setOpinionContentId] = useState('');
  const [opinionVariantHash, setOpinionVariantHash] = useState('');
  const [opinionScore, setOpinionScore] = useState(5);
  const [opinionNote, setOpinionNote] = useState('');
  const [opinions, setOpinions] = useState([]);
  const [opinionStatistics, setOpinionStatistics] = useState(null);
  const [publishOpinionLoading, setPublishOpinionLoading] = useState(false);
  const [getOpinionsLoading, setGetOpinionsLoading] = useState(false);
  const [getStatsLoading, setGetStatsLoading] = useState(false);
  const [refreshOpinionsLoading, setRefreshOpinionsLoading] = useState(false);

  // Pod Opinion Aggregation states
  const [aggregatedOpinions, setAggregatedOpinions] = useState(null);
  const [memberAffinities, setMemberAffinities] = useState({});
  const [consensusRecommendations, setConsensusRecommendations] = useState([]);
  const [getAggregatedLoading, setGetAggregatedLoading] = useState(false);
  const [getAffinitiesLoading, setGetAffinitiesLoading] = useState(false);
  const [getRecommendationsLoading, setGetRecommendationsLoading] =
    useState(false);
  const [updateAffinitiesLoading, setUpdateAffinitiesLoading] = useState(false);
  const [publishContentId, setPublishContentId] = useState('');

  // PodCore handlers
  const handlePublishPod = async () => {
    if (!podToPublish.trim()) {
      toast.warning('Please enter pod JSON data');
      return;
    }

    try {
      setPublishingPod(true);
      setPodPublishingResult(null);
      const pod = JSON.parse(podToPublish);
      const result = await mediacore.publishPod(pod);
      setPodPublishingResult(result);
      setPodToPublish('');
    } catch (error_) {
      setPodPublishingResult({ error: error_.message });
    } finally {
      setPublishingPod(false);
    }
  };

  const handleRetrievePodMetadata = async () => {
    if (!podMetadataToRetrieve.trim()) {
      toast.warning('Please enter a pod ID');
      return;
    }

    try {
      setRetrievingPodMetadata(true);
      setPodMetadataResult(null);
      const result = await mediacore.getPublishedPodMetadata(
        podMetadataToRetrieve,
      );
      setPodMetadataResult(result);
    } catch (error_) {
      setPodMetadataResult({ error: error_.message });
    } finally {
      setRetrievingPodMetadata(false);
    }
  };

  const handleUnpublishPod = async () => {
    if (!podToUnpublish.trim()) {
      toast.warning('Please enter a pod ID');
      return;
    }

    if (
      !confirm(`Are you sure you want to unpublish pod "${podToUnpublish}"?`)
    ) {
      return;
    }

    try {
      setUnpublishingPod(true);
      setPodUnpublishResult(null);
      const result = await mediacore.unpublishPod(podToUnpublish);
      setPodUnpublishResult(result);
      setPodToUnpublish('');
    } catch (error_) {
      setPodUnpublishResult({ error: error_.message });
    } finally {
      setUnpublishingPod(false);
    }
  };

  const handleLoadPodPublishingStats = async () => {
    try {
      setLoadingPodStats(true);
      setPodPublishingStats(null);
      const result = await mediacore.getPodPublishingStats();
      setPodPublishingStats(result);
    } catch (error_) {
      setPodPublishingStats({ error: error_.message });
    } finally {
      setLoadingPodStats(false);
    }
  };

  // Pod Membership handlers
  const handlePublishMembership = async () => {
    if (!membershipRecord.trim()) {
      toast.warning('Please enter membership record JSON data');
      return;
    }

    try {
      setPublishingMembership(true);
      setMembershipPublishResult(null);
      const record = JSON.parse(membershipRecord);
      const result = await mediacore.publishMembership(record);
      setMembershipPublishResult(result);
      setMembershipRecord('');
    } catch (error_) {
      setMembershipPublishResult({ error: error_.message });
    } finally {
      setPublishingMembership(false);
    }
  };

  const handleGetMembership = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    try {
      setGettingMembership(true);
      setMembershipResult(null);
      const result = await mediacore.getMembership(
        membershipPodId,
        membershipPeerId,
      );
      setMembershipResult(result);
    } catch (error_) {
      setMembershipResult({ error: error_.message });
    } finally {
      setGettingMembership(false);
    }
  };

  const handleVerifyMembership = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    try {
      setVerifyingMembership(true);
      setMembershipVerification(null);
      const result = await mediacore.verifyMembership(
        membershipPodId,
        membershipPeerId,
      );
      setMembershipVerification(result);
    } catch (error_) {
      setMembershipVerification({ error: error_.message });
    } finally {
      setVerifyingMembership(false);
    }
  };

  const handleBanMember = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    if (
      !confirm(
        `Are you sure you want to ban member "${membershipPeerId}" from pod "${membershipPodId}"?`,
      )
    ) {
      return;
    }

    try {
      setBanningMember(true);
      setBanResult(null);
      const result = await mediacore.banMember(
        membershipPodId,
        membershipPeerId,
        banReason || null,
      );
      setBanResult(result);
      setBanReason('');
    } catch (error_) {
      setBanResult({ error: error_.message });
    } finally {
      setBanningMember(false);
    }
  };

  const handleChangeRole = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    try {
      setChangingRole(true);
      setRoleChangeResult(null);
      const result = await mediacore.changeMemberRole(
        membershipPodId,
        membershipPeerId,
        newRole,
      );
      setRoleChangeResult(result);
    } catch (error_) {
      setRoleChangeResult({ error: error_.message });
    } finally {
      setChangingRole(false);
    }
  };

  const handleLoadMembershipStats = async () => {
    try {
      setLoadingMembershipStats(true);
      setMembershipStats(null);
      const result = await mediacore.getMembershipStats();
      setMembershipStats(result);
    } catch (error_) {
      setMembershipStats({ error: error_.message });
    } finally {
      setLoadingMembershipStats(false);
    }
  };

  const handleCleanupMemberships = async () => {
    if (
      !confirm('Are you sure you want to cleanup expired membership records?')
    ) {
      return;
    }

    try {
      const result = await mediacore.cleanupExpiredMemberships();
      toast.success(
        `Cleanup completed: ${result.recordsCleaned} records cleaned, ${result.errorsEncountered} errors`,
      );
      // Reload stats to reflect changes
      await handleLoadMembershipStats();
    } catch (error_) {
      toast.error(`Failed to cleanup: ${error_.message}`);
    }
  };

  // Pod Membership Verification handlers
  const handleVerifyPodMembership = async () => {
    if (!verifyPodId.trim() || !verifyPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    try {
      setVerifyingMembership(true);
      setMembershipVerificationResult(null);
      const result = await mediacore.verifyPodMembership(
        verifyPodId,
        verifyPeerId,
      );
      setMembershipVerificationResult(result);
    } catch (error_) {
      setMembershipVerificationResult({ error: error_.message });
    } finally {
      setVerifyingMembership(false);
    }
  };

  const handleVerifyMessage = async () => {
    if (!membershipMessageToVerify.trim()) {
      toast.warning('Please enter a message JSON');
      return;
    }

    try {
      setVerifyingMessage(true);
      setMessageVerificationResult(null);
      const message = JSON.parse(membershipMessageToVerify);
      const result = await mediacore.verifyPodMessage(message);
      setMessageVerificationResult(result);
    } catch (error_) {
      setMessageVerificationResult({ error: error_.message });
    } finally {
      setVerifyingMessage(false);
    }
  };

  const handleCheckRole = async () => {
    if (!roleCheckPodId.trim() || !roleCheckPeerId.trim()) {
      toast.warning('Please enter both Pod ID and Peer ID');
      return;
    }

    try {
      setCheckingRole(true);
      setRoleCheckResult(null);
      const hasRole = await mediacore.checkPodRole(
        roleCheckPodId,
        roleCheckPeerId,
        requiredRole,
      );
      setRoleCheckResult({ hasRole });
    } catch (error_) {
      setRoleCheckResult({ error: error_.message });
    } finally {
      setCheckingRole(false);
    }
  };

  const handleLoadVerificationStats = async () => {
    try {
      setLoadingVerificationStats(true);
      setVerificationStats(null);
      const result = await mediacore.getVerificationStats();
      setVerificationStats(result);
    } catch (error_) {
      setVerificationStats({ error: error_.message });
    } finally {
      setLoadingVerificationStats(false);
    }
  };

  // Pod Discovery handlers
  const handleRegisterPodForDiscovery = async () => {
    if (!podToRegister.trim()) {
      toast.warning('Please enter pod JSON data');
      return;
    }

    try {
      setRegisteringPod(true);
      setPodRegistrationResult(null);
      const pod = JSON.parse(podToRegister);
      const result = await mediacore.registerPodForDiscovery(pod);
      setPodRegistrationResult(result);
      setPodToRegister('');
    } catch (error_) {
      setPodRegistrationResult({ error: error_.message });
    } finally {
      setRegisteringPod(false);
    }
  };

  const handleUnregisterPodFromDiscovery = async () => {
    if (!podToUnregister.trim()) {
      toast.warning('Please enter a pod ID');
      return;
    }

    try {
      setUnregisteringPod(true);
      setPodUnregistrationResult(null);
      const result =
        await mediacore.unregisterPodFromDiscovery(podToUnregister);
      setPodUnregistrationResult(result);
      setPodToUnregister('');
    } catch (error_) {
      setPodUnregistrationResult({ error: error_.message });
    } finally {
      setUnregisteringPod(false);
    }
  };

  const handleDiscoverByName = async () => {
    if (!discoverByName.trim()) {
      toast.warning('Please enter a pod name');
      return;
    }

    try {
      setDiscoveringByName(true);
      setNameDiscoveryResult(null);
      const result = await mediacore.discoverPodsByName(discoverByName);
      setNameDiscoveryResult(result);
    } catch (error_) {
      setNameDiscoveryResult({ error: error_.message });
    } finally {
      setDiscoveringByName(false);
    }
  };

  const handleDiscoverByTag = async () => {
    if (!discoverByTag.trim()) {
      toast.warning('Please enter a tag');
      return;
    }

    try {
      setDiscoveringByTag(true);
      setTagDiscoveryResult(null);
      const result = await mediacore.discoverPodsByTag(discoverByTag);
      setTagDiscoveryResult(result);
    } catch (error_) {
      setTagDiscoveryResult({ error: error_.message });
    } finally {
      setDiscoveringByTag(false);
    }
  };

  const handleDiscoverByTags = async () => {
    if (!discoverTags.trim()) {
      toast.warning('Please enter tags (comma-separated)');
      return;
    }

    try {
      setDiscoveringByTags(true);
      setTagsDiscoveryResult(null);
      const tagList = discoverTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const result = await mediacore.discoverPodsByTags(tagList);
      setTagsDiscoveryResult(result);
    } catch (error_) {
      setTagsDiscoveryResult({ error: error_.message });
    } finally {
      setDiscoveringByTags(false);
    }
  };

  const handleDiscoverAll = async () => {
    try {
      setDiscoveringAll(true);
      setAllDiscoveryResult(null);
      const result = await mediacore.discoverAllPods(discoverLimit);
      setAllDiscoveryResult(result);
    } catch (error_) {
      setAllDiscoveryResult({ error: error_.message });
    } finally {
      setDiscoveringAll(false);
    }
  };

  const handleDiscoverByContent = async () => {
    if (!discoverByContent.trim()) {
      toast.warning('Please enter a content ID');
      return;
    }

    try {
      setDiscoveringByContent(true);
      setContentDiscoveryResult(null);
      const result = await mediacore.discoverPodsByContent(discoverByContent);
      setContentDiscoveryResult(result);
    } catch (error_) {
      setContentDiscoveryResult({ error: error_.message });
    } finally {
      setDiscoveringByContent(false);
    }
  };

  const handleLoadDiscoveryStats = async () => {
    try {
      setLoadingDiscoveryStats(true);
      setDiscoveryStats(null);
      const result = await mediacore.getPodDiscoveryStats();
      setDiscoveryStats(result);
    } catch (error_) {
      setDiscoveryStats({ error: error_.message });
    } finally {
      setLoadingDiscoveryStats(false);
    }
  };

  const handleRefreshDiscovery = async () => {
    try {
      const result = await mediacore.refreshPodDiscovery();
      toast.success(
        `Discovery refresh completed: ${result.entriesRefreshed} refreshed, ${result.entriesExpired} expired`,
      );
      // Reload stats to reflect changes
      await handleLoadDiscoveryStats();
    } catch (error_) {
      toast.error(`Failed to refresh discovery: ${error_.message}`);
    }
  };

  // Pod Join/Leave handlers
  const handleRequestJoin = async () => {
    if (!joinRequestData.trim()) {
      toast.warning('Please enter join request JSON data');
      return;
    }

    try {
      setRequestingJoin(true);
      setJoinRequestResult(null);
      const joinRequest = JSON.parse(joinRequestData);
      const result = await mediacore.requestPodJoin(joinRequest);
      setJoinRequestResult(result);
      setJoinRequestData('');
    } catch (error_) {
      setJoinRequestResult({ error: error_.message });
    } finally {
      setRequestingJoin(false);
    }
  };

  const handleAcceptJoin = async () => {
    if (!acceptanceData.trim()) {
      toast.warning('Please enter acceptance JSON data');
      return;
    }

    try {
      setAcceptingJoin(true);
      setAcceptanceResult(null);
      const acceptance = JSON.parse(acceptanceData);
      const result = await mediacore.acceptPodJoin(acceptance);
      setAcceptanceResult(result);
      setAcceptanceData('');
    } catch (error_) {
      setAcceptanceResult({ error: error_.message });
    } finally {
      setAcceptingJoin(false);
    }
  };

  const handleRequestLeave = async () => {
    if (!leaveRequestData.trim()) {
      toast.warning('Please enter leave request JSON data');
      return;
    }

    try {
      setRequestingLeave(true);
      setLeaveRequestResult(null);
      const leaveRequest = JSON.parse(leaveRequestData);
      const result = await mediacore.requestPodLeave(leaveRequest);
      setLeaveRequestResult(result);
      setLeaveRequestData('');
    } catch (error_) {
      setLeaveRequestResult({ error: error_.message });
    } finally {
      setRequestingLeave(false);
    }
  };

  const handleAcceptLeave = async () => {
    if (!acceptanceData.trim()) {
      toast.warning('Please enter leave acceptance JSON data');
      return;
    }

    try {
      setAcceptingLeave(true);
      setLeaveAcceptanceResult(null);
      const acceptance = JSON.parse(acceptanceData);
      const result = await mediacore.acceptPodLeave(acceptance);
      setLeaveAcceptanceResult(result);
      setAcceptanceData('');
    } catch (error_) {
      setLeaveAcceptanceResult({ error: error_.message });
    } finally {
      setAcceptingLeave(false);
    }
  };

  const handleLoadPendingRequests = async () => {
    if (!pendingPodId.trim()) {
      toast.warning('Please enter a pod ID');
      return;
    }

    try {
      setLoadingPendingRequests(true);
      setPendingJoinRequests(null);
      setPendingLeaveRequests(null);

      const [joinRequests, leaveRequests] = await Promise.all([
        mediacore.getPendingJoinRequests(pendingPodId),
        mediacore.getPendingLeaveRequests(pendingPodId),
      ]);

      setPendingJoinRequests(joinRequests);
      setPendingLeaveRequests(leaveRequests);
    } catch (error_) {
      setPendingJoinRequests({ error: error_.message });
      setPendingLeaveRequests({ error: error_.message });
    } finally {
      setLoadingPendingRequests(false);
    }
  };

  // Pod Message Routing handlers
  const handleRouteMessage = async () => {
    if (!routeMessageData.trim()) {
      toast.warning('Please enter message JSON data');
      return;
    }

    try {
      setRoutingMessage(true);
      setRoutingResult(null);
      const message = JSON.parse(routeMessageData);
      const result = await mediacore.routePodMessage(message);
      setRoutingResult(result);
      setRouteMessageData('');
    } catch (error_) {
      setRoutingResult({ error: error_.message });
    } finally {
      setRoutingMessage(false);
    }
  };

  const handleRouteMessageToPeers = async () => {
    if (!routeToPeersMessage.trim() || !routeToPeersIds.trim()) {
      toast.warning('Please enter message JSON and target peer IDs');
      return;
    }

    try {
      setRoutingToPeers(true);
      setRoutingToPeersResult(null);
      const message = JSON.parse(routeToPeersMessage);
      const targetPeerIds = routeToPeersIds
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean);
      const result = await mediacore.routePodMessageToPeers(
        message,
        targetPeerIds,
      );
      setRoutingToPeersResult(result);
      setRouteToPeersMessage('');
      setRouteToPeersIds('');
    } catch (error_) {
      setRoutingToPeersResult({ error: error_.message });
    } finally {
      setRoutingToPeers(false);
    }
  };

  const handleLoadRoutingStats = async () => {
    try {
      setLoadingRoutingStats(true);
      setRoutingStats(null);
      const result = await mediacore.getPodMessageRoutingStats();
      setRoutingStats(result);
    } catch (error_) {
      setRoutingStats({ error: error_.message });
    } finally {
      setLoadingRoutingStats(false);
    }
  };

  const handleCheckMessageSeen = async () => {
    if (!checkMessageId.trim() || !checkPodId.trim()) {
      toast.warning('Please enter both message ID and pod ID');
      return;
    }

    try {
      setCheckingMessageSeen(true);
      setMessageSeenResult(null);
      const result = await mediacore.checkMessageSeen(
        checkMessageId,
        checkPodId,
      );
      setMessageSeenResult(result);
    } catch (error_) {
      setMessageSeenResult({ error: error_.message });
    } finally {
      setCheckingMessageSeen(false);
    }
  };

  const handleRegisterMessageSeen = async () => {
    if (!checkMessageId.trim() || !checkPodId.trim()) {
      toast.warning('Please enter both message ID and pod ID');
      return;
    }

    try {
      const result = await mediacore.registerMessageSeen(
        checkMessageId,
        checkPodId,
      );
      toast.success(
        `Message registered as seen: ${result.wasNewlyRegistered ? 'New' : 'Already known'}`,
      );
    } catch (error_) {
      toast.error(`Failed to register message: ${error_.message}`);
    }
  };

  const handleCleanupSeenMessages = async () => {
    try {
      const result = await mediacore.cleanupSeenMessages();
      toast.success(
        `Cleanup completed: ${result.messagesCleaned} messages cleaned, ${result.messagesRetained} retained`,
      );
      // Reload stats to reflect changes
      await handleLoadRoutingStats();
    } catch (error_) {
      toast.error(`Failed to cleanup: ${error_.message}`);
    }
  };

  // Pod Message Signing handlers
  const handleSignMessage = async () => {
    if (!messageToSign.trim() || !privateKeyForSigning.trim()) {
      toast.warning('Please enter message JSON and private key');
      return;
    }

    try {
      setSigningMessage(true);
      setSignedMessageResult(null);
      const message = JSON.parse(messageToSign);
      const result = await mediacore.signPodMessage(
        message,
        privateKeyForSigning,
      );
      setSignedMessageResult(result);
      setMessageToSign('');
    } catch (error_) {
      setSignedMessageResult({ error: error_.message });
    } finally {
      setSigningMessage(false);
    }
  };

  const handleVerifySignature = async () => {
    if (!messageToVerify.trim()) {
      toast.warning('Please enter message JSON to verify');
      return;
    }

    try {
      setVerifyingSignature(true);
      setVerificationResult(null);
      const message = JSON.parse(messageToVerify);
      const result = await mediacore.verifyPodMessageSignature(message);
      setVerificationResult(result);
    } catch (error_) {
      setVerificationResult({ error: error_.message });
    } finally {
      setVerifyingSignature(false);
    }
  };

  const handleGenerateKeyPair = async () => {
    try {
      setGeneratingKeyPair(true);
      setGeneratedKeyPair(null);
      const result = await mediacore.generateMessageKeyPair();
      setGeneratedKeyPair(result);
    } catch (error_) {
      setGeneratedKeyPair({ error: error_.message });
    } finally {
      setGeneratingKeyPair(false);
    }
  };

  const handleLoadSigningStats = async () => {
    try {
      setLoadingSigningStats(true);
      setSigningStats(null);
      const result = await mediacore.getMessageSigningStats();
      setSigningStats(result);
    } catch (error_) {
      setSigningStats({ error: error_.message });
    } finally {
      setLoadingSigningStats(false);
    }
  };

  // Pod Message Storage handlers
  const handleGetStorageStats = async () => {
    try {
      setStorageStatsLoading(true);
      setStorageStats(null);
      const result = await mediacore.getMessageStorageStats();
      setStorageStats(result);
    } catch (error_) {
      setStorageStats({ error: error_.message });
      toast.error(`Failed to get storage stats: ${error_.message}`);
    } finally {
      setStorageStatsLoading(false);
    }
  };

  const handleCleanupMessages = async () => {
    try {
      setCleanupLoading(true);
      const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1_000;
      const result = await mediacore.cleanupMessages(thirtyDaysAgo);
      toast.success(`Cleaned up ${result} old messages`);
      // Refresh stats after cleanup
      await handleGetStorageStats();
    } catch (error_) {
      toast.error(`Failed to cleanup messages: ${error_.message}`);
    } finally {
      setCleanupLoading(false);
    }
  };

  const handleRebuildSearchIndex = async () => {
    try {
      setRebuildIndexLoading(true);
      const result = await mediacore.rebuildSearchIndex();
      toast.success(
        result
          ? 'Search index rebuilt successfully'
          : 'Search index rebuild failed',
      );
    } catch (error_) {
      toast.error(`Failed to rebuild search index: ${error_.message}`);
    } finally {
      setRebuildIndexLoading(false);
    }
  };

  const handleVacuumDatabase = async () => {
    try {
      setVacuumLoading(true);
      const result = await mediacore.vacuumDatabase();
      toast.success(
        result
          ? 'Database vacuum completed successfully'
          : 'Database vacuum failed',
      );
    } catch (error_) {
      toast.error(`Failed to vacuum database: ${error_.message}`);
    } finally {
      setVacuumLoading(false);
    }
  };

  const handleSearchMessages = async () => {
    if (!searchQuery.trim()) return;

    try {
      setSearchLoading(true);
      setSearchResults(null);
      const result = await mediacore.searchMessages(
        'all',
        searchQuery,
        null,
        50,
      ); // Search all pods
      setSearchResults(result);
    } catch (error_) {
      setSearchResults([]);
      toast.error(`Failed to search messages: ${error_.message}`);
    } finally {
      setSearchLoading(false);
    }
  };

  // Pod Message Backfill handlers
  const handleGetBackfillStats = async () => {
    try {
      setBackfillStatsLoading(true);
      setBackfillStats(null);
      const result = await mediacore.getBackfillStats();
      setBackfillStats(result);
    } catch (error_) {
      setBackfillStats({ error: error_.message });
      toast.error(`Failed to get backfill stats: ${error_.message}`);
    } finally {
      setBackfillStatsLoading(false);
    }
  };

  const handleSyncPodBackfill = async () => {
    if (!backfillPodId.trim()) {
      toast.error('Pod ID is required for backfill sync');
      return;
    }

    try {
      setSyncBackfillLoading(true);
      // Get current last seen timestamps
      const timestamps = await mediacore.getLastSeenTimestamps(backfillPodId);
      const result = await mediacore.syncPodBackfill(backfillPodId, timestamps);
      toast.success(
        `Backfill sync completed: ${result.totalMessagesReceived} messages received`,
      );
      // Refresh stats
      await handleGetBackfillStats();
    } catch (error_) {
      toast.error(`Failed to sync pod backfill: ${error_.message}`);
    } finally {
      setSyncBackfillLoading(false);
    }
  };

  const handleGetLastSeenTimestamps = async () => {
    if (!backfillPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    try {
      const timestamps = await mediacore.getLastSeenTimestamps(backfillPodId);
      setLastSeenTimestamps(timestamps);
    } catch (error_) {
      toast.error(`Failed to get last seen timestamps: ${error_.message}`);
      setLastSeenTimestamps(null);
    }
  };

  // Pod Channel Management handlers
  const handleGetChannels = async () => {
    if (!channelPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    try {
      setChannelsLoading(true);
      const result = await mediacore.getChannels(channelPodId);
      setChannels(asArray(result));
    } catch (error_) {
      toast.error(`Failed to get channels: ${error_.message}`);
      setChannels([]);
    } finally {
      setChannelsLoading(false);
    }
  };

  const handleCreateChannel = async () => {
    if (!channelPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    if (!newChannelName.trim()) {
      toast.error('Channel name is required');
      return;
    }

    try {
      setCreateChannelLoading(true);
      const channel = {
        kind: newChannelKind,
        name: newChannelName,
      };
      await mediacore.createChannel(channelPodId, channel);
      toast.success(`Channel "${newChannelName}" created successfully`);
      setNewChannelName('');
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(`Failed to create channel: ${error_.message}`);
    } finally {
      setCreateChannelLoading(false);
    }
  };

  const handleUpdateChannel = async (channelId) => {
    if (!editChannelName.trim()) {
      toast.error('Channel name is required');
      return;
    }

    try {
      setUpdateChannelLoading(true);
      const updatedChannel = {
        channelId,
        kind: editingChannel.kind,
        name: editChannelName,
      };
      await mediacore.updateChannel(channelPodId, channelId, updatedChannel);
      toast.success(`Channel updated successfully`);
      setEditingChannel(null);
      setEditChannelName('');
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(`Failed to update channel: ${error_.message}`);
    } finally {
      setUpdateChannelLoading(false);
    }
  };

  const handleDeleteChannel = async (channelId, channelName) => {
    if (
      !confirm(
        `Are you sure you want to delete the channel "${channelName}"? This action cannot be undone.`,
      )
    ) {
      return;
    }

    try {
      setDeleteChannelLoading(true);
      await mediacore.deleteChannel(channelPodId, channelId);
      toast.success(`Channel "${channelName}" deleted successfully`);
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(`Failed to delete channel: ${error_.message}`);
    } finally {
      setDeleteChannelLoading(false);
    }
  };

  const startEditingChannel = (channel) => {
    setEditingChannel(channel);
    setEditChannelName(channel.name);
  };

  const cancelEditingChannel = () => {
    setEditingChannel(null);
    setEditChannelName('');
  };

  // Pod Content Linking handlers
  const handleValidateContentId = async () => {
    if (!contentId.trim()) {
      toast.error('Content ID is required');
      return;
    }

    try {
      setContentValidationLoading(true);
      setContentValidation(null);
      setContentMetadata(null);
      const result = await mediacore.validateContentIdForPod(contentId.trim());
      setContentValidation(result);

      // If valid, automatically fetch metadata
      if (result.isValid) {
        await handleGetContentMetadata();
      }
    } catch (error_) {
      setContentValidation({ error: error_.message, isValid: false });
      toast.error(`Failed to validate content ID: ${error_.message}`);
    } finally {
      setContentValidationLoading(false);
    }
  };

  const handleGetContentMetadata = async () => {
    if (!contentId.trim()) return;

    try {
      setContentMetadataLoading(true);
      const metadata = await mediacore.getContentMetadata(contentId.trim());
      setContentMetadata(metadata);

      // Auto-fill pod name if empty
      if (!newPodName.trim() && metadata) {
        setNewPodName(`${metadata.artist} - ${metadata.title}`);
      }
    } catch (error_) {
      toast.error(`Failed to get content metadata: ${error_.message}`);
      setContentMetadata(null);
    } finally {
      setContentMetadataLoading(false);
    }
  };

  const handleSearchContent = async () => {
    if (!contentSearchQuery.trim()) return;

    try {
      setContentSearchLoading(true);
      setContentSearchResults([]);
      const results = await mediacore.searchContent(
        contentSearchQuery.trim(),
        null,
        10,
      );
      setContentSearchResults(results);
    } catch (error_) {
      toast.error(`Failed to search content: ${error_.message}`);
      setContentSearchResults([]);
    } finally {
      setContentSearchLoading(false);
    }
  };

  const handleCreateContentLinkedPod = async () => {
    if (!contentId.trim()) {
      toast.error('Content ID is required');
      return;
    }

    if (!newPodName.trim()) {
      toast.error('Pod name is required');
      return;
    }

    if (!contentValidation?.isValid) {
      toast.error('Please validate the content ID first');
      return;
    }

    try {
      setCreatePodLoading(true);
      const podRequest = {
        channels: [
          {
            channelId: 'general',
            kind: 'General',
            name: 'General',
          },
        ],

        contentId: contentId.trim(),

        externalBindings: [],
        // Auto-generate
        name: newPodName.trim(),
        podId: '',
        tags: [],
        visibility: newPodVisibility,
      };

      const createdPod = await mediacore.createContentLinkedPod(podRequest);
      toast.success(`Pod "${createdPod.name}" created successfully!`);

      // Reset form
      setContentId('');
      setContentValidation(null);
      setContentMetadata(null);
      setNewPodName('');
      setContentSearchQuery('');
      setContentSearchResults([]);
    } catch (error_) {
      toast.error(`Failed to create pod: ${error_.message}`);
    } finally {
      setCreatePodLoading(false);
    }
  };

  const selectContentFromSearch = (contentItem) => {
    setContentId(contentItem.contentId);
    setContentSearchQuery('');
    setContentSearchResults([]);
  };

  // Pod Opinion Management handlers
  const handlePublishOpinion = async () => {
    if (
      !opinionPodId.trim() ||
      !opinionContentId.trim() ||
      !opinionVariantHash.trim()
    ) {
      toast.error('Pod ID, Content ID, and Variant Hash are required');
      return;
    }

    if (opinionScore < 0 || opinionScore > 10) {
      toast.error('Score must be between 0 and 10');
      return;
    }

    try {
      setPublishOpinionLoading(true);
      const opinion = {
        contentId: opinionContentId.trim(),
        note: opinionNote.trim(),
        score: opinionScore,
        senderPeerId: 'current-user',
        variantHash: opinionVariantHash.trim(), // Get from session when available
      };

      await mediacore.publishOpinion(opinionPodId.trim(), opinion);
      toast.success('Opinion published successfully');

      // Reset form
      setOpinionContentId('');
      setOpinionVariantHash('');
      setOpinionScore(5);
      setOpinionNote('');

      // Refresh opinions if we're viewing them
      if (opinionContentId) {
        await handleGetOpinions();
      }
    } catch (error_) {
      toast.error(`Failed to publish opinion: ${error_.message}`);
    } finally {
      setPublishOpinionLoading(false);
    }
  };

  const handleGetOpinions = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error('Pod ID and Content ID are required');
      return;
    }

    try {
      setGetOpinionsLoading(true);
      const result = await mediacore.getContentOpinions(
        opinionPodId.trim(),
        opinionContentId.trim(),
      );
      setOpinions(result);
    } catch (error_) {
      toast.error(`Failed to get opinions: ${error_.message}`);
      setOpinions([]);
    } finally {
      setGetOpinionsLoading(false);
    }
  };

  const handleGetOpinionStatistics = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error('Pod ID and Content ID are required');
      return;
    }

    try {
      setGetStatsLoading(true);
      const stats = await mediacore.getOpinionStatistics(
        opinionPodId.trim(),
        opinionContentId.trim(),
      );
      setOpinionStatistics(stats);
    } catch (error_) {
      toast.error(`Failed to get opinion statistics: ${error_.message}`);
      setOpinionStatistics(null);
    } finally {
      setGetStatsLoading(false);
    }
  };

  const handleRefreshOpinions = async () => {
    if (!opinionPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    try {
      setRefreshOpinionsLoading(true);
      const result = await mediacore.refreshPodOpinions(opinionPodId.trim());
      toast.success(`Refreshed ${result.opinionsRefreshed} opinions`);

      // Refresh current view
      if (opinionContentId) {
        await Promise.all([handleGetOpinions(), handleGetOpinionStatistics()]);
      }
    } catch (error_) {
      toast.error(`Failed to refresh opinions: ${error_.message}`);
    } finally {
      setRefreshOpinionsLoading(false);
    }
  };

  // Pod Opinion Aggregation handlers
  const handleGetAggregatedOpinions = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error('Pod ID and Content ID are required');
      return;
    }

    try {
      setGetAggregatedLoading(true);
      const aggregated = await mediacore.getAggregatedOpinions(
        opinionPodId.trim(),
        opinionContentId.trim(),
      );
      setAggregatedOpinions(aggregated);
    } catch (error_) {
      toast.error(`Failed to get aggregated opinions: ${error_.message}`);
      setAggregatedOpinions(null);
    } finally {
      setGetAggregatedLoading(false);
    }
  };

  const handleGetMemberAffinities = async () => {
    if (!opinionPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    try {
      setGetAffinitiesLoading(true);
      const affinities = await mediacore.getMemberAffinities(
        opinionPodId.trim(),
      );
      setMemberAffinities(affinities);
    } catch (error_) {
      toast.error(`Failed to get member affinities: ${error_.message}`);
      setMemberAffinities({});
    } finally {
      setGetAffinitiesLoading(false);
    }
  };

  const handleGetConsensusRecommendations = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error('Pod ID and Content ID are required');
      return;
    }

    try {
      setGetRecommendationsLoading(true);
      const recommendations = await mediacore.getConsensusRecommendations(
        opinionPodId.trim(),
        opinionContentId.trim(),
      );
      setConsensusRecommendations(recommendations);
    } catch (error_) {
      toast.error(`Failed to get consensus recommendations: ${error_.message}`);
      setConsensusRecommendations([]);
    } finally {
      setGetRecommendationsLoading(false);
    }
  };

  const handleUpdateMemberAffinities = async () => {
    if (!opinionPodId.trim()) {
      toast.error('Pod ID is required');
      return;
    }

    try {
      setUpdateAffinitiesLoading(true);
      const result = await mediacore.updateMemberAffinities(
        opinionPodId.trim(),
      );
      toast.success(`Updated affinities for ${result.membersUpdated} members`);

      // Refresh affinities display
      await handleGetMemberAffinities();
    } catch (error_) {
      toast.error(`Failed to update member affinities: ${error_.message}`);
    } finally {
      setUpdateAffinitiesLoading(false);
    }
  };

  return (
    <>
        {/* PodCore DHT Publishing */}
        <Grid.Column style={{ display: isPodWorkflowVisible("podcore-dht-publishing") ? undefined : "none" }} width={16}>
          <Card id="podcore-dht-publishing" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="podcast" />
                PodCore DHT Publishing
              </Card.Header>
              <Card.Description>
                Publish and manage pod metadata on the decentralized DHT for
                discovery
              </Card.Description>
              <PodWorkflowNotice title="Publishes pod metadata">
                Publishing or updating a listed pod can make pod identifiers,
                tags, focus content IDs, and descriptive metadata discoverable
                by other mesh participants.
              </PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header>Retrieve DHT metadata first</Message.Header>
                <p>
                  Metadata retrieval and publishing statistics are read-only.
                  Publishing and unpublishing pod metadata are grouped below as
                  advanced DHT mutation controls.
                </p>
              </Message>
              {/* Retrieve Pod Metadata */}
              <Header size="small">Retrieve Pod Metadata</Header>
              <Form>
                <Form.Input
                  label="Pod ID"
                  onChange={(e) => setPodMetadataToRetrieve(e.target.value)}
                  placeholder="pod:artist:mb:daft-punk-hash"
                  value={podMetadataToRetrieve}
                />
                <Button
                  tooltip="Query the DHT for this pod’s signed metadata so you can inspect the record participants may discover. This is a manual lookup."
                  disabled={
                    retrievingPodMetadata || !podMetadataToRetrieve.trim()
                  }
                  loading={retrievingPodMetadata}
                  onClick={handleRetrievePodMetadata}
                >
                  Retrieve Metadata
                </Button>
              </Form>

              {podMetadataResult && (
                <div style={{ marginTop: '1em' }}>
                  {podMetadataResult.error ? (
                    <Message error>
                      <p>
                        Failed to retrieve metadata: {podMetadataResult.error}
                      </p>
                    </Message>
                  ) : podMetadataResult.found ? (
                    <Message success>
                      <Message.Header>
                        Pod Metadata Retrieved
                      </Message.Header>
                      <p>
                        <strong>Pod ID:</strong>{' '}
                        {podMetadataResult.podId?.value ||
                          podMetadataResult.podId}
                        <br />
                        <strong>Signature Valid:</strong>{' '}
                        {podMetadataResult.isValidSignature ? 'Yes' : 'No'}
                        <br />
                        <strong>Retrieved:</strong>{' '}
                        {new Date(
                          podMetadataResult.retrievedAt,
                        ).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong>Expires:</strong>{' '}
                        {new Date(podMetadataResult.expiresAt).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong>Display Name:</strong>{' '}
                        {podMetadataResult.publishedPod?.displayName}
                        <br />
                        <strong>Members:</strong>{' '}
                        {podMetadataResult.publishedPod?.metadata?.memberCount ||
                          'Unknown'}
                      </p>
                    </Message>
                  ) : (
                    <Message warning>
                      <p>Pod not found in DHT</p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>

            <Card.Content>
              <details>
                <summary>Advanced DHT publishing controls</summary>
                <Message warning>
                  Publishing or unpublishing pod metadata changes DHT-visible
                  records. Confirm visibility, tags, focus content, and target
                  pod ID before applying changes.
                </Message>
                <Grid>
                  <Grid.Column width={8}>
                  <Header size="small">Publish Pod to DHT</Header>
                  <Form>
                    <Form.TextArea
                      label="Pod JSON"
                      onChange={(e) => setPodToPublish(e.target.value)}
                      placeholder='{"id": {"value": "pod:artist:mb:daft-punk-hash"}, "displayName": "Daft Punk Fans", "visibility": "Listed", "focusType": "ContentId", "focusContentId": {"domain": "audio", "type": "artist", "id": "daft-punk-hash"}, "tags": ["electronic", "french-house"], "createdAt": "2024-01-01T00:00:00Z", "createdBy": "alice", "metadata": {"description": "A community for Daft Punk fans", "memberCount": 150}}'
                      rows={6}
                      value={podToPublish}
                    />
                    <Button
                      tooltip="Publish this pod metadata to the DHT so mesh participants can discover it. Review its visibility, tags, and focus content before publishing."
                      disabled={publishingPod || !podToPublish.trim()}
                      loading={publishingPod}
                      onClick={handlePublishPod}
                      primary
                    >
                      Publish Pod
                    </Button>
                  </Form>

                  {podPublishingResult && (
                    <div style={{ marginTop: '1em' }}>
                      {podPublishingResult.error ? (
                        <Message error>
                          <p>
                            Failed to publish pod: {podPublishingResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message success>
                          <Message.Header>
                            Pod Published Successfully
                          </Message.Header>
                          <p>
                            <strong>Pod ID:</strong>{' '}
                            {podPublishingResult.podId?.value ||
                              podPublishingResult.podId}
                            <br />
                            <strong>DHT Key:</strong>{' '}
                            {podPublishingResult.dhtKey}
                            <br />
                            <strong>Published:</strong>{' '}
                            {new Date(
                              podPublishingResult.publishedAt,
                            ).toLocaleString(getRegionalLocale())}
                            <br />
                            <strong>Expires:</strong>{' '}
                            {new Date(
                              podPublishingResult.expiresAt,
                            ).toLocaleString(getRegionalLocale())}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  {/* Unpublish Pod */}
                  <Header size="small">Unpublish Pod from DHT</Header>
                  <Form>
                    <Form.Input
                      label="Pod ID"
                      onChange={(e) => setPodToUnpublish(e.target.value)}
                      placeholder="pod:artist:mb:daft-punk-hash"
                      value={podToUnpublish}
                    />
                    <Button
                      tooltip="Remove this pod’s metadata from the DHT so discovery no longer advertises it. Use this when you want to withdraw a listing."
                      color="red"
                      disabled={unpublishingPod || !podToUnpublish.trim()}
                      fluid
                      loading={unpublishingPod}
                      onClick={handleUnpublishPod}
                    >
                      Unpublish Pod
                    </Button>
                  </Form>

                  {podUnpublishResult && (
                    <div style={{ marginTop: '1em' }}>
                      {podUnpublishResult.error ? (
                        <Message error>
                          <p>
                            Failed to unpublish pod: {podUnpublishResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message success>
                          <p>Pod unpublished successfully from DHT</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>
              </Grid>
              </details>
            </Card.Content>

            {/* Pod Publishing Statistics */}
            <Card.Content>
              <Button.Group fluid>
                <Button
                  tooltip="Load publication counts and timing so you can review recent pod metadata publishing activity."
                  disabled={loadingPodStats}
                  loading={loadingPodStats}
                  onClick={handleLoadPodPublishingStats}
                  primary
                >
                  Load Pod Publishing Stats
                </Button>
              </Button.Group>

              {podPublishingStats && !podPublishingStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header>Pod Publishing Statistics</Message.Header>
                    <p>
                      <strong>Total Published:</strong>{' '}
                      {podPublishingStats.totalPublished}
                      <br />
                      <strong>Active Publications:</strong>{' '}
                      {podPublishingStats.activePublications}
                      <br />
                      <strong>Expired Publications:</strong>{' '}
                      {podPublishingStats.expiredPublications}
                      <br />
                      <strong>Failed Publications:</strong>{' '}
                      {podPublishingStats.failedPublications}
                      <br />
                      <strong>Avg Publish Time:</strong>{' '}
                      {podPublishingStats.averagePublishTime
                        ? `${podPublishingStats.averagePublishTime.totalMilliseconds.toFixed(0)}ms`
                        : 'N/A'}
                      <br />
                      <strong>Last Operation:</strong>{' '}
                      {podPublishingStats.lastPublishOperation
                        ? new Date(
                            podPublishingStats.lastPublishOperation,
                          ).toLocaleString(getRegionalLocale())
                        : 'Never'}
                    </p>
                    {podPublishingStats.publicationsByVisibility &&
                      Object.keys(podPublishingStats.publicationsByVisibility)
                        .length > 0 && (
                        <div style={{ marginTop: '0.5em' }}>
                          <strong>Publications by Visibility:</strong>
                          {Object.entries(
                            podPublishingStats.publicationsByVisibility,
                          ).map(([visibility, count]) => (
                            <Label
                              key={visibility}
                              size="tiny"
                              style={{ margin: '0.1em' }}
                            >
                              {visibility}: {count}
                            </Label>
                          ))}
                        </div>
                      )}
                  </Message>
                </div>
              )}

              {podPublishingStats?.error && (
                <Message
                  error
                  style={{ marginTop: '1em' }}
                >
                  <p>
                    Failed to load pod publishing stats:{' '}
                    {podPublishingStats.error}
                  </p>
                </Message>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Membership Management */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-membership-management") ? undefined : "none" }} width={16}>
          <Card id="pod-membership-management" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="users" />
                Pod Membership Management
              </Card.Header>
              <Card.Description>
                Manage signed membership records in DHT with role-based access
                control
              </Card.Description>
              <PodWorkflowNotice title="Publishes membership state">
                Membership records can reveal peer IDs, roles, bans, public
                keys, and pod participation history. Verify the record before
                publishing it.
              </PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header>Verify membership before changing it</Message.Header>
                <p>
                  Getting, verifying, and loading membership stats are read-only.
                  Publishing membership records, role changes, bans, and cleanup
                  are grouped below as advanced membership mutation controls.
                </p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  {/* Get Membership */}
                  <Header size="small">Get Membership Record</Header>
                  <Form>
                    <Form.Input
                      label="Pod ID"
                      onChange={(e) => setMembershipPodId(e.target.value)}
                      placeholder="pod:artist:mb:daft-punk-hash"
                      value={membershipPodId}
                    />
                    <Form.Input
                      label="Peer ID"
                      onChange={(e) => setMembershipPeerId(e.target.value)}
                      placeholder="alice"
                      value={membershipPeerId}
                    />
                    <Button.Group fluid>
                      <Button
                        tooltip="Look up the selected peer’s membership record for this pod so you can review its role and status."
                        disabled={
                          gettingMembership ||
                          !membershipPodId.trim() ||
                          !membershipPeerId.trim()
                        }
                        loading={gettingMembership}
                        onClick={handleGetMembership}
                      >
                        Get Membership
                      </Button>
                      <Button
                        tooltip="Verify the selected peer’s signed membership record before relying on its role or ban status."
                        disabled={
                          verifyingMembership ||
                          !membershipPodId.trim() ||
                          !membershipPeerId.trim()
                        }
                        loading={verifyingMembership}
                        onClick={handleVerifyMembership}
                      >
                        Verify Membership
                      </Button>
                    </Button.Group>
                  </Form>

                  {/* Membership Results */}
                  {membershipResult && (
                    <div style={{ marginTop: '1em' }}>
                      {membershipResult.error ? (
                        <Message error>
                          <p>
                            Failed to get membership: {membershipResult.error}
                          </p>
                        </Message>
                      ) : membershipResult.found ? (
                        <Message success>
                          <Message.Header>Membership Found</Message.Header>
                          <p>
                            <strong>Pod ID:</strong> {membershipResult.podId}
                            <br />
                            <strong>Peer ID:</strong> {membershipResult.peerId}
                            <br />
                            <strong>Role:</strong>{' '}
                            {membershipResult.signedRecord?.membership?.role}
                            <br />
                            <strong>Banned:</strong>{' '}
                            {membershipResult.signedRecord?.membership?.isBanned
                              ? 'Yes'
                              : 'No'}
                            <br />
                            <strong>Signature Valid:</strong>{' '}
                            {membershipResult.isValidSignature ? 'Yes' : 'No'}
                            <br />
                            <strong>Joined:</strong>{' '}
                            {membershipResult.signedRecord?.membership?.joinedAt
                              ? new Date(
                                  membershipResult.signedRecord.membership.joinedAt,
                                ).toLocaleString(getRegionalLocale())
                              : 'Unknown'}
                          </p>
                        </Message>
                      ) : (
                        <Message warning>
                          <p>Membership not found in DHT</p>
                        </Message>
                      )}
                    </div>
                  )}

                  {/* Verification Results */}
                  {membershipVerification && (
                    <div style={{ marginTop: '1em' }}>
                      {membershipVerification.error ? (
                        <Message error>
                          <p>
                            Failed to verify membership:{' '}
                            {membershipVerification.error}
                          </p>
                        </Message>
                      ) : (
                        <Message info>
                          <Message.Header>
                            Membership Verification
                          </Message.Header>
                          <p>
                            <strong>Valid Member:</strong>{' '}
                            {membershipVerification.isValidMember
                              ? 'Yes'
                              : 'No'}
                            <br />
                            <strong>Role:</strong>{' '}
                            {membershipVerification.role || 'None'}
                            <br />
                            <strong>Banned:</strong>{' '}
                            {membershipVerification.isBanned ? 'Yes' : 'No'}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  <details>
                    <summary>Advanced member mutation controls</summary>
                    <Message warning>
                      Banning members and changing roles publish membership
                      state for the selected pod and peer. Verify the current
                      membership record before applying changes.
                    </Message>
                  {/* Member Management */}
                  <Header size="small">Member Management</Header>

                  {/* Ban Member */}
                  <Form style={{ marginBottom: '1em' }}>
                    <Form.Input
                      label="Ban Reason (optional)"
                      onChange={(e) => setBanReason(e.target.value)}
                      placeholder="Violation of community rules"
                      value={banReason}
                    />
                    <Button
                      tooltip="Ban the selected peer from this pod after reviewing the membership record and reason. This publishes a membership change."
                      color="red"
                      disabled={
                        banningMember ||
                        !membershipPodId.trim() ||
                        !membershipPeerId.trim()
                      }
                      fluid
                      loading={banningMember}
                      onClick={handleBanMember}
                    >
                      Ban Member
                    </Button>
                  </Form>

                  {/* Change Role */}
                  <Form>
                    <Form.Select
                      label="New Role"
                      onChange={(e, { value }) => setNewRole(value)}
                      options={[
                        { key: 'member', text: 'Member', value: 'member' },
                        { key: 'mod', text: 'Moderator', value: 'mod' },
                        { key: 'owner', text: 'Owner', value: 'owner' },
                      ]}
                      value={newRole}
                    />
                    <Button
                      tooltip="Change the selected peer’s pod role. Use this to grant or remove moderator or owner duties after verifying the peer."
                      color="blue"
                      disabled={
                        changingRole ||
                        !membershipPodId.trim() ||
                        !membershipPeerId.trim()
                      }
                      fluid
                      loading={changingRole}
                      onClick={handleChangeRole}
                    >
                      Change Role
                    </Button>
                  </Form>

                  {/* Management Results */}
                  {banResult && (
                    <Message
                      style={{ marginTop: '1em' }}
                      success
                    >
                      <p>Member banned successfully</p>
                    </Message>
                  )}

                  {roleChangeResult && (
                    <Message
                      style={{ marginTop: '1em' }}
                      success
                    >
                      <p>Member role changed successfully</p>
                    </Message>
                  )}
                  </details>
                </Grid.Column>
              </Grid>
            </Card.Content>

            {/* Publish Membership */}
            <Card.Content>
              <details>
                <summary>Advanced membership publishing controls</summary>
                <Message warning>
                  Publishing membership records can expose peer IDs, roles,
                  public keys, ban state, and pod participation history.
                </Message>
                <Header size="small">Publish Membership Record</Header>
                <Form>
                  <Form.TextArea
                    label="Membership Record JSON"
                    onChange={(e) => setMembershipRecord(e.target.value)}
                    placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "role": "member", "isBanned": false, "publicKey": "base64-ed25519-key", "joinedAt": "2024-01-01T00:00:00Z"}'
                    rows={4}
                    value={membershipRecord}
                  />
                  <Button
                    tooltip="Publish this signed membership record to the DHT so peers can verify participation and roles. Check peer IDs and key material first."
                    disabled={publishingMembership || !membershipRecord.trim()}
                    loading={publishingMembership}
                    onClick={handlePublishMembership}
                    primary
                  >
                    Publish Membership
                  </Button>
                </Form>

                {membershipPublishResult && (
                  <div style={{ marginTop: '1em' }}>
                    {membershipPublishResult.error ? (
                      <Message error>
                        <p>
                          Failed to publish membership:{' '}
                          {membershipPublishResult.error}
                        </p>
                      </Message>
                    ) : (
                      <Message success>
                        <Message.Header>
                          Membership Published Successfully
                        </Message.Header>
                        <p>
                          <strong>Pod ID:</strong>{' '}
                          {membershipPublishResult.podId}
                          <br />
                          <strong>Peer ID:</strong>{' '}
                          {membershipPublishResult.peerId}
                          <br />
                          <strong>DHT Key:</strong>{' '}
                          {membershipPublishResult.dhtKey}
                          <br />
                          <strong>Published:</strong>{' '}
                          {new Date(
                            membershipPublishResult.publishedAt,
                          ).toLocaleString(getRegionalLocale())}
                          <br />
                          <strong>Expires:</strong>{' '}
                          {new Date(
                            membershipPublishResult.expiresAt,
                          ).toLocaleString(getRegionalLocale())}
                        </p>
                      </Message>
                    )}
                  </div>
                )}
              </details>
            </Card.Content>

            {/* Membership Statistics */}
            <Card.Content>
              <Button.Group fluid>
                <Button
                  tooltip="Load membership counts and expiration state so you can decide whether cleanup is needed."
                  disabled={loadingMembershipStats}
                  loading={loadingMembershipStats}
                  onClick={handleLoadMembershipStats}
                  primary
                >
                  Load Membership Stats
                </Button>
              </Button.Group>

              <details style={{ marginTop: '1em' }}>
                <summary>Advanced membership cleanup controls</summary>
                <Message warning>
                  Cleanup removes expired membership records from local
                  membership state. Load stats before running cleanup.
                </Message>
                <Button
                  tooltip="Remove expired membership records from local state to clear stale entries. Review membership stats first."
                  color="orange"
                  onClick={handleCleanupMemberships}
                >
                  Cleanup Expired
                </Button>
              </details>

              {membershipStats && !membershipStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header>Membership Statistics</Message.Header>
                    <p>
                      <strong>Total Memberships:</strong>{' '}
                      {membershipStats.totalMemberships}
                      <br />
                      <strong>Active Memberships:</strong>{' '}
                      {membershipStats.activeMemberships}
                      <br />
                      <strong>Banned Memberships:</strong>{' '}
                      {membershipStats.bannedMemberships}
                      <br />
                      <strong>Expired Memberships:</strong>{' '}
                      {membershipStats.expiredMemberships}
                      <br />
                      <strong>Last Operation:</strong>{' '}
                      {membershipStats.lastOperation
                        ? new Date(
                            membershipStats.lastOperation,
                          ).toLocaleString(getRegionalLocale())
                        : 'Never'}
                    </p>
                    {membershipStats.membershipsByRole &&
                      Object.keys(membershipStats.membershipsByRole).length >
                        0 && (
                        <div style={{ marginTop: '0.5em' }}>
                          <strong>Memberships by Role:</strong>
                          {Object.entries(
                            membershipStats.membershipsByRole,
                          ).map(([role, count]) => (
                            <Label
                              key={role}
                              size="tiny"
                              style={{ margin: '0.1em' }}
                            >
                              {role}: {count}
                            </Label>
                          ))}
                        </div>
                      )}
                  </Message>
                </div>
              )}

              {membershipStats?.error && (
                <Message
                  error
                  style={{ marginTop: '1em' }}
                >
                  <p>
                    Failed to load membership stats: {membershipStats.error}
                  </p>
                </Message>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Membership Verification */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-membership-verification") ? undefined : "none" }} width={16}>
          <Card id="pod-membership-verification" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="shield" />
                Pod Membership Verification
              </Card.Header>
              <Card.Description>
                Verify membership status, message authenticity, and role
                permissions for pod security
              </Card.Description>
              <PodWorkflowNotice
                color="blue"
                icon="check circle"
                title="Read-only verification"
              >
                Verification checks should not mutate pod state, but pasted
                messages and membership records can still contain sensitive
                peer or signature data.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Membership Verification */}
            <Card.Content>
              <Header size="small">Verify Membership Status</Header>
              <Form>
                <Form.Group widths="equal">
                  <Form.Input
                    label="Pod ID"
                    onChange={(e) => setVerifyPodId(e.target.value)}
                    placeholder="pod:artist:mb:daft-punk-hash"
                    value={verifyPodId}
                  />
                  <Form.Input
                    label="Peer ID"
                    onChange={(e) => setVerifyPeerId(e.target.value)}
                    placeholder="alice"
                    value={verifyPeerId}
                  />
                </Form.Group>
                <Button
                  tooltip="Check the selected peer’s membership proof and signature for this pod before relying on the claimed membership."
                  disabled={
                    verifyingMembership ||
                    !verifyPodId.trim() ||
                    !verifyPeerId.trim()
                  }
                  fluid
                  loading={verifyingMembership}
                  onClick={handleVerifyPodMembership}
                >
                  Verify Membership
                </Button>
              </Form>

              {membershipVerificationResult && (
                <div style={{ marginTop: '1em' }}>
                  {membershipVerificationResult.error ? (
                    <Message error>
                      <p>
                        Failed to verify membership:{' '}
                        {membershipVerificationResult.error}
                      </p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>
                        Membership Verification Result
                      </Message.Header>
                      <p>
                        <strong>Valid Member:</strong>{' '}
                        {membershipVerificationResult.isValidMember
                          ? 'Yes'
                          : 'No'}
                        <br />
                        <strong>Role:</strong>{' '}
                        {membershipVerificationResult.role || 'None'}
                        <br />
                        <strong>Banned:</strong>{' '}
                        {membershipVerificationResult.isBanned ? 'Yes' : 'No'}
                      </p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>

            <Card.Content>
              <Grid>
                <Grid.Column width={8}>
                  {/* Message Verification */}
                  <Header size="small">Verify Message Authenticity</Header>
                  <Form>
                    <Form.TextArea
                      label="Pod Message JSON"
                      onChange={(e) => setMessageToVerify(e.target.value)}
                      placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello everyone!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                      rows={4}
                      value={messageToVerify}
                    />
                    <Button
                      tooltip="Validate the supplied message signature so you can detect altered or untrusted pod messages."
                      disabled={verifyingMessage || !messageToVerify.trim()}
                      fluid
                      loading={verifyingMessage}
                      onClick={handleVerifyMessage}
                    >
                      Verify Message
                    </Button>
                  </Form>

                  {messageVerificationResult && (
                    <div style={{ marginTop: '1em' }}>
                      {messageVerificationResult.error ? (
                        <Message error>
                          <p>
                            Failed to verify message:{' '}
                            {messageVerificationResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message info>
                          <Message.Header>
                            Message Verification Result
                          </Message.Header>
                          <p>
                            <strong>Valid:</strong>{' '}
                            {messageVerificationResult.isValid ? 'Yes' : 'No'}
                            <br />
                            <strong>From Valid Member:</strong>{' '}
                            {messageVerificationResult.isFromValidMember
                              ? 'Yes'
                              : 'No'}
                            <br />
                            <strong>Not Banned:</strong>{' '}
                            {messageVerificationResult.isNotBanned
                              ? 'Yes'
                              : 'No'}
                            <br />
                            <strong>Valid Signature:</strong>{' '}
                            {messageVerificationResult.hasValidSignature
                              ? 'Yes'
                              : 'No'}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  {/* Role Checking */}
                  <Header size="small">Check Role Permissions</Header>
                  <Form>
                    <Form.Group widths="equal">
                      <Form.Input
                        label="Pod ID"
                        onChange={(e) => setRoleCheckPodId(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={roleCheckPodId}
                      />
                      <Form.Input
                        label="Peer ID"
                        onChange={(e) => setRoleCheckPeerId(e.target.value)}
                        placeholder="alice"
                        value={roleCheckPeerId}
                      />
                    </Form.Group>
                    <Form.Select
                      label="Required Role"
                      onChange={(e, { value }) => setRequiredRole(value)}
                      options={[
                        { key: 'member', text: 'Member', value: 'member' },
                        { key: 'mod', text: 'Moderator', value: 'mod' },
                        { key: 'owner', text: 'Owner', value: 'owner' },
                      ]}
                      value={requiredRole}
                    />
                    <Button
                      tooltip="Check whether this peer has the required role in the selected pod before authorizing an operation."
                      disabled={
                        checkingRole ||
                        !roleCheckPodId.trim() ||
                        !roleCheckPeerId.trim()
                      }
                      fluid
                      loading={checkingRole}
                      onClick={handleCheckRole}
                    >
                      Check Role
                    </Button>
                  </Form>

                  {roleCheckResult && (
                    <div style={{ marginTop: '1em' }}>
                      {roleCheckResult.error ? (
                        <Message error>
                          <p>Failed to check role: {roleCheckResult.error}</p>
                        </Message>
                      ) : (
                        <Message>
                          <Message.Header>Role Check Result</Message.Header>
                          <p>
                            <strong>Has Required Role ({requiredRole}):</strong>{' '}
                            {roleCheckResult.hasRole ? 'Yes' : 'No'}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            {/* Verification Statistics */}
            <Card.Content>
              <Button.Group fluid>
                <Button
                  tooltip="Load local verification counts and timing so you can review membership and message signature checks."
                  disabled={loadingVerificationStats}
                  loading={loadingVerificationStats}
                  onClick={handleLoadVerificationStats}
                  primary
                >
                  Load Verification Stats
                </Button>
              </Button.Group>

              {verificationStats && !verificationStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header>Verification Statistics</Message.Header>
                    <p>
                      <strong>Total Verifications:</strong>{' '}
                      {verificationStats.totalVerifications}
                      <br />
                      <strong>Successful:</strong>{' '}
                      {verificationStats.successfulVerifications}
                      <br />
                      <strong>Failed Membership:</strong>{' '}
                      {verificationStats.failedMembershipChecks}
                      <br />
                      <strong>Failed Signatures:</strong>{' '}
                      {verificationStats.failedSignatureChecks}
                      <br />
                      <strong>Banned Rejections:</strong>{' '}
                      {verificationStats.bannedMemberRejections}
                      <br />
                      <strong>Avg Time:</strong>{' '}
                      {verificationStats.averageVerificationTimeMs.toFixed(2)}ms
                      <br />
                      <strong>Last Verification:</strong>{' '}
                      {verificationStats.lastVerification
                        ? new Date(
                            verificationStats.lastVerification,
                          ).toLocaleString(getRegionalLocale())
                        : 'Never'}
                    </p>
                  </Message>
                </div>
              )}

              {verificationStats?.error && (
                <Message
                  error
                  style={{ marginTop: '1em' }}
                >
                  <p>
                    Failed to load verification stats: {verificationStats.error}
                  </p>
                </Message>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Discovery */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-discovery") ? undefined : "none" }} width={16}>
          <Card id="pod-discovery" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="search" />
                Pod Discovery
              </Card.Header>
              <Card.Description>
                Discover pods via DHT using name slugs, tags, and content
                associations
              </Card.Description>
              <PodWorkflowNotice
                color="blue"
                icon="info circle"
                title="Mostly read-only discovery"
              >
                Search operations are read-only, but registering, updating,
                unregistering, or refreshing discovery data changes public pod
                discovery state.
              </PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message
                info
                size="small"
              >
                <Message.Header>Find pods first</Message.Header>
                Name, tag, content, and limited registry searches are the
                normal discovery path. Registry mutation controls are grouped
                below because they publish or remove public discovery records.
              </Message>
            </Card.Content>

            <Card.Content>
              <Grid>
                <Grid.Column width={4}>
                  {/* Discover by Name */}
                  <Header size="small">By Name</Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByName(e.target.value)}
                      placeholder="daft-punk-fans"
                      value={discoverByName}
                    />
                    <Button
                      tooltip="Run a manual discovery lookup for pods matching this name. Use it to find a specific community; the query contacts the pod discovery service."
                      disabled={discoveringByName || !discoverByName.trim()}
                      fluid
                      loading={discoveringByName}
                      onClick={handleDiscoverByName}
                    >
                      Discover
                    </Button>
                  </Form>

                  {nameDiscoveryResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {nameDiscoveryResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{nameDiscoveryResult.error}</p>
                        </Message>
                      ) : (
                        <Message
                          size="tiny"
                          success
                        >
                          <p>Found {nameDiscoveryResult.totalFound} pods</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover by Tag */}
                  <Header size="small">By Tag</Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByTag(e.target.value)}
                      placeholder="electronic"
                      value={discoverByTag}
                    />
                    <Button
                      tooltip="Run a manual discovery lookup for pods with this tag. Use it to browse a topic; the query contacts the pod discovery service."
                      disabled={discoveringByTag || !discoverByTag.trim()}
                      fluid
                      loading={discoveringByTag}
                      onClick={handleDiscoverByTag}
                    >
                      Discover
                    </Button>
                  </Form>

                  {tagDiscoveryResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {tagDiscoveryResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{tagDiscoveryResult.error}</p>
                        </Message>
                      ) : (
                        <Message
                          size="tiny"
                          success
                        >
                          <p>Found {tagDiscoveryResult.totalFound} pods</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover by Tags */}
                  <Header size="small">By Tags (AND)</Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverTags(e.target.value)}
                      placeholder="electronic,french-house"
                      value={discoverTags}
                    />
                    <Button
                      tooltip="Run a manual lookup for pods matching the entered tags. Use it to narrow discovery to a combination of topics."
                      disabled={discoveringByTags || !discoverTags.trim()}
                      fluid
                      loading={discoveringByTags}
                      onClick={handleDiscoverByTags}
                    >
                      Discover
                    </Button>
                  </Form>

                  {tagsDiscoveryResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {tagsDiscoveryResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{tagsDiscoveryResult.error}</p>
                        </Message>
                      ) : (
                        <Message
                          size="tiny"
                          success
                        >
                          <p>Found {tagsDiscoveryResult.totalFound} pods</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover All */}
                  <Header size="small">All Pods</Header>
                  <Form>
                    <Form.Input
                      label="Limit"
                      max="1000"
                      min="1"
                      onChange={(e) =>
                        setDiscoverLimit(Number.parseInt(e.target.value) || 50)
                      }
                      type="number"
                      value={discoverLimit}
                    />
                    <Button
                      tooltip="Browse a bounded sample of discoverable pods. This performs a manual discovery request using the selected result limit."
                      disabled={discoveringAll}
                      fluid
                      loading={discoveringAll}
                      onClick={handleDiscoverAll}
                    >
                      Discover
                    </Button>
                  </Form>

                  {allDiscoveryResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {allDiscoveryResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{allDiscoveryResult.error}</p>
                        </Message>
                      ) : (
                        <Message
                          size="tiny"
                          success
                        >
                          <p>Found {allDiscoveryResult.totalFound} pods</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            <Card.Content>
              <Grid>
                <Grid.Column width={8}>
                  {/* Discover by Content */}
                  <Header size="small">By Content ID</Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByContent(e.target.value)}
                      placeholder="content:audio:artist:daft-punk"
                      value={discoverByContent}
                    />
                    <Button
                      tooltip="Find pods linked to this content ID so you can browse communities about the item. This is a manual discovery lookup."
                      disabled={
                        discoveringByContent || !discoverByContent.trim()
                      }
                      fluid
                      loading={discoveringByContent}
                      onClick={handleDiscoverByContent}
                    >
                      Discover
                    </Button>
                  </Form>

                  {contentDiscoveryResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {contentDiscoveryResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{contentDiscoveryResult.error}</p>
                        </Message>
                      ) : (
                        <Message
                          size="tiny"
                          success
                        >
                          <p>Found {contentDiscoveryResult.totalFound} pods</p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  {/* Discovery Stats */}
                  <Header size="small">Discovery Statistics</Header>
                  <Button.Group fluid>
                    <Button
                      tooltip="Load discovery index counts and freshness so you can review the current local index state."
                      disabled={loadingDiscoveryStats}
                      loading={loadingDiscoveryStats}
                      onClick={handleLoadDiscoveryStats}
                    >
                      Load Stats
                    </Button>
                    <Button
                      tooltip="Refresh the pod discovery index and expire stale entries. Use this when discovery results appear out of date."
                      color="blue"
                      onClick={handleRefreshDiscovery}
                    >
                      Refresh
                    </Button>
                  </Button.Group>

                  {discoveryStats && !discoveryStats.error && (
                    <div style={{ marginTop: '0.5em' }}>
                      <Message size="tiny">
                        <p>
                          <strong>Registered Pods:</strong>{' '}
                          {discoveryStats.totalRegisteredPods}
                          <br />
                          <strong>Active Entries:</strong>{' '}
                          {discoveryStats.activeDiscoveryEntries}
                          <br />
                          <strong>Expired Entries:</strong>{' '}
                          {discoveryStats.expiredEntries}
                          <br />
                          <strong>Avg Search Time:</strong>{' '}
                          {discoveryStats.averageDiscoveryTime?.totalMilliseconds.toFixed(
                            0,
                          )}
                          ms
                        </p>
                      </Message>
                    </div>
                  )}

                  {discoveryStats?.error && (
                    <Message
                      error
                      size="tiny"
                      style={{ marginTop: '0.5em' }}
                    >
                      <p>{discoveryStats.error}</p>
                    </Message>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            <Card.Content>
              <details>
                <summary>
                  Advanced registry publishing controls
                </summary>
                <Message
                  size="small"
                  warning
                >
                  Registering, unregistering, updating, or refreshing pod
                  discovery entries changes public DHT-visible pod metadata.
                </Message>
                <Grid stackable>
                  <Grid.Column width={8}>
                    <Header size="small">Register Pod for Discovery</Header>
                    <Form>
                      <Form.TextArea
                        label="Pod JSON (must have Visibility: Listed)"
                        onChange={(e) => setPodToRegister(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "name": "Daft Punk Fans", "visibility": "Listed", "focusContentId": "content:audio:artist:daft-punk", "tags": ["electronic", "french-house"]}'
                        rows={3}
                        value={podToRegister}
                      />
                      <Button
                        tooltip="Publish this pod to the discovery index so others can find it. Check its public metadata and visibility before registering."
                        disabled={registeringPod || !podToRegister.trim()}
                        loading={registeringPod}
                        onClick={handleRegisterPodForDiscovery}
                        primary
                      >
                        Register Pod
                      </Button>
                    </Form>

                    {podRegistrationResult && (
                      <div style={{ marginTop: '1em' }}>
                        {podRegistrationResult.error ? (
                          <Message error>
                            <p>
                              Failed to register pod:{' '}
                              {podRegistrationResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              Pod Registered for Discovery
                            </Message.Header>
                            <p>
                              <strong>Pod ID:</strong>{' '}
                              {podRegistrationResult.podId}
                              <br />
                              <strong>Discovery Keys:</strong>{' '}
                              {podRegistrationResult.discoveryKeys?.join(', ')}
                              <br />
                              <strong>Registered:</strong>{' '}
                              {new Date(
                                podRegistrationResult.registeredAt,
                              ).toLocaleString(getRegionalLocale())}
                              <br />
                              <strong>Expires:</strong>{' '}
                              {new Date(
                                podRegistrationResult.expiresAt,
                              ).toLocaleString(getRegionalLocale())}
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">Unregister Pod from Discovery</Header>
                    <Form>
                      <Form.Input
                        label="Pod ID"
                        onChange={(e) => setPodToUnregister(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={podToUnregister}
                      />
                      <Button
                        tooltip="Remove this pod from the discovery index so future lookups stop returning it."
                        color="red"
                        disabled={unregisteringPod || !podToUnregister.trim()}
                        loading={unregisteringPod}
                        onClick={handleUnregisterPodFromDiscovery}
                      >
                        Unregister Pod
                      </Button>
                    </Form>

                    {podUnregistrationResult && (
                      <div style={{ marginTop: '1em' }}>
                        {podUnregistrationResult.error ? (
                          <Message error>
                            <p>
                              Failed to unregister pod:{' '}
                              {podUnregistrationResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <p>Pod unregistered from discovery successfully</p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>
                </Grid>
              </details>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Join/Leave */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-join-leave") ? undefined : "none" }} width={16}>
          <Card id="pod-join-leave" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="user plus" />
                Pod Join/Leave Operations
              </Card.Header>
              <Card.Description>
                Manage signed pod membership operations with cryptographic
                Ed25519 verification and role-based approvals
              </Card.Description>
              <PodWorkflowNotice title="Publishes join and leave events">
                Join and leave requests can expose peer IDs, requested roles,
                public keys, signatures, and operator-provided messages.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Pending Requests */}
            <Card.Content>
              <Message info>
                <Message.Header>Review pending requests first</Message.Header>
                <p>
                  Loading pending join and leave requests only reads local pod
                  state. The signed request and approval actions below publish
                  membership events.
                </p>
                <p>
                  In Enforce mode, signatures must use the
                  <code>ed25519:&lt;base64 signature&gt;</code> format over
                  the canonical join/leave payload and the supplied public key.
                </p>
              </Message>
              <Form>
                <Form.Input
                  label="Pod ID"
                  onChange={(e) => setPendingPodId(e.target.value)}
                  placeholder="pod:artist:mb:daft-punk-hash"
                  value={pendingPodId}
                />
                <Button
                  tooltip="Load pending join and leave requests for this pod so you can review them before accepting a membership change."
                  disabled={loadingPendingRequests || !pendingPodId.trim()}
                  loading={loadingPendingRequests}
                  onClick={handleLoadPendingRequests}
                >
                  Load Pending Requests
                </Button>
              </Form>

              {pendingJoinRequests && !pendingJoinRequests.error && (
                <div style={{ marginTop: '0.5em' }}>
                  <Message size="tiny">
                    <strong>Join Requests:</strong>{' '}
                    {pendingJoinRequests.pendingJoinRequests?.length || 0}
                  </Message>
                </div>
              )}

              {pendingLeaveRequests && !pendingLeaveRequests.error && (
                <div style={{ marginTop: '0.5em' }}>
                  <Message size="tiny">
                    <strong>Leave Requests:</strong>{' '}
                    {pendingLeaveRequests.pendingLeaveRequests?.length || 0}
                  </Message>
                </div>
              )}

              {(pendingJoinRequests?.error ||
                pendingLeaveRequests?.error) && (
                <Message
                  error
                  size="tiny"
                  style={{ marginTop: '0.5em' }}
                >
                  <p>Failed to load pending requests</p>
                </Message>
              )}
            </Card.Content>

            <Card.Content>
              <details>
                <summary>Advanced signed membership event controls</summary>
                <Message warning>
                  These controls submit signed JSON payloads and can publish
                  pod membership changes. Use them after checking the pending
                  request list for the target pod.
                </Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small">Request to Join Pod</Header>
                    <Form>
                      <Form.TextArea
                        label="Join Request JSON (signed by requester)"
                        onChange={(e) => setJoinRequestData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "requestedRole": "member", "publicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "nonce": "unique-request-nonce", "message": "Please let me join!"}'
                        rows={4}
                        value={joinRequestData}
                      />
                      <Button
                        tooltip="Submit a signed request to join the pod. Use this to ask its owner or moderators for membership; the request includes the supplied identity details."
                        disabled={requestingJoin || !joinRequestData.trim()}
                        loading={requestingJoin}
                        onClick={handleRequestJoin}
                        primary
                      >
                        Submit Join Request
                      </Button>
                    </Form>

                    {joinRequestResult && (
                      <div style={{ marginTop: '1em' }}>
                        {joinRequestResult.error ? (
                          <Message error>
                            <p>
                              Failed to submit join request:{' '}
                              {joinRequestResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              Join Request Submitted
                            </Message.Header>
                            <p>
                              <strong>Pod ID:</strong> {joinRequestResult.podId}
                              <br />
                              <strong>Peer ID:</strong>{' '}
                              {joinRequestResult.peerId}
                              <br />
                              <strong>Status:</strong>{' '}
                              {joinRequestResult.success
                                ? 'Pending approval'
                                : 'Failed'}
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">Accept Join Request</Header>
                    <Form>
                      <Form.TextArea
                        label="Acceptance JSON (signed by owner/mod)"
                        onChange={(e) => setAcceptanceData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "acceptedRole": "member", "acceptorPeerId": "bob", "acceptorPublicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Welcome!"}'
                        rows={4}
                        value={acceptanceData}
                      />
                      <Button
                        tooltip="Accept the signed join request and publish the membership change so the peer can participate. Verify the peer and requested role first."
                        disabled={acceptingJoin || !acceptanceData.trim()}
                        loading={acceptingJoin}
                        onClick={handleAcceptJoin}
                        positive
                      >
                        Accept Join
                      </Button>
                    </Form>

                    {acceptanceResult && (
                      <div style={{ marginTop: '0.5em' }}>
                        {acceptanceResult.error ? (
                          <Message
                            error
                            size="tiny"
                          >
                            <p>{acceptanceResult.error}</p>
                          </Message>
                        ) : (
                          <Message
                            size="tiny"
                            success
                          >
                            <p>Join accepted successfully</p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">Request to Leave Pod</Header>
                    <Form>
                      <Form.TextArea
                        label="Leave Request JSON (signed by member)"
                        onChange={(e) => setLeaveRequestData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "publicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Goodbye!"}'
                        rows={4}
                        value={leaveRequestData}
                      />
                      <Button
                        tooltip="Submit a signed request to leave the pod so its owner or moderators can review the membership change."
                        disabled={requestingLeave || !leaveRequestData.trim()}
                        loading={requestingLeave}
                        onClick={handleRequestLeave}
                      >
                        Submit Leave Request
                      </Button>
                    </Form>

                    {leaveRequestResult && (
                      <div style={{ marginTop: '0.5em' }}>
                        {leaveRequestResult.error ? (
                          <Message
                            error
                            size="tiny"
                          >
                            <p>{leaveRequestResult.error}</p>
                          </Message>
                        ) : (
                          <Message
                            size="tiny"
                            success
                          >
                            <p>Leave request submitted</p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">
                      Accept Leave Request (Owner/Mod Only)
                    </Header>
                    <Form>
                      <Form.TextArea
                        label="Leave Acceptance JSON (signed by owner/mod)"
                        onChange={(e) => setAcceptanceData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "acceptorPeerId": "bob", "acceptorPublicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Farewell!"}'
                        rows={4}
                        value={acceptanceData}
                      />
                      <Button
                        tooltip="Accept the signed leave request and publish the membership removal. Verify the peer and request before accepting."
                        disabled={acceptingLeave || !acceptanceData.trim()}
                        loading={acceptingLeave}
                        negative
                        onClick={handleAcceptLeave}
                      >
                        Accept Leave
                      </Button>
                    </Form>

                    {leaveAcceptanceResult && (
                      <div style={{ marginTop: '0.5em' }}>
                        {leaveAcceptanceResult.error ? (
                          <Message
                            error
                            size="tiny"
                          >
                            <p>{leaveAcceptanceResult.error}</p>
                          </Message>
                        ) : (
                          <Message
                            size="tiny"
                            success
                          >
                            <p>Leave accepted successfully</p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>
                </Grid>
              </details>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Message Routing */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-message-routing") ? undefined : "none" }} width={16}>
          <Card id="pod-message-routing" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="send" />
                Pod Message Routing
              </Card.Header>
              <Card.Description>
                Decentralized message routing via overlay network with fanout
                and deduplication for reliable pod communication
              </Card.Description>
              <PodWorkflowNotice title="Sends pod messages">
                Routing actions can transmit message bodies and sender
                identifiers to selected peers or overlay routes. Use
                deduplication checks before resending.
              </PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header>Check routing state before sending</Message.Header>
                <p>
                  Deduplication checks and routing statistics are read-only.
                  Sending messages, marking messages as seen, and cleanup are
                  grouped below as advanced routing controls.
                </p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  <Header size="small">Message Deduplication</Header>
                  <Form>
                    <Form.Group widths="equal">
                      <Form.Input
                        label="Message ID"
                        onChange={(e) => setCheckMessageId(e.target.value)}
                        placeholder="msg123"
                        value={checkMessageId}
                      />
                      <Form.Input
                        label="Pod ID"
                        onChange={(e) => setCheckPodId(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={checkPodId}
                      />
                    </Form.Group>
                    <Button
                      tooltip="Check whether a seen receipt exists for this message and pod before registering another one."
                      disabled={
                        checkingMessageSeen ||
                        !checkMessageId.trim() ||
                        !checkPodId.trim()
                      }
                      fluid
                      loading={checkingMessageSeen}
                      onClick={handleCheckMessageSeen}
                    >
                      Check Seen
                    </Button>
                  </Form>

                  {messageSeenResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {messageSeenResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{messageSeenResult.error}</p>
                        </Message>
                      ) : (
                        <Message size="tiny">
                          <p>
                            Message{' '}
                            {messageSeenResult.isSeen
                              ? 'has been'
                              : 'has not been'}{' '}
                            seen in pod {messageSeenResult.podId}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  <Header size="small">Routing Statistics</Header>
                  <Button
                    tooltip="Load message-routing counts and outcomes so you can review recent Pod delivery activity."
                    disabled={loadingRoutingStats}
                    fluid
                    loading={loadingRoutingStats}
                    onClick={handleLoadRoutingStats}
                    primary
                  >
                    Load Routing Stats
                  </Button>

                  {routingStats && !routingStats.error && (
                    <div style={{ marginTop: '1em' }}>
                      <Message>
                        <Message.Header>Message Routing Statistics</Message.Header>
                        <p>
                          <strong>Total Messages Routed:</strong>{' '}
                          {routingStats.totalMessagesRouted}
                          <br />
                          <strong>Total Routing Attempts:</strong>{' '}
                          {routingStats.totalRoutingAttempts}
                          <br />
                          <strong>Successful Routes:</strong>{' '}
                          {routingStats.successfulRoutingCount}
                          <br />
                          <strong>Failed Routes:</strong>{' '}
                          {routingStats.failedRoutingCount}
                          <br />
                          <strong>Avg Routing Time:</strong>{' '}
                          {routingStats.averageRoutingTimeMs.toFixed(2)}ms
                          <br />
                          <strong>Deduplication Items:</strong>{' '}
                          {routingStats.activeDeduplicationItems}
                          <br />
                          <strong>Bloom Filter Fill:</strong>{' '}
                          {(routingStats.bloomFilterFillRatio * 100).toFixed(1)}%
                          <br />
                          <strong>Est. False Positive:</strong>{' '}
                          {(routingStats.estimatedFalsePositiveRate * 100).toFixed(4)}%
                          <br />
                          <strong>Last Operation:</strong>{' '}
                          {routingStats.lastRoutingOperation
                            ? new Date(
                                routingStats.lastRoutingOperation,
                              ).toLocaleString(getRegionalLocale())
                            : 'Never'}
                        </p>
                      </Message>
                    </div>
                  )}

                  {routingStats?.error && (
                    <Message
                      error
                      style={{ marginTop: '1em' }}
                    >
                      <p>Failed to load routing stats: {routingStats.error}</p>
                    </Message>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            <Card.Content>
              <details>
                <summary>Advanced message routing controls</summary>
                <Message warning>
                  Routing sends message bodies and sender identifiers to pod
                  peers or overlay routes. Confirm deduplication state before
                  resending messages.
                </Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small">Manual Message Routing</Header>
                    <Form>
                      <Form.TextArea
                        label="Pod Message JSON"
                        onChange={(e) => setRouteMessageData(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                        rows={4}
                        value={routeMessageData}
                      />
                      <Button
                        tooltip="Route this message through the pod messaging service to its eligible recipients. Use this to deliver a message to the pod."
                        disabled={routingMessage || !routeMessageData.trim()}
                        loading={routingMessage}
                        onClick={handleRouteMessage}
                        primary
                      >
                        Route Message
                      </Button>
                    </Form>

                    {routingResult && (
                      <div style={{ marginTop: '1em' }}>
                        {routingResult.error ? (
                          <Message error>
                            <p>Failed to route message: {routingResult.error}</p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              Message Routed Successfully
                            </Message.Header>
                            <p>
                              <strong>Message ID:</strong>{' '}
                              {routingResult.messageId}
                              <br />
                              <strong>Pod ID:</strong> {routingResult.podId}
                              <br />
                              <strong>Target Peers:</strong>{' '}
                              {routingResult.targetPeerCount}
                              <br />
                              <strong>Successfully Routed:</strong>{' '}
                              {routingResult.successfullyRoutedCount}
                              <br />
                              <strong>Failed:</strong>{' '}
                              {routingResult.failedRoutingCount}
                              <br />
                              <strong>Duration:</strong>{' '}
                              {routingResult.routingDuration?.totalMilliseconds?.toFixed(
                                0,
                              )}
                              ms
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">Route to Specific Peers</Header>
                    <Form>
                      <Form.TextArea
                        label="Pod Message JSON"
                        onChange={(e) => setRouteToPeersMessage(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Direct message", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                        rows={3}
                        value={routeToPeersMessage}
                      />
                      <Form.Input
                        label="Target Peer IDs (comma-separated)"
                        onChange={(e) => setRouteToPeersIds(e.target.value)}
                        placeholder="bob,charlie,diana"
                        value={routeToPeersIds}
                      />
                      <Button
                        tooltip="Route this message only to the listed peer IDs. Confirm the recipients because each selected peer receives the payload."
                        disabled={
                          routingToPeers ||
                          !routeToPeersMessage.trim() ||
                          !routeToPeersIds.trim()
                        }
                        fluid
                        loading={routingToPeers}
                        onClick={handleRouteMessageToPeers}
                      >
                        Route to Peers
                      </Button>
                    </Form>

                    {routingToPeersResult && (
                      <div style={{ marginTop: '0.5em' }}>
                        {routingToPeersResult.error ? (
                          <Message
                            error
                            size="tiny"
                          >
                            <p>{routingToPeersResult.error}</p>
                          </Message>
                        ) : (
                          <Message
                            info
                            size="tiny"
                          >
                            <p>
                              Routed to{' '}
                              {routingToPeersResult.successfullyRoutedCount}/
                              {routingToPeersResult.targetPeerCount} peers
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>
                </Grid>
              </details>
            </Card.Content>

            <Card.Content>
              <details>
                <summary>Advanced seen-state cleanup controls</summary>
                <Message warning>
                  Marking messages as seen and cleanup mutate local routing
                  deduplication state. Use them only after checking the target
                  message and pod IDs.
                </Message>
                <Button
                  tooltip="Record a seen receipt for this message and pod so the message state reflects that it was observed."
                  color="blue"
                  disabled={!checkMessageId.trim() || !checkPodId.trim()}
                  onClick={handleRegisterMessageSeen}
                >
                  Mark Seen
                </Button>
                <Button
                  tooltip="Remove expired seen-message receipts from local state to clear stale routing records."
                  color="red"
                  onClick={handleCleanupSeenMessages}
                >
                  Cleanup Seen Messages
                </Button>
              </details>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Message Storage */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-message-storage") ? undefined : "none" }} width={16}>
          <Card id="pod-message-storage" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="database" />
                Pod Message Storage
              </Card.Header>
              <Card.Description>
                SQLite-backed message storage with full-text search and
                retention policies
              </Card.Description>
              <PodWorkflowNotice title="Mutates local message storage">
                Cleanup, rebuild, and vacuum actions affect local pod message
                storage. Search and count actions are read-only.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Message Storage */}
            <Card.Content>
              <Header size="small">Storage Review</Header>
              <Message info>
                <Message.Header>Review storage before maintenance</Message.Header>
                <p>
                  Storage statistics and message search are read-only.
                  Cleanup, index rebuild, and vacuum operations are grouped
                  below as advanced local maintenance actions.
                </p>
              </Message>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip="Load local message-storage counts so you can review database usage before cleanup or maintenance."
                  color="teal"
                  loading={storageStatsLoading}
                  onClick={() => handleGetStorageStats()}
                  size="small"
                >
                  Get Storage Stats
                </Button>
              </div>

              <details style={{ marginBottom: '1em' }}>
                <summary>Advanced storage maintenance controls</summary>
                <Message warning>
                  Cleanup, search-index rebuild, and vacuum operations mutate
                  local pod message storage. Review storage stats before
                  running maintenance.
                </Message>
                <Button
                  tooltip="Permanently remove local pod messages older than 30 days. Use this to reclaim storage after reviewing the retention period."
                  color="purple"
                  loading={cleanupLoading}
                  onClick={() => handleCleanupMessages()}
                  size="small"
                >
                  Cleanup Old Messages (30 days)
                </Button>

                <Button
                  tooltip="Rebuild the local message search index from stored messages if search results are stale or incomplete."
                  color="blue"
                  loading={rebuildIndexLoading}
                  onClick={() => handleRebuildSearchIndex()}
                  size="small"
                >
                  Rebuild Search Index
                </Button>

                <Button
                  tooltip="Run SQLite vacuum to compact the local message database and reclaim unused file space. This may take time."
                  color="orange"
                  loading={vacuumLoading}
                  onClick={() => handleVacuumDatabase()}
                  size="small"
                >
                  Vacuum Database
                </Button>
              </details>

              {storageStats && (
                <Message
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header>Message Storage Statistics</Message.Header>
                  <p>
                    <strong>Total Messages:</strong>{' '}
                    {storageStats.totalMessages?.toLocaleString(getRegionalLocale()) || 0}
                    <br />
                    <strong>Estimated Size:</strong>{' '}
                    {(storageStats.totalSizeBytes / (1_024 * 1_024)).toFixed(2)}{' '}
                    MB
                    <br />
                    <strong>Oldest Message:</strong>{' '}
                    {storageStats.oldestMessage
                      ? new Date(storageStats.oldestMessage).toLocaleString(getRegionalLocale())
                      : 'None'}
                    <br />
                    <strong>Newest Message:</strong>{' '}
                    {storageStats.newestMessage
                      ? new Date(storageStats.newestMessage).toLocaleString(getRegionalLocale())
                      : 'None'}
                    <br />
                    <strong>Pods with Messages:</strong>{' '}
                    {Object.keys(storageStats.messagesPerPod || {}).length}
                    <br />
                    <strong>Active Channels:</strong>{' '}
                    {Object.keys(storageStats.messagesPerChannel || {}).length}
                  </p>
                </Message>
              )}

              <Header size="small">Message Search</Header>
              <Input
                action={
                  <Button
                    tooltip="Search stored pod messages locally for the entered text. Use this to find prior messages without contacting peers."
                    color="green"
                    disabled={!searchQuery.trim()}
                    loading={searchLoading}
                    onClick={() => handleSearchMessages()}
                  >
                    Search
                  </Button>
                }
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search messages..."
                style={{ marginBottom: '1em', width: '100%' }}
                value={searchQuery}
              />

              {searchResults && searchResults.length > 0 && (
                <Message size="small">
                  <Message.Header>
                    Search Results ({searchResults.length})
                  </Message.Header>
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    {searchResults.map((message, index) => (
                      <div
                        key={index}
                        style={{
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          marginBottom: '0.5em',
                          padding: '0.5em',
                        }}
                      >
                        <small style={{ color: '#666' }}>
                          {new Date(message.timestampUnixMs).toLocaleString(getRegionalLocale())} •{' '}
                          {message.senderPeerId} • {message.channelId}
                        </small>
                        <div style={{ marginTop: '0.25em' }}>
                          {message.body}
                        </div>
                      </div>
                    ))}
                  </div>
                </Message>
              )}

              {searchResults && searchResults.length === 0 && searchQuery && (
                <Message
                  size="small"
                  warning
                >
                  No messages found matching "{searchQuery}"
                </Message>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Message Backfill */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-message-backfill") ? undefined : "none" }} width={16}>
          <Card id="pod-message-backfill" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="sync" />
                Pod Message Backfill
              </Card.Header>
              <Card.Description>
                Synchronize missed messages when peers rejoin pods
              </Card.Description>
              <PodWorkflowNotice title="Syncs local pod state">
                Backfill sync uses last-seen timestamps to request missed
                messages. Confirm the target pod before syncing all channels.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Message Backfill */}
            <Card.Content>
              <Header size="small">Backfill Management</Header>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip="Load local backfill status so you can see which pod histories may need to catch up."
                  color="purple"
                  loading={backfillStatsLoading}
                  onClick={() => handleGetBackfillStats()}
                  size="small"
                >
                  Get Backfill Stats
                </Button>
              </div>

              {backfillStats && (
                <Message
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header>Backfill Statistics</Message.Header>
                  <p>
                    <strong>Requests Sent:</strong>{' '}
                    {backfillStats.totalBackfillRequestsSent?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong>Requests Received:</strong>{' '}
                    {backfillStats.totalBackfillRequestsReceived?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong>Messages Backfilled:</strong>{' '}
                    {backfillStats.totalMessagesBackfilled?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong>Data Transferred:</strong>{' '}
                    {(
                      backfillStats.totalBackfillBytesTransferred /
                      (1_024 * 1_024)
                    ).toFixed(2)}{' '}
                    MB
                    <br />
                    <strong>Avg Duration:</strong>{' '}
                    {backfillStats.averageBackfillDurationMs?.toFixed(2) || 0}ms
                    <br />
                    <strong>Last Operation:</strong>{' '}
                    {backfillStats.lastBackfillOperation
                      ? new Date(
                          backfillStats.lastBackfillOperation,
                        ).toLocaleString(getRegionalLocale())
                      : 'Never'}
                  </p>
                </Message>
              )}

              <Header size="small">Pod Backfill Review</Header>
              <Input
                action={
                  <Button
                    tooltip="Read the latest stored message timestamps for this pod so you can inspect its current history position."
                    color="blue"
                    disabled={!backfillPodId.trim()}
                    onClick={() => handleGetLastSeenTimestamps()}
                  >
                    Get Timestamps
                  </Button>
                }
                onChange={(e) => setBackfillPodId(e.target.value)}
                placeholder="Pod ID for backfill sync"
                style={{ marginBottom: '1em', width: '100%' }}
                value={backfillPodId}
              />

              <details style={{ marginBottom: '1em' }}>
                <summary>Advanced backfill sync controls</summary>
                <Message warning>
                  Backfill sync can request missed messages for the selected
                  pod. Confirm timestamps and pod ID before starting sync.
                </Message>
                <Button
                  tooltip="Request missing message history for this pod from its backfill sources. Run it manually when history is missing; it can transfer data over the network."
                  color="green"
                  disabled={!backfillPodId.trim()}
                  loading={syncBackfillLoading}
                  onClick={() => handleSyncPodBackfill()}
                >
                  Sync Backfill
                </Button>
              </details>

              {Object.keys(asObject(lastSeenTimestamps)).length > 0 && (
                  <Message size="small">
                    <Message.Header>
                      Last Seen Timestamps for Pod {backfillPodId}
                    </Message.Header>
                    <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                      {Object.entries(asObject(lastSeenTimestamps)).map(
                        ([channelId, timestamp]) => (
                          <div
                            key={channelId}
                            style={{ marginBottom: '0.25em' }}
                          >
                            <strong>{channelId}:</strong>{' '}
                            {new Date(timestamp).toLocaleString(getRegionalLocale())}
                          </div>
                        ),
                      )}
                    </div>
                  </Message>
                )}

              {lastSeenTimestamps &&
                Object.keys(lastSeenTimestamps).length === 0 && (
                  <Message
                    info
                    size="small"
                  >
                    No last seen timestamps recorded for pod {backfillPodId}
                  </Message>
                )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Channel Management */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-channel-management") ? undefined : "none" }} width={16}>
          <Card id="pod-channel-management" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="hashtag" />
                Pod Channel Management
              </Card.Header>
              <Card.Description>
                Create, update, and manage channels within pods for organized
                messaging
              </Card.Description>
              <PodWorkflowNotice title="Mutates pod structure">
                Channel create, update, and delete actions change how pod
                messages are organized. Deleting channels can disrupt routing
                and history workflows.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Channel Management */}
            <Card.Content>
              <Header size="small">Load Pod Channels</Header>
              <Message info>
                <Message.Header>Review channels before changing them</Message.Header>
                <p>
                  Loading channels only reads local pod structure. Create,
                  edit, and delete controls are grouped below as advanced
                  operations because they change pod routing and history shape.
                </p>
              </Message>

              <Input
                action={
                  <Button
                    tooltip="Load the selected pod’s channel list so you can review its current discussion spaces."
                    color="blue"
                    disabled={!channelPodId.trim()}
                    loading={channelsLoading}
                    onClick={() => handleGetChannels()}
                  >
                    Load Channels
                  </Button>
                }
                onChange={(e) => setChannelPodId(e.target.value)}
                placeholder="Pod ID for channel management"
                style={{ marginBottom: '1em', width: '100%' }}
                value={channelPodId}
              />

              <details style={{ marginBottom: '1em' }}>
                <summary>Advanced channel mutation controls</summary>
                <Message warning>
                  Creating, renaming, or deleting channels changes how pod
                  messages are organized for members. Confirm the target pod ID
                  before applying changes.
                </Message>

                {/* Create New Channel */}
                <Header size="tiny">Create New Channel</Header>
                <Input
                  action={
                    <>
                      <select
                        onChange={(e) => setNewChannelKind(e.target.value)}
                        style={{
                          border: '1px solid #ccc',
                          borderRadius: '4px',
                          padding: '0.5em',
                        }}
                        value={newChannelKind}
                      >
                        <option value="General">General</option>
                        <option value="Custom">Custom</option>
                        <option value="Bound">Bound</option>
                      </select>
                      <Button
                        tooltip="Create a channel in this pod so members can use a new discussion space."
                        color="green"
                        disabled={!newChannelName.trim() || !channelPodId.trim()}
                        loading={createChannelLoading}
                        onClick={() => handleCreateChannel()}
                      >
                        Create
                      </Button>
                    </>
                  }
                  onChange={(e) => setNewChannelName(e.target.value)}
                  placeholder="Channel name"
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={newChannelName}
                />
              </details>

              {/* Channels List */}
              {channels.length > 0 && (
                <div>
                  <Header size="tiny">Existing Channels</Header>
                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    {channels.map((channel) => (
                      <Card
                        key={channel.channelId}
                        style={{ marginBottom: '0.5em' }}
                      >
                        <Card.Content style={{ padding: '0.5em' }}>
                          {editingChannel &&
                          editingChannel.channelId === channel.channelId ? (
                            <div>
                              <Input
                                action={
                                  <>
                                    <Button
                                      tooltip="Save the channel name and kind changes to the selected pod."
                                      color="green"
                                      disabled={!editChannelName.trim()}
                                      loading={updateChannelLoading}
                                      onClick={() =>
                                        handleUpdateChannel(channel.channelId)
                                      }
                                      size="small"
                                    >
                                      Save
                                    </Button>
                                    <Button
                                      tooltip="Discard the unsaved channel edits and return to the channel list."
                                      onClick={() => cancelEditingChannel()}
                                      size="small"
                                    >
                                      Cancel
                                    </Button>
                                  </>
                                }
                                onChange={(e) =>
                                  setEditChannelName(e.target.value)
                                }
                                placeholder="Channel name"
                                style={{ width: '100%' }}
                                value={editChannelName}
                              />
                            </div>
                          ) : (
                            <div
                              style={{
                                alignItems: 'center',
                                display: 'flex',
                                justifyContent: 'space-between',
                              }}
                            >
                              <div>
                                <strong>{channel.name}</strong>
                                <div
                                  style={{
                                    color: '#666',
                                    fontSize: '0.8em',
                                    marginTop: '0.25em',
                                  }}
                                >
                                  ID: {channel.channelId} • Type: {channel.kind}
                                  {channel.bindingInfo &&
                                    ` • Binding: ${channel.bindingInfo}`}
                                </div>
                              </div>
                              <details>
                                <summary>Actions</summary>
                                <Button
                                  tooltip="Open this channel’s details for editing; changes are not saved until you choose Save."
                                  disabled={
                                    channel.name.toLowerCase() === 'general' &&
                                    channel.kind === 'General'
                                  }
                                  onClick={() => startEditingChannel(channel)}
                                  size="tiny"
                                >
                                  Edit
                                </Button>
                                <Button
                                  tooltip="Permanently delete this channel from the pod after confirmation. Use this only when the discussion space is no longer needed."
                                  color="red"
                                  disabled={
                                    channel.name.toLowerCase() === 'general' &&
                                    channel.kind === 'General'
                                  }
                                  loading={deleteChannelLoading}
                                  onClick={() =>
                                    handleDeleteChannel(
                                      channel.channelId,
                                      channel.name,
                                    )
                                  }
                                  size="tiny"
                                >
                                  Delete
                                </Button>
                              </details>
                            </div>
                          )}
                        </Card.Content>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {channels.length === 0 && channelPodId && !channelsLoading && (
                <Message
                  info
                  size="small"
                >
                  No channels found in pod {channelPodId}. Use advanced channel
                  mutation controls to create the first channel.
                </Message>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Content Linking */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-content-linking") ? undefined : "none" }} width={16}>
          <Card id="pod-content-linking" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="linkify" />
                Pod Content Linking
              </Card.Header>
              <Card.Description>
                Create pods linked to specific content (music, videos, etc.) for
                focused discussions
              </Card.Description>
              <PodWorkflowNotice title="Can create content-linked pods">
                Content search and validation are read-only. Creating a
                content-linked pod can publish content identifiers and pod
                metadata depending on visibility settings.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Content Linking */}
            <Card.Content>
              <Header size="small">Content Search & Validation</Header>

              {/* Content Search */}
              <Input
                action={
                  <Button
                    tooltip="Search content metadata so you can choose the exact item to link with a pod."
                    color="blue"
                    disabled={!contentSearchQuery.trim()}
                    loading={contentSearchLoading}
                    onClick={() => handleSearchContent()}
                  >
                    Search
                  </Button>
                }
                onChange={(e) => setContentSearchQuery(e.target.value)}
                placeholder="Search for content (artist, album, movie, etc.)"
                style={{ marginBottom: '1em', width: '100%' }}
                value={contentSearchQuery}
              />

              {/* Search Results */}
              {contentSearchResults.length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny">Search Results</Header>
                  {contentSearchResults.map((item, index) => (
                    <Card
                      key={index}
                      onClick={() => selectContentFromSearch(item)}
                      style={{ cursor: 'pointer', marginBottom: '0.5em' }}
                    >
                      <Card.Content style={{ padding: '0.5em' }}>
                        <strong>{item.title}</strong>
                        {item.subtitle && <div>{item.subtitle}</div>}
                        <small>
                          {item.domain} • {item.type}
                        </small>
                      </Card.Content>
                    </Card>
                  ))}
                </div>
              )}

              {/* Content Validation */}
              <Input
                action={
                  <Button
                    tooltip="Validate this content ID and load its metadata before creating a linked pod."
                    color="green"
                    disabled={!contentId.trim()}
                    loading={contentValidationLoading}
                    onClick={() => handleValidateContentId()}
                  >
                    Validate
                  </Button>
                }
                onChange={(e) => setContentId(e.target.value)}
                placeholder="Content ID (e.g., content:audio:album:mb-release-id)"
                style={{ marginBottom: '1em', width: '100%' }}
                value={contentId}
              />

              {/* Validation Result */}
              {contentValidation && (
                <Message
                  negative={!contentValidation.isValid}
                  positive={contentValidation.isValid}
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header>
                    {contentValidation.isValid
                      ? '✓ Valid Content ID'
                      : '✗ Invalid Content ID'}
                  </Message.Header>
                  {!contentValidation.isValid &&
                    contentValidation.errorMessage && (
                      <p>{contentValidation.errorMessage}</p>
                    )}
                </Message>
              )}

              {/* Content Metadata */}
              {contentMetadata && (
                <Message
                  info
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header>Content Metadata</Message.Header>
                  <p>
                    <strong>Title:</strong> {contentMetadata.title}
                    <br />
                    <strong>Artist:</strong> {contentMetadata.artist}
                    <br />
                    <strong>Type:</strong> {contentMetadata.type} (
                    {contentMetadata.domain})
                  </p>
                </Message>
              )}

              {/* Pod Creation */}
              {contentValidation?.isValid && (
                <details>
                  <summary>Advanced content-linked pod creation controls</summary>
                  <Message warning>
                    Creating a content-linked pod can publish the selected
                    content identifier, pod name, and visibility setting. Keep
                    private or draft discussions unlisted unless public
                    discovery is intended.
                  </Message>
                  <Header size="small">Create Content-Linked Pod</Header>

                  <Input
                    onChange={(e) => setNewPodName(e.target.value)}
                    placeholder="Pod name (auto-filled from content)"
                    style={{ marginBottom: '1em', width: '100%' }}
                    value={newPodName}
                  />

                  <div style={{ marginBottom: '1em' }}>
                    <label style={{ marginRight: '1em' }}>Visibility:</label>
                    <select
                      onChange={(e) => setNewPodVisibility(e.target.value)}
                      value={newPodVisibility}
                    >
                      <option value="Unlisted">Unlisted</option>
                      <option value="Listed">Listed</option>
                      <option value="Private">Private</option>
                    </select>
                  </div>

                  <Button
                    tooltip="Create a pod linked to this content ID so members can discuss the item. Review its visibility before creation."
                    color="teal"
                    disabled={!newPodName.trim()}
                    loading={createPodLoading}
                    onClick={() => handleCreateContentLinkedPod()}
                  >
                    Create Content-Linked Pod
                  </Button>
                </details>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Opinion Management */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-opinion-management") ? undefined : "none" }} width={16}>
          <Card id="pod-opinion-management" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="star" />
                Pod Opinion Management
              </Card.Header>
              <Card.Description>
                Publish and view opinions on content variants within pods for
                quality assessment and community feedback
              </Card.Description>
              <PodWorkflowNotice title="Publishes opinion data">
                Opinion publishing can expose peer preferences, ratings,
                confidence values, and content identifiers to other pod
                participants.
              </PodWorkflowNotice>
            </Card.Content>

            {/* Opinion Management */}
            <Card.Content>
              <Header size="small">Review Opinions</Header>
              <Message info>
                <Message.Header>Read pod opinions first</Message.Header>
                <p>
                  Refreshing, listing, and aggregating opinions reads pod
                  opinion state. Publishing opinions and recalculating affinity
                  data are grouped below as advanced operations.
                </p>
              </Message>

              {/* Pod Selection */}
              <Input
                onChange={(e) => setOpinionPodId(e.target.value)}
                placeholder="Pod ID"
                style={{ marginBottom: '1em', width: '100%' }}
                value={opinionPodId}
              />

              <Button
                tooltip="Refresh opinion records for this pod and update the current view. Use this when displayed community ratings may be stale."
                color="blue"
                disabled={!opinionPodId.trim()}
                loading={refreshOpinionsLoading}
                onClick={() => handleRefreshOpinions()}
                style={{ marginBottom: '1em' }}
              >
                Refresh Pod Opinions
              </Button>

              {/* Content Opinions */}
              <Header size="tiny">Content Opinions</Header>
              <Input
                onChange={(e) => setOpinionContentId(e.target.value)}
                placeholder="Content ID (e.g., content:audio:album:mb-id)"
                style={{ marginBottom: '1em', width: '100%' }}
                value={opinionContentId}
              />

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip="Load opinions for this pod and content ID so you can review the available ratings and notes."
                  color="teal"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getOpinionsLoading}
                  onClick={() => handleGetOpinions()}
                  style={{ marginRight: '0.5em' }}
                >
                  Get Opinions
                </Button>

                <Button
                  tooltip="Load rating counts and distribution for this pod and content item so you can review the data before publishing."
                  color="purple"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getStatsLoading}
                  onClick={() => handleGetOpinionStatistics()}
                >
                  Get Statistics
                </Button>
              </div>

              {/* Opinion Statistics */}
              {opinionStatistics && (
                <Message
                  info
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header>Opinion Statistics</Message.Header>
                  <p>
                    <strong>Total Opinions:</strong>{' '}
                    {opinionStatistics.totalOpinions}
                    <br />
                    <strong>Unique Variants:</strong>{' '}
                    {opinionStatistics.uniqueVariants}
                    <br />
                    <strong>Average Score:</strong>{' '}
                    {opinionStatistics.averageScore.toFixed(1)}
                    <br />
                    <strong>Score Range:</strong> {opinionStatistics.minScore} -{' '}
                    {opinionStatistics.maxScore}
                    <br />
                    <strong>Last Updated:</strong>{' '}
                    {new Date(opinionStatistics.lastUpdated).toLocaleString(getRegionalLocale())}
                  </p>
                </Message>
              )}

              {/* Opinions List */}
              {opinions.length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny">Opinions ({opinions.length})</Header>
                  {opinions.map((opinion, index) => (
                    <Card
                      key={index}
                      style={{ marginBottom: '0.5em' }}
                    >
                      <Card.Content style={{ padding: '0.5em' }}>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <strong>Variant:</strong>{' '}
                            {opinion.variantHash.slice(0, 8)}...
                            <br />
                            <strong>Score:</strong> {opinion.score}/10
                            {opinion.note && (
                              <>
                                <br />
                                <strong>Note:</strong> {opinion.note}
                              </>
                            )}
                          </div>
                          <small>{opinion.senderPeerId}</small>
                        </div>
                      </Card.Content>
                    </Card>
                  ))}
                </div>
              )}

              <details>
                <summary>Advanced opinion publishing controls</summary>
                <Message warning>
                  Publishing an opinion can expose the selected content ID,
                  variant hash, score, note, and peer preference signal to pod
                  participants.
                </Message>

                {/* Publish Opinion */}
                <Header size="small">Publish New Opinion</Header>

                <Input
                  onChange={(e) => setOpinionVariantHash(e.target.value)}
                  placeholder="Variant Hash"
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={opinionVariantHash}
                />

                <div style={{ marginBottom: '1em' }}>
                  <label style={{ marginRight: '1em' }}>Score (0-10):</label>
                  <input
                    max="10"
                    min="0"
                    onChange={(e) =>
                      setOpinionScore(Number.parseFloat(e.target.value))
                    }
                    step="0.5"
                    style={{ width: '200px' }}
                    type="range"
                    value={opinionScore}
                  />
                  <span style={{ marginLeft: '1em' }}>{opinionScore}/10</span>
                </div>

                <Input
                  onChange={(e) => setOpinionNote(e.target.value)}
                  placeholder="Optional note about this variant"
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={opinionNote}
                />

                <Button
                  tooltip="Publish your score and note for this content to the pod. Review the content ID and variant hash because other participants may see this opinion."
                  color="green"
                  disabled={
                    !opinionPodId.trim() ||
                    !opinionContentId.trim() ||
                    !opinionVariantHash.trim()
                  }
                  loading={publishOpinionLoading}
                  onClick={() => handlePublishOpinion()}
                >
                  Publish Opinion
                </Button>
              </details>
            </Card.Content>

            {/* Opinion Aggregation */}
            <Card.Content>
              <Header size="small">Opinion Aggregation & Consensus</Header>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip="Request the combined opinion view for this pod and content item to compare member feedback."
                  color="purple"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getAggregatedLoading}
                  onClick={() => handleGetAggregatedOpinions()}
                  style={{ marginRight: '0.5em' }}
                >
                  Get Aggregated Opinions
                </Button>

                <Button
                  tooltip="Load member affinity scores for this pod so you can understand how current recommendations are ranked."
                  color="blue"
                  disabled={!opinionPodId.trim()}
                  loading={getAffinitiesLoading}
                  onClick={() => handleGetMemberAffinities()}
                  style={{ marginRight: '0.5em' }}
                >
                  Get Member Affinities
                </Button>

                <Button
                  tooltip="Load recommendations derived from pod consensus so you can review what members collectively favor."
                  color="teal"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getRecommendationsLoading}
                  onClick={() => handleGetConsensusRecommendations()}
                  style={{ marginRight: '0.5em' }}
                >
                  Get Recommendations
                </Button>

              </div>

              <details style={{ marginBottom: '1em' }}>
                <summary>Advanced affinity recalculation controls</summary>
                <Message warning>
                  Updating member affinities recalculates stored relationship
                  weights from pod opinion history. Review current opinions and
                  affinities before running it.
                </Message>
                <Button
                  tooltip="Recompute stored member affinity values from available pod opinion data after ratings change."
                  color="orange"
                  disabled={!opinionPodId.trim()}
                  loading={updateAffinitiesLoading}
                  onClick={() => handleUpdateMemberAffinities()}
                >
                  Update Affinities
                </Button>
              </details>

              {/* Aggregated Opinions */}
              {aggregatedOpinions && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny">Aggregated Opinion Results</Header>
                  <Message info>
                    <strong>Weighted Average:</strong>{' '}
                    {aggregatedOpinions.weightedAverageScore.toFixed(2)}/10
                    <br />
                    <strong>Unweighted Average:</strong>{' '}
                    {aggregatedOpinions.unweightedAverageScore.toFixed(2)}/10
                    <br />
                    <strong>Consensus Strength:</strong>{' '}
                    {(aggregatedOpinions.consensusStrength * 100).toFixed(1)}%
                    <br />
                    <strong>Total Opinions:</strong>{' '}
                    {aggregatedOpinions.totalOpinions}
                    <br />
                    <strong>Unique Variants:</strong>{' '}
                    {aggregatedOpinions.uniqueVariants}
                    <br />
                    <strong>Contributing Members:</strong>{' '}
                    {aggregatedOpinions.contributingMembers}
                  </Message>

                  {/* Variant Breakdown */}
                  {aggregatedOpinions.variantAggregates.length > 0 && (
                    <div style={{ marginTop: '1em' }}>
                      <Header size="tiny">Variant Analysis</Header>
                      {asArray(aggregatedOpinions.variantAggregates).map(
                        (variant, index) => (
                          <Card
                            key={index}
                            style={{ marginBottom: '0.5em' }}
                          >
                            <Card.Content style={{ padding: '0.5em' }}>
                              <div>
                                <strong>Variant:</strong>{' '}
                                {variant.variantHash.slice(0, 8)}...
                                <br />
                                <strong>Weighted Score:</strong>{' '}
                                {variant.weightedAverageScore.toFixed(2)}/10
                                <br />
                                <strong>Unweighted Score:</strong>{' '}
                                {variant.unweightedAverageScore.toFixed(2)}/10
                                <br />
                                <strong>Opinions:</strong>{' '}
                                {variant.opinionCount}
                                <br />
                                <strong>Agreement:</strong>{' '}
                                {(
                                  1 -
                                  variant.scoreStandardDeviation / 5
                                ).toFixed(2)}{' '}
                                (lower std dev = higher agreement)
                              </div>
                            </Card.Content>
                          </Card>
                        ),
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Consensus Recommendations */}
              {consensusRecommendations.length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny">Consensus Recommendations</Header>
                  {consensusRecommendations.map((rec, index) => (
                    <Card
                      key={index}
                      style={{
                        borderLeft:
                          rec.recommendation === 'StronglyRecommended'
                            ? '5px solid #21ba45'
                            : rec.recommendation === 'Recommended'
                              ? '5px solid #2185d0'
                              : rec.recommendation === 'Neutral'
                                ? '5px solid #fbbd08'
                                : rec.recommendation === 'NotRecommended'
                                  ? '5px solid #f2711c'
                                  : '5px solid #db2828',
                        marginBottom: '0.5em',
                      }}
                    >
                      <Card.Content style={{ padding: '0.5em' }}>
                        <div>
                          <strong>Variant:</strong>{' '}
                          {rec.variantHash.slice(0, 8)}...
                          <br />
                          <strong>Recommendation:</strong>{' '}
                          {rec.recommendation
                            .replaceAll(/([A-Z])/g, ' $1')
                            .trim()}
                          <br />
                          <strong>Consensus Score:</strong>{' '}
                          {(rec.consensusScore * 100).toFixed(1)}%<br />
                          <strong>Reasoning:</strong> {rec.reasoning}
                          <br />
                          <small>
                            <strong>Factors:</strong>{' '}
                            {asArray(rec.supportingFactors).join(', ')}
                          </small>
                        </div>
                      </Card.Content>
                    </Card>
                  ))}
                </div>
              )}

              {/* Member Affinities */}
              {Object.keys(asObject(memberAffinities)).length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny">
                    Member Affinities ({Object.keys(asObject(memberAffinities)).length})
                  </Header>
                  {Object.entries(asObject(memberAffinities)).map(
                    ([peerId, affinity], index) => (
                      <Card
                        key={index}
                        style={{ marginBottom: '0.5em' }}
                      >
                        <Card.Content style={{ padding: '0.5em' }}>
                          <div>
                            <strong>Peer:</strong> {peerId.slice(0, 8)}...
                            <br />
                            <strong>Affinity Score:</strong>{' '}
                            {(affinity.affinityScore * 100).toFixed(1)}%<br />
                            <strong>Trust Score:</strong>{' '}
                            {(affinity.trustScore * 100).toFixed(1)}%<br />
                            <strong>Messages:</strong> {affinity.messageCount}
                            <br />
                            <strong>Opinions:</strong> {affinity.opinionCount}
                            <br />
                            <small>
                              Last Activity:{' '}
                              {new Date(
                                affinity.lastActivity,
                              ).toLocaleDateString(getRegionalLocale())}
                            </small>
                          </div>
                        </Card.Content>
                      </Card>
                    ),
                  )}
                </div>
              )}
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Pod Message Signing */}
        <Grid.Column style={{ display: isPodWorkflowVisible("pod-message-signing") ? undefined : "none" }} width={16}>
          <Card id="pod-message-signing" fluid>
            <Card.Content>
              <Card.Header>
                <Icon name="key" />
                Pod Message Signing
              </Card.Header>
              <Card.Description>
                Cryptographic signing and verification of pod messages for
                authenticity and integrity
              </Card.Description>
              <PodWorkflowNotice title="Handles key material">
                Signing and key generation workflows may expose private keys or
                signed payloads in the browser. Treat pasted keys and generated
                output as sensitive.
              </PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header>Verify before generating signatures</Message.Header>
                <p>
                  Signature verification and signing statistics do not expose
                  private key material. Signing and key generation controls are
                  grouped below as advanced operations.
                </p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  {/* Signature Verification */}
                  <Header size="small">Verify Message Signature</Header>
                  <Form>
                    <Form.TextArea
                      label="Pod Message JSON (with signature)"
                      onChange={(e) => setMessageToVerify(e.target.value)}
                      placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                      rows={4}
                      value={messageToVerify}
                    />
                    <Button
                      tooltip="Verify the supplied message signature locally so you can check authenticity without routing the message."
                      disabled={verifyingSignature || !messageToVerify.trim()}
                      fluid
                      loading={verifyingSignature}
                      onClick={handleVerifySignature}
                    >
                      Verify Signature
                    </Button>
                  </Form>

                  {verificationResult && (
                    <div style={{ marginTop: '0.5em' }}>
                      {verificationResult.error ? (
                        <Message
                          error
                          size="tiny"
                        >
                          <p>{verificationResult.error}</p>
                        </Message>
                      ) : (
                        <Message size="tiny">
                          <p>
                            Message {verificationResult.messageId}: Signature is{' '}
                            {verificationResult.isValid ? 'VALID' : 'INVALID'}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>
                <Grid.Column width={8}>
                  {/* Signing Statistics */}
                  <Header size="small">Signing Statistics</Header>
                  <Button.Group fluid>
                    <Button
                      tooltip="Load local signing and verification counts so you can review recent signature operations."
                      disabled={loadingSigningStats}
                      loading={loadingSigningStats}
                      onClick={handleLoadSigningStats}
                    >
                      Load Stats
                    </Button>
                  </Button.Group>

                  {signingStats && !signingStats.error && (
                    <div style={{ marginTop: '0.5em' }}>
                      <Message size="tiny">
                        <p>
                          <strong>Signatures Created:</strong>{' '}
                          {signingStats.totalSignaturesCreated}
                          <br />
                          <strong>Signatures Verified:</strong>{' '}
                          {signingStats.totalSignaturesVerified}
                          <br />
                          <strong>Successful:</strong>{' '}
                          {signingStats.successfulVerifications}
                          <br />
                          <strong>Failed:</strong>{' '}
                          {signingStats.failedVerifications}
                          <br />
                          <strong>Avg Sign Time:</strong>{' '}
                          {signingStats.averageSigningTimeMs.toFixed(2)}ms
                          <br />
                          <strong>Avg Verify Time:</strong>{' '}
                          {signingStats.averageVerificationTimeMs.toFixed(2)}ms
                        </p>
                      </Message>
                    </div>
                  )}

                  {signingStats?.error && (
                    <Message
                      error
                      size="tiny"
                      style={{ marginTop: '0.5em' }}
                    >
                      <p>{signingStats.error}</p>
                    </Message>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            <Card.Content>
              <details>
                <summary>Advanced key material and signing controls</summary>
                <Message warning>
                  These controls handle private keys or create signed payloads
                  that may be routed to other pod members. Keep generated
                  private keys out of logs and screenshots.
                </Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small">Sign Pod Message</Header>
                    <Form>
                      <Form.TextArea
                        label="Pod Message JSON"
                        onChange={(e) => setMessageToSign(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789}'
                        rows={3}
                        value={messageToSign}
                      />
                      <Form.Input
                        label="Private Key"
                        onChange={(e) => setPrivateKeyForSigning(e.target.value)}
                        placeholder="base64-encoded private key"
                        type="password"
                        value={privateKeyForSigning}
                      />
                      <Button
                        tooltip="Sign this message with the supplied private key so it can be authenticated before routing. Signing does not send it to pod members."
                        disabled={
                          signingMessage ||
                          !messageToSign.trim() ||
                          !privateKeyForSigning.trim()
                        }
                        loading={signingMessage}
                        onClick={handleSignMessage}
                        primary
                      >
                        Sign Message
                      </Button>
                    </Form>

                    {signedMessageResult && (
                      <div style={{ marginTop: '1em' }}>
                        {signedMessageResult.error ? (
                          <Message error>
                            <p>
                              Failed to sign message:{' '}
                              {signedMessageResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              Message Signed Successfully
                            </Message.Header>
                            <p>
                              <strong>Message ID:</strong>{' '}
                              {signedMessageResult.messageId}
                              <br />
                              <strong>Channel:</strong>{' '}
                              {signedMessageResult.channelId}
                              <br />
                              <strong>Signature:</strong>{' '}
                              {signedMessageResult.signature?.slice(0, 50)}...
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">Generate Key Pair</Header>
                    <Form>
                      <Button
                        tooltip="Generate a new key pair for pod message signing. Keep the private key secret and store it securely before clearing this result."
                        disabled={generatingKeyPair}
                        fluid
                        loading={generatingKeyPair}
                        onClick={handleGenerateKeyPair}
                      >
                        Generate New Key Pair
                      </Button>
                    </Form>

                    {generatedKeyPair && (
                      <div style={{ marginTop: '0.5em' }}>
                        {generatedKeyPair.error ? (
                          <Message
                            error
                            size="tiny"
                          >
                            <p>{generatedKeyPair.error}</p>
                          </Message>
                        ) : (
                          <Message
                            size="tiny"
                            success
                          >
                            <Message.Header>Key Pair Generated</Message.Header>
                            <p>
                              <strong>Public Key:</strong>{' '}
                              {generatedKeyPair.publicKey?.slice(0, 30)}...
                              <br />
                              <strong>Private Key:</strong>{' '}
                              {generatedKeyPair.privateKey?.slice(0, 30)}...
                              <br />
                              <em>Keep private key secure.</em>
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>
                </Grid>
              </details>
            </Card.Content>
          </Card>
        </Grid.Column>

        {/* Supported Algorithms Info */}
        {supportedAlgorithms && (
          <Grid.Column width={16}>
            <Segment>
              <Header as="h3">
                <Icon name="cogs" />
                Supported Hash Algorithms
              </Header>
              <List
                divided
                relaxed
              >
                {asArray(supportedAlgorithms.algorithms).map((alg) => (
                  <List.Item key={alg}>
                    <List.Content>
                      <List.Header>{alg}</List.Header>
                      <List.Description>
                        {(supportedAlgorithms.descriptions || {})[alg]}
                      </List.Description>
                    </List.Content>
                  </List.Item>
                ))}
              </List>
            </Segment>
          </Grid.Column>
        )}

    </>
  );
};

export default MediaCorePods;
