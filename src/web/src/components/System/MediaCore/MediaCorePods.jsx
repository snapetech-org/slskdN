import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';


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
  useInterfaceLanguage();
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
      toast.warning(interfaceText("Please enter pod JSON data"));
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
      setPodPublishingResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setPublishingPod(false);
    }
  };

  const handleRetrievePodMetadata = async () => {
    if (!podMetadataToRetrieve.trim()) {
      toast.warning(interfaceText("Please enter a pod ID"));
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
      setPodMetadataResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setRetrievingPodMetadata(false);
    }
  };

  const handleUnpublishPod = async () => {
    if (!podToUnpublish.trim()) {
      toast.warning(interfaceText("Please enter a pod ID"));
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
      setPodUnpublishResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setPodPublishingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingPodStats(false);
    }
  };

  // Pod Membership handlers
  const handlePublishMembership = async () => {
    if (!membershipRecord.trim()) {
      toast.warning(interfaceText("Please enter membership record JSON data"));
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
      setMembershipPublishResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setPublishingMembership(false);
    }
  };

  const handleGetMembership = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setMembershipResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setGettingMembership(false);
    }
  };

  const handleVerifyMembership = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setMembershipVerification({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setVerifyingMembership(false);
    }
  };

  const handleBanMember = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setBanResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setBanningMember(false);
    }
  };

  const handleChangeRole = async () => {
    if (!membershipPodId.trim() || !membershipPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setRoleChangeResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setMembershipStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
        interfaceText("Cleanup completed: {recordsCleaned} records cleaned, {errorsEncountered} errors", { "recordsCleaned": (result.recordsCleaned), "errorsEncountered": (result.errorsEncountered) }),
      );
      // Reload stats to reflect changes
      await handleLoadMembershipStats();
    } catch (error_) {
      toast.error(interfaceText("Failed to cleanup: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  // Pod Membership Verification handlers
  const handleVerifyPodMembership = async () => {
    if (!verifyPodId.trim() || !verifyPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setMembershipVerificationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setVerifyingMembership(false);
    }
  };

  const handleVerifyMessage = async () => {
    if (!membershipMessageToVerify.trim()) {
      toast.warning(interfaceText("Please enter a message JSON"));
      return;
    }

    try {
      setVerifyingMessage(true);
      setMessageVerificationResult(null);
      const message = JSON.parse(membershipMessageToVerify);
      const result = await mediacore.verifyPodMessage(message);
      setMessageVerificationResult(result);
    } catch (error_) {
      setMessageVerificationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setVerifyingMessage(false);
    }
  };

  const handleCheckRole = async () => {
    if (!roleCheckPodId.trim() || !roleCheckPeerId.trim()) {
      toast.warning(interfaceText("Please enter both Pod ID and Peer ID"));
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
      setRoleCheckResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setVerificationStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingVerificationStats(false);
    }
  };

  // Pod Discovery handlers
  const handleRegisterPodForDiscovery = async () => {
    if (!podToRegister.trim()) {
      toast.warning(interfaceText("Please enter pod JSON data"));
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
      setPodRegistrationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setRegisteringPod(false);
    }
  };

  const handleUnregisterPodFromDiscovery = async () => {
    if (!podToUnregister.trim()) {
      toast.warning(interfaceText("Please enter a pod ID"));
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
      setPodUnregistrationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setUnregisteringPod(false);
    }
  };

  const handleDiscoverByName = async () => {
    if (!discoverByName.trim()) {
      toast.warning(interfaceText("Please enter a pod name"));
      return;
    }

    try {
      setDiscoveringByName(true);
      setNameDiscoveryResult(null);
      const result = await mediacore.discoverPodsByName(discoverByName);
      setNameDiscoveryResult(result);
    } catch (error_) {
      setNameDiscoveryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setDiscoveringByName(false);
    }
  };

  const handleDiscoverByTag = async () => {
    if (!discoverByTag.trim()) {
      toast.warning(interfaceText("Please enter a tag"));
      return;
    }

    try {
      setDiscoveringByTag(true);
      setTagDiscoveryResult(null);
      const result = await mediacore.discoverPodsByTag(discoverByTag);
      setTagDiscoveryResult(result);
    } catch (error_) {
      setTagDiscoveryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setDiscoveringByTag(false);
    }
  };

  const handleDiscoverByTags = async () => {
    if (!discoverTags.trim()) {
      toast.warning(interfaceText("Please enter tags (comma-separated)"));
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
      setTagsDiscoveryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setAllDiscoveryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setDiscoveringAll(false);
    }
  };

  const handleDiscoverByContent = async () => {
    if (!discoverByContent.trim()) {
      toast.warning(interfaceText("Please enter a content ID"));
      return;
    }

    try {
      setDiscoveringByContent(true);
      setContentDiscoveryResult(null);
      const result = await mediacore.discoverPodsByContent(discoverByContent);
      setContentDiscoveryResult(result);
    } catch (error_) {
      setContentDiscoveryResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setDiscoveryStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingDiscoveryStats(false);
    }
  };

  const handleRefreshDiscovery = async () => {
    try {
      const result = await mediacore.refreshPodDiscovery();
      toast.success(
        interfaceText("Discovery refresh completed: {entriesRefreshed} refreshed, {entriesExpired} expired", { "entriesRefreshed": (result.entriesRefreshed), "entriesExpired": (result.entriesExpired) }),
      );
      // Reload stats to reflect changes
      await handleLoadDiscoveryStats();
    } catch (error_) {
      toast.error(interfaceText("Failed to refresh discovery: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  // Pod Join/Leave handlers
  const handleRequestJoin = async () => {
    if (!joinRequestData.trim()) {
      toast.warning(interfaceText("Please enter join request JSON data"));
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
      setJoinRequestResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setRequestingJoin(false);
    }
  };

  const handleAcceptJoin = async () => {
    if (!acceptanceData.trim()) {
      toast.warning(interfaceText("Please enter acceptance JSON data"));
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
      setAcceptanceResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setAcceptingJoin(false);
    }
  };

  const handleRequestLeave = async () => {
    if (!leaveRequestData.trim()) {
      toast.warning(interfaceText("Please enter leave request JSON data"));
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
      setLeaveRequestResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setRequestingLeave(false);
    }
  };

  const handleAcceptLeave = async () => {
    if (!acceptanceData.trim()) {
      toast.warning(interfaceText("Please enter leave acceptance JSON data"));
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
      setLeaveAcceptanceResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setAcceptingLeave(false);
    }
  };

  const handleLoadPendingRequests = async () => {
    if (!pendingPodId.trim()) {
      toast.warning(interfaceText("Please enter a pod ID"));
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
      setPendingJoinRequests({ error: getApiErrorMessage(error_, { t: interfaceText }) });
      setPendingLeaveRequests({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingPendingRequests(false);
    }
  };

  // Pod Message Routing handlers
  const handleRouteMessage = async () => {
    if (!routeMessageData.trim()) {
      toast.warning(interfaceText("Please enter message JSON data"));
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
      setRoutingResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setRoutingMessage(false);
    }
  };

  const handleRouteMessageToPeers = async () => {
    if (!routeToPeersMessage.trim() || !routeToPeersIds.trim()) {
      toast.warning(interfaceText("Please enter message JSON and target peer IDs"));
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
      setRoutingToPeersResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setRoutingStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setLoadingRoutingStats(false);
    }
  };

  const handleCheckMessageSeen = async () => {
    if (!checkMessageId.trim() || !checkPodId.trim()) {
      toast.warning(interfaceText("Please enter both message ID and pod ID"));
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
      setMessageSeenResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setCheckingMessageSeen(false);
    }
  };

  const handleRegisterMessageSeen = async () => {
    if (!checkMessageId.trim() || !checkPodId.trim()) {
      toast.warning(interfaceText("Please enter both message ID and pod ID"));
      return;
    }

    try {
      const result = await mediacore.registerMessageSeen(
        checkMessageId,
        checkPodId,
      );
      toast.success(
        interfaceText('Message registered as seen: {status}', {
          status: interfaceText(result.wasNewlyRegistered ? 'New' : 'Already known'),
        }),
      );
    } catch (error_) {
      toast.error(interfaceText("Failed to register message: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  const handleCleanupSeenMessages = async () => {
    try {
      const result = await mediacore.cleanupSeenMessages();
      toast.success(
        interfaceText("Cleanup completed: {messagesCleaned} messages cleaned, {messagesRetained} retained", { "messagesCleaned": (result.messagesCleaned), "messagesRetained": (result.messagesRetained) }),
      );
      // Reload stats to reflect changes
      await handleLoadRoutingStats();
    } catch (error_) {
      toast.error(interfaceText("Failed to cleanup: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    }
  };

  // Pod Message Signing handlers
  const handleSignMessage = async () => {
    if (!messageToSign.trim() || !privateKeyForSigning.trim()) {
      toast.warning(interfaceText("Please enter message JSON and private key"));
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
      setSignedMessageResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
    } finally {
      setSigningMessage(false);
    }
  };

  const handleVerifySignature = async () => {
    if (!messageToVerify.trim()) {
      toast.warning(interfaceText("Please enter message JSON to verify"));
      return;
    }

    try {
      setVerifyingSignature(true);
      setVerificationResult(null);
      const message = JSON.parse(messageToVerify);
      const result = await mediacore.verifyPodMessageSignature(message);
      setVerificationResult(result);
    } catch (error_) {
      setVerificationResult({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setGeneratedKeyPair({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setSigningStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
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
      setStorageStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
      toast.error(interfaceText("Failed to get storage stats: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setStorageStatsLoading(false);
    }
  };

  const handleCleanupMessages = async () => {
    try {
      setCleanupLoading(true);
      const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1_000;
      const result = await mediacore.cleanupMessages(thirtyDaysAgo);
      toast.success(interfaceText("Cleaned up {result} old messages", { "result": (result) }));
      // Refresh stats after cleanup
      await handleGetStorageStats();
    } catch (error_) {
      toast.error(interfaceText("Failed to cleanup messages: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
          ? interfaceText('Search index rebuilt successfully')
          : interfaceText('Search index rebuild failed'),
      );
    } catch (error_) {
      toast.error(interfaceText("Failed to rebuild search index: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
          ? interfaceText('Database vacuum completed successfully')
          : interfaceText('Database vacuum failed'),
      );
    } catch (error_) {
      toast.error(interfaceText("Failed to vacuum database: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.error(interfaceText("Failed to search messages: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      setBackfillStats({ error: getApiErrorMessage(error_, { t: interfaceText }) });
      toast.error(interfaceText("Failed to get backfill stats: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setBackfillStatsLoading(false);
    }
  };

  const handleSyncPodBackfill = async () => {
    if (!backfillPodId.trim()) {
      toast.error(interfaceText("Pod ID is required for backfill sync"));
      return;
    }

    try {
      setSyncBackfillLoading(true);
      // Get current last seen timestamps
      const timestamps = await mediacore.getLastSeenTimestamps(backfillPodId);
      const result = await mediacore.syncPodBackfill(backfillPodId, timestamps);
      toast.success(
        interfaceText("Backfill sync completed: {totalMessagesReceived} messages received", { "totalMessagesReceived": (result.totalMessagesReceived) }),
      );
      // Refresh stats
      await handleGetBackfillStats();
    } catch (error_) {
      toast.error(interfaceText("Failed to sync pod backfill: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setSyncBackfillLoading(false);
    }
  };

  const handleGetLastSeenTimestamps = async () => {
    if (!backfillPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    try {
      const timestamps = await mediacore.getLastSeenTimestamps(backfillPodId);
      setLastSeenTimestamps(timestamps);
    } catch (error_) {
      toast.error(interfaceText("Failed to get last seen timestamps: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setLastSeenTimestamps(null);
    }
  };

  // Pod Channel Management handlers
  const handleGetChannels = async () => {
    if (!channelPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    try {
      setChannelsLoading(true);
      const result = await mediacore.getChannels(channelPodId);
      setChannels(asArray(result));
    } catch (error_) {
      toast.error(interfaceText("Failed to get channels: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setChannels([]);
    } finally {
      setChannelsLoading(false);
    }
  };

  const handleCreateChannel = async () => {
    if (!channelPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    if (!newChannelName.trim()) {
      toast.error(interfaceText("Channel name is required"));
      return;
    }

    try {
      setCreateChannelLoading(true);
      const channel = {
        kind: newChannelKind,
        name: newChannelName,
      };
      await mediacore.createChannel(channelPodId, channel);
      toast.success(interfaceText("Channel \"{newChannelName}\" created successfully", { "newChannelName": (newChannelName) }));
      setNewChannelName('');
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(interfaceText("Failed to create channel: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setCreateChannelLoading(false);
    }
  };

  const handleUpdateChannel = async (channelId) => {
    if (!editChannelName.trim()) {
      toast.error(interfaceText("Channel name is required"));
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
      toast.success(interfaceText("Channel updated successfully"));
      setEditingChannel(null);
      setEditChannelName('');
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(interfaceText("Failed to update channel: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.success(interfaceText("Channel \"{channelName}\" deleted successfully", { "channelName": (channelName) }));
      // Refresh channels list
      await handleGetChannels();
    } catch (error_) {
      toast.error(interfaceText("Failed to delete channel: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.error(interfaceText("Content ID is required"));
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
      setContentValidation({ error: getApiErrorMessage(error_, { t: interfaceText }), isValid: false });
      toast.error(interfaceText("Failed to validate content ID: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.error(interfaceText("Failed to get content metadata: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.error(interfaceText("Failed to search content: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setContentSearchResults([]);
    } finally {
      setContentSearchLoading(false);
    }
  };

  const handleCreateContentLinkedPod = async () => {
    if (!contentId.trim()) {
      toast.error(interfaceText("Content ID is required"));
      return;
    }

    if (!newPodName.trim()) {
      toast.error(interfaceText("Pod name is required"));
      return;
    }

    if (!contentValidation?.isValid) {
      toast.error(interfaceText("Please validate the content ID first"));
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
      toast.success(interfaceText("Pod \"{name}\" created successfully!", { "name": (createdPod.name) }));

      // Reset form
      setContentId('');
      setContentValidation(null);
      setContentMetadata(null);
      setNewPodName('');
      setContentSearchQuery('');
      setContentSearchResults([]);
    } catch (error_) {
      toast.error(interfaceText("Failed to create pod: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
      toast.error(interfaceText("Pod ID, Content ID, and Variant Hash are required"));
      return;
    }

    if (opinionScore < 0 || opinionScore > 10) {
      toast.error(interfaceText("Score must be between 0 and 10"));
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
      toast.success(interfaceText("Opinion published successfully"));

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
      toast.error(interfaceText("Failed to publish opinion: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setPublishOpinionLoading(false);
    }
  };

  const handleGetOpinions = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error(interfaceText("Pod ID and Content ID are required"));
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
      toast.error(interfaceText("Failed to get opinions: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setOpinions([]);
    } finally {
      setGetOpinionsLoading(false);
    }
  };

  const handleGetOpinionStatistics = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error(interfaceText("Pod ID and Content ID are required"));
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
      toast.error(interfaceText("Failed to get opinion statistics: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setOpinionStatistics(null);
    } finally {
      setGetStatsLoading(false);
    }
  };

  const handleRefreshOpinions = async () => {
    if (!opinionPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    try {
      setRefreshOpinionsLoading(true);
      const result = await mediacore.refreshPodOpinions(opinionPodId.trim());
      toast.success(interfaceText("Refreshed {opinionsRefreshed} opinions", { "opinionsRefreshed": (result.opinionsRefreshed) }));

      // Refresh current view
      if (opinionContentId) {
        await Promise.all([handleGetOpinions(), handleGetOpinionStatistics()]);
      }
    } catch (error_) {
      toast.error(interfaceText("Failed to refresh opinions: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
    } finally {
      setRefreshOpinionsLoading(false);
    }
  };

  // Pod Opinion Aggregation handlers
  const handleGetAggregatedOpinions = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error(interfaceText("Pod ID and Content ID are required"));
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
      toast.error(interfaceText("Failed to get aggregated opinions: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setAggregatedOpinions(null);
    } finally {
      setGetAggregatedLoading(false);
    }
  };

  const handleGetMemberAffinities = async () => {
    if (!opinionPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    try {
      setGetAffinitiesLoading(true);
      const affinities = await mediacore.getMemberAffinities(
        opinionPodId.trim(),
      );
      setMemberAffinities(affinities);
    } catch (error_) {
      toast.error(interfaceText("Failed to get member affinities: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setMemberAffinities({});
    } finally {
      setGetAffinitiesLoading(false);
    }
  };

  const handleGetConsensusRecommendations = async () => {
    if (!opinionPodId.trim() || !opinionContentId.trim()) {
      toast.error(interfaceText("Pod ID and Content ID are required"));
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
      toast.error(interfaceText("Failed to get consensus recommendations: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
      setConsensusRecommendations([]);
    } finally {
      setGetRecommendationsLoading(false);
    }
  };

  const handleUpdateMemberAffinities = async () => {
    if (!opinionPodId.trim()) {
      toast.error(interfaceText("Pod ID is required"));
      return;
    }

    try {
      setUpdateAffinitiesLoading(true);
      const result = await mediacore.updateMemberAffinities(
        opinionPodId.trim(),
      );
      toast.success(interfaceText("Updated affinities for {membersUpdated} members", { "membersUpdated": (result.membersUpdated) }));

      // Refresh affinities display
      await handleGetMemberAffinities();
    } catch (error_) {
      toast.error(interfaceText("Failed to update member affinities: {message}", { "message": (getApiErrorMessage(error_, { t: interfaceText })) }));
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
                <LocalizedText source={"PodCore DHT Publishing"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Publish and manage pod metadata on the decentralized DHT for discovery"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Publishes pod metadata")} {...interfaceTextProps("Publishes pod metadata")}>
                <LocalizedText source={"Publishing or updating a listed pod can make pod identifiers, tags, focus content IDs, and descriptive metadata discoverable by other mesh participants."} /></PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header><LocalizedText source={"Retrieve DHT metadata first"} /></Message.Header>
                <p>
                  <LocalizedText source={"Metadata retrieval and publishing statistics are read-only. Publishing and unpublishing pod metadata are grouped below as advanced DHT mutation controls."} /></p>
              </Message>
              {/* Retrieve Pod Metadata */}
              <Header size="small"><LocalizedText source={"Retrieve Pod Metadata"} /></Header>
              <Form>
                <Form.Input
                  label={interfaceText("Pod ID")}
                  onChange={(e) => setPodMetadataToRetrieve(e.target.value)}
                  placeholder="pod:artist:mb:daft-punk-hash"
                  value={podMetadataToRetrieve}
                 {...interfaceTextProps("Pod ID")}/>
                <Button
                  tooltip={interfaceText("Query the DHT for this pod’s signed metadata so you can inspect the record participants may discover. This is a manual lookup.")}
                  disabled={
                    retrievingPodMetadata || !podMetadataToRetrieve.trim()
                  }
                  loading={retrievingPodMetadata}
                  onClick={handleRetrievePodMetadata}
                >
                  <LocalizedText source={"Retrieve Metadata"} /></Button>
              </Form>

              {podMetadataResult && (
                <div style={{ marginTop: '1em' }}>
                  {podMetadataResult.error ? (
                    <Message error>
                      <p>
                        <LocalizedText source={"Failed to retrieve metadata:"} />{" "}{podMetadataResult.error}
                      </p>
                    </Message>
                  ) : podMetadataResult.found ? (
                    <Message success>
                      <Message.Header>
                        <LocalizedText source={"Pod Metadata Retrieved"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Pod ID:"} /></strong>{' '}
                        {podMetadataResult.podId?.value ||
                          podMetadataResult.podId}
                        <br />
                        <strong><LocalizedText source={"Signature Valid:"} /></strong>{' '}
                        {podMetadataResult.isValidSignature ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                        <br />
                        <strong><LocalizedText source={"Retrieved:"} /></strong>{' '}
                        {new Date(
                          podMetadataResult.retrievedAt,
                        ).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong><LocalizedText source={"Expires:"} /></strong>{' '}
                        {new Date(podMetadataResult.expiresAt).toLocaleString(getRegionalLocale())}
                        <br />
                        <strong><LocalizedText source={"Display Name:"} /></strong>{' '}
                        {podMetadataResult.publishedPod?.displayName}
                        <br />
                        <strong><LocalizedText source={"Members:"} /></strong>{' '}
                        {podMetadataResult.publishedPod?.metadata?.memberCount ||
                          'Unknown'}
                      </p>
                    </Message>
                  ) : (
                    <Message warning>
                      <p><LocalizedText source={"Pod not found in DHT"} /></p>
                    </Message>
                  )}
                </div>
              )}
            </Card.Content>

            <Card.Content>
              <details>
                <summary><LocalizedText source={"Advanced DHT publishing controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Publishing or unpublishing pod metadata changes DHT-visible records. Confirm visibility, tags, focus content, and target pod ID before applying changes."} /></Message>
                <Grid>
                  <Grid.Column width={8}>
                  <Header size="small"><LocalizedText source={"Publish Pod to DHT"} /></Header>
                  <Form>
                    <Form.TextArea
                      label={interfaceText("Pod JSON")}
                      onChange={(e) => setPodToPublish(e.target.value)}
                      placeholder={"{\"id\": {\"value\": \"pod:artist:mb:daft-punk-hash\"}, \"displayName\": \"Daft Punk Fans\", \"visibility\": \"Listed\", \"focusType\": \"ContentId\", \"focusContentId\": {\"domain\": \"audio\", \"type\": \"artist\", \"id\": \"daft-punk-hash\"}, \"tags\": [\"electronic\", \"french-house\"], \"createdAt\": \"2024-01-01T00:00:00Z\", \"createdBy\": \"alice\", \"metadata\": {\"description\": \"A community for Daft Punk fans\", \"memberCount\": 150}}"}
                      rows={6}
                      value={podToPublish}
                     {...interfaceTextProps("Pod JSON")} dir="ltr"/>
                    <Button
                      tooltip={interfaceText("Publish this pod metadata to the DHT so mesh participants can discover it. Review its visibility, tags, and focus content before publishing.")}
                      disabled={publishingPod || !podToPublish.trim()}
                      loading={publishingPod}
                      onClick={handlePublishPod}
                      primary
                    >
                      <LocalizedText source={"Publish Pod"} /></Button>
                  </Form>

                  {podPublishingResult && (
                    <div style={{ marginTop: '1em' }}>
                      {podPublishingResult.error ? (
                        <Message error>
                          <p>
                            <LocalizedText source={"Failed to publish pod:"} />{" "}{podPublishingResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message success>
                          <Message.Header>
                            <LocalizedText source={"Pod Published Successfully"} /></Message.Header>
                          <p>
                            <strong><LocalizedText source={"Pod ID:"} /></strong>{' '}
                            {podPublishingResult.podId?.value ||
                              podPublishingResult.podId}
                            <br />
                            <strong><LocalizedText source={"DHT Key:"} /></strong>{' '}
                            {podPublishingResult.dhtKey}
                            <br />
                            <strong><LocalizedText source={"Published:"} /></strong>{' '}
                            {new Date(
                              podPublishingResult.publishedAt,
                            ).toLocaleString(getRegionalLocale())}
                            <br />
                            <strong><LocalizedText source={"Expires:"} /></strong>{' '}
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
                  <Header size="small"><LocalizedText source={"Unpublish Pod from DHT"} /></Header>
                  <Form>
                    <Form.Input
                      label={interfaceText("Pod ID")}
                      onChange={(e) => setPodToUnpublish(e.target.value)}
                      placeholder="pod:artist:mb:daft-punk-hash"
                      value={podToUnpublish}
                     {...interfaceTextProps("Pod ID")}/>
                    <Button
                      tooltip={interfaceText("Remove this pod’s metadata from the DHT so discovery no longer advertises it. Use this when you want to withdraw a listing.")}
                      color="red"
                      disabled={unpublishingPod || !podToUnpublish.trim()}
                      fluid
                      loading={unpublishingPod}
                      onClick={handleUnpublishPod}
                    >
                      <LocalizedText source={"Unpublish Pod"} /></Button>
                  </Form>

                  {podUnpublishResult && (
                    <div style={{ marginTop: '1em' }}>
                      {podUnpublishResult.error ? (
                        <Message error>
                          <p>
                            <LocalizedText source={"Failed to unpublish pod:"} />{" "}{podUnpublishResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message success>
                          <p><LocalizedText source={"Pod unpublished successfully from DHT"} /></p>
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
                  tooltip={interfaceText("Load publication counts and timing so you can review recent pod metadata publishing activity.")}
                  disabled={loadingPodStats}
                  loading={loadingPodStats}
                  onClick={handleLoadPodPublishingStats}
                  primary
                >
                  <LocalizedText source={"Load Pod Publishing Stats"} /></Button>
              </Button.Group>

              {podPublishingStats && !podPublishingStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header><LocalizedText source={"Pod Publishing Statistics"} /></Message.Header>
                    <p>
                      <strong><LocalizedText source={"Total Published:"} /></strong>{' '}
                      {podPublishingStats.totalPublished}
                      <br />
                      <strong><LocalizedText source={"Active Publications:"} /></strong>{' '}
                      {podPublishingStats.activePublications}
                      <br />
                      <strong><LocalizedText source={"Expired Publications:"} /></strong>{' '}
                      {podPublishingStats.expiredPublications}
                      <br />
                      <strong><LocalizedText source={"Failed Publications:"} /></strong>{' '}
                      {podPublishingStats.failedPublications}
                      <br />
                      <strong><LocalizedText source={"Avg Publish Time:"} /></strong>{' '}
                      {podPublishingStats.averagePublishTime
                        ? `${podPublishingStats.averagePublishTime.totalMilliseconds.toFixed(0)}ms`
                        : interfaceText('N/A')}
                      <br />
                      <strong><LocalizedText source={"Last Operation:"} /></strong>{' '}
                      {podPublishingStats.lastPublishOperation
                        ? new Date(
                            podPublishingStats.lastPublishOperation,
                          ).toLocaleString(getRegionalLocale())
                        : <LocalizedText source={"Never"} />}
                    </p>
                    {podPublishingStats.publicationsByVisibility &&
                      Object.keys(podPublishingStats.publicationsByVisibility)
                        .length > 0 && (
                        <div style={{ marginTop: '0.5em' }}>
                          <strong><LocalizedText source={"Publications by Visibility:"} /></strong>
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
                    <LocalizedText source={"Failed to load pod publishing stats:"} />{' '}
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
                <LocalizedText source={"Pod Membership Management"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Manage signed membership records in DHT with role-based access control"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Publishes membership state")} {...interfaceTextProps("Publishes membership state")}>
                <LocalizedText source={"Membership records can reveal peer IDs, roles, bans, public keys, and pod participation history. Verify the record before publishing it."} /></PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header><LocalizedText source={"Verify membership before changing it"} /></Message.Header>
                <p>
                  <LocalizedText source={"Getting, verifying, and loading membership stats are read-only. Publishing membership records, role changes, bans, and cleanup are grouped below as advanced membership mutation controls."} /></p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  {/* Get Membership */}
                  <Header size="small"><LocalizedText source={"Get Membership Record"} /></Header>
                  <Form>
                    <Form.Input
                      label={interfaceText("Pod ID")}
                      onChange={(e) => setMembershipPodId(e.target.value)}
                      placeholder="pod:artist:mb:daft-punk-hash"
                      value={membershipPodId}
                     {...interfaceTextProps("Pod ID")}/>
                    <Form.Input
                      label={interfaceText("Peer ID")}
                      onChange={(e) => setMembershipPeerId(e.target.value)}
                      placeholder={interfaceText("alice")}
                      value={membershipPeerId}
                     {...interfaceTextProps("Peer ID")}/>
                    <Button.Group fluid>
                      <Button
                        tooltip={interfaceText("Look up the selected peer’s membership record for this pod so you can review its role and status.")}
                        disabled={
                          gettingMembership ||
                          !membershipPodId.trim() ||
                          !membershipPeerId.trim()
                        }
                        loading={gettingMembership}
                        onClick={handleGetMembership}
                      >
                        <LocalizedText source={"Get Membership"} /></Button>
                      <Button
                        tooltip={interfaceText("Verify the selected peer’s signed membership record before relying on its role or ban status.")}
                        disabled={
                          verifyingMembership ||
                          !membershipPodId.trim() ||
                          !membershipPeerId.trim()
                        }
                        loading={verifyingMembership}
                        onClick={handleVerifyMembership}
                      >
                        <LocalizedText source={"Verify Membership"} /></Button>
                    </Button.Group>
                  </Form>

                  {/* Membership Results */}
                  {membershipResult && (
                    <div style={{ marginTop: '1em' }}>
                      {membershipResult.error ? (
                        <Message error>
                          <p>
                            <LocalizedText source={"Failed to get membership:"} />{" "}{membershipResult.error}
                          </p>
                        </Message>
                      ) : membershipResult.found ? (
                        <Message success>
                          <Message.Header><LocalizedText source={"Membership Found"} /></Message.Header>
                          <p>
                            <strong><LocalizedText source={"Pod ID:"} /></strong> {membershipResult.podId}
                            <br />
                            <strong><LocalizedText source={"Peer ID:"} /></strong> {membershipResult.peerId}
                            <br />
                            <strong><LocalizedText source={"Role:"} /></strong>{' '}
                            {membershipResult.signedRecord?.membership?.role}
                            <br />
                            <strong><LocalizedText source={"Banned:"} /></strong>{' '}
                            {membershipResult.signedRecord?.membership?.isBanned
                              ? <LocalizedText source={"Yes"} />
                              : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"Signature Valid:"} /></strong>{' '}
                            {membershipResult.isValidSignature ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"Joined:"} /></strong>{' '}
                            {membershipResult.signedRecord?.membership?.joinedAt
                              ? new Date(
                                  membershipResult.signedRecord.membership.joinedAt,
                                ).toLocaleString(getRegionalLocale())
                              : <LocalizedText source={"Unknown"} />}
                          </p>
                        </Message>
                      ) : (
                        <Message warning>
                          <p><LocalizedText source={"Membership not found in DHT"} /></p>
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
                            <LocalizedText source={"Failed to verify membership:"} />{' '}
                            {membershipVerification.error}
                          </p>
                        </Message>
                      ) : (
                        <Message info>
                          <Message.Header>
                            <LocalizedText source={"Membership Verification"} /></Message.Header>
                          <p>
                            <strong><LocalizedText source={"Valid Member:"} /></strong>{' '}
                            {membershipVerification.isValidMember
                              ? <LocalizedText source={"Yes"} />
                              : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"Role:"} /></strong>{' '}
                            {membershipVerification.role || 'None'}
                            <br />
                            <strong><LocalizedText source={"Banned:"} /></strong>{' '}
                            {membershipVerification.isBanned ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  <details>
                    <summary><LocalizedText source={"Advanced member mutation controls"} /></summary>
                    <Message warning>
                      <LocalizedText source={"Banning members and changing roles publish membership state for the selected pod and peer. Verify the current membership record before applying changes."} /></Message>
                  {/* Member Management */}
                  <Header size="small"><LocalizedText source={"Member Management"} /></Header>

                  {/* Ban Member */}
                  <Form style={{ marginBottom: '1em' }}>
                    <Form.Input
                      label={interfaceText("Ban Reason (optional)")}
                      onChange={(e) => setBanReason(e.target.value)}
                      placeholder={interfaceText("Violation of community rules")}
                      value={banReason}
                     {...interfaceTextProps("Ban Reason (optional)")}/>
                    <Button
                      tooltip={interfaceText("Ban the selected peer from this pod after reviewing the membership record and reason. This publishes a membership change.")}
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
                      <LocalizedText source={"Ban Member"} /></Button>
                  </Form>

                  {/* Change Role */}
                  <Form>
                    <Form.Select
                      label={interfaceText("New Role")}
                      onChange={(e, { value }) => setNewRole(value)}
                      options={[
                        { key: 'member', text: interfaceText("Member"), value: 'member' },
                        { key: 'mod', text: interfaceText("Moderator"), value: 'mod' },
                        { key: 'owner', text: interfaceText("Owner"), value: 'owner' },
                      ]}
                      value={newRole}
                     {...interfaceTextProps("New Role")}/>
                    <Button
                      tooltip={interfaceText("Change the selected peer’s pod role. Use this to grant or remove moderator or owner duties after verifying the peer.")}
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
                      <LocalizedText source={"Change Role"} /></Button>
                  </Form>

                  {/* Management Results */}
                  {banResult && (
                    <Message
                      style={{ marginTop: '1em' }}
                      success
                    >
                      <p><LocalizedText source={"Member banned successfully"} /></p>
                    </Message>
                  )}

                  {roleChangeResult && (
                    <Message
                      style={{ marginTop: '1em' }}
                      success
                    >
                      <p><LocalizedText source={"Member role changed successfully"} /></p>
                    </Message>
                  )}
                  </details>
                </Grid.Column>
              </Grid>
            </Card.Content>

            {/* Publish Membership */}
            <Card.Content>
              <details>
                <summary><LocalizedText source={"Advanced membership publishing controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Publishing membership records can expose peer IDs, roles, public keys, ban state, and pod participation history."} /></Message>
                <Header size="small"><LocalizedText source={"Publish Membership Record"} /></Header>
                <Form>
                  <Form.TextArea
                    label={interfaceText("Membership Record JSON")}
                    onChange={(e) => setMembershipRecord(e.target.value)}
                    placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "role": "member", "isBanned": false, "publicKey": "base64-ed25519-key", "joinedAt": "2024-01-01T00:00:00Z"}'
                    rows={4}
                    value={membershipRecord}
                   {...interfaceTextProps("Membership Record JSON")}/>
                  <Button
                    tooltip={interfaceText("Publish this signed membership record to the DHT so peers can verify participation and roles. Check peer IDs and key material first.")}
                    disabled={publishingMembership || !membershipRecord.trim()}
                    loading={publishingMembership}
                    onClick={handlePublishMembership}
                    primary
                  >
                    <LocalizedText source={"Publish Membership"} /></Button>
                </Form>

                {membershipPublishResult && (
                  <div style={{ marginTop: '1em' }}>
                    {membershipPublishResult.error ? (
                      <Message error>
                        <p>
                          <LocalizedText source={"Failed to publish membership:"} />{' '}
                          {membershipPublishResult.error}
                        </p>
                      </Message>
                    ) : (
                      <Message success>
                        <Message.Header>
                          <LocalizedText source={"Membership Published Successfully"} /></Message.Header>
                        <p>
                          <strong><LocalizedText source={"Pod ID:"} /></strong>{' '}
                          {membershipPublishResult.podId}
                          <br />
                          <strong><LocalizedText source={"Peer ID:"} /></strong>{' '}
                          {membershipPublishResult.peerId}
                          <br />
                          <strong><LocalizedText source={"DHT Key:"} /></strong>{' '}
                          {membershipPublishResult.dhtKey}
                          <br />
                          <strong><LocalizedText source={"Published:"} /></strong>{' '}
                          {new Date(
                            membershipPublishResult.publishedAt,
                          ).toLocaleString(getRegionalLocale())}
                          <br />
                          <strong><LocalizedText source={"Expires:"} /></strong>{' '}
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
                  tooltip={interfaceText("Load membership counts and expiration state so you can decide whether cleanup is needed.")}
                  disabled={loadingMembershipStats}
                  loading={loadingMembershipStats}
                  onClick={handleLoadMembershipStats}
                  primary
                >
                  <LocalizedText source={"Load Membership Stats"} /></Button>
              </Button.Group>

              <details style={{ marginTop: '1em' }}>
                <summary><LocalizedText source={"Advanced membership cleanup controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Cleanup removes expired membership records from local membership state. Load stats before running cleanup."} /></Message>
                <Button
                  tooltip={interfaceText("Remove expired membership records from local state to clear stale entries. Review membership stats first.")}
                  color="orange"
                  onClick={handleCleanupMemberships}
                >
                  <LocalizedText source={"Cleanup Expired"} /></Button>
              </details>

              {membershipStats && !membershipStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header><LocalizedText source={"Membership Statistics"} /></Message.Header>
                    <p>
                      <strong><LocalizedText source={"Total Memberships:"} /></strong>{' '}
                      {membershipStats.totalMemberships}
                      <br />
                      <strong><LocalizedText source={"Active Memberships:"} /></strong>{' '}
                      {membershipStats.activeMemberships}
                      <br />
                      <strong><LocalizedText source={"Banned Memberships:"} /></strong>{' '}
                      {membershipStats.bannedMemberships}
                      <br />
                      <strong><LocalizedText source={"Expired Memberships:"} /></strong>{' '}
                      {membershipStats.expiredMemberships}
                      <br />
                      <strong><LocalizedText source={"Last Operation:"} /></strong>{' '}
                      {membershipStats.lastOperation
                        ? new Date(
                            membershipStats.lastOperation,
                          ).toLocaleString(getRegionalLocale())
                        : <LocalizedText source={"Never"} />}
                    </p>
                    {membershipStats.membershipsByRole &&
                      Object.keys(membershipStats.membershipsByRole).length >
                        0 && (
                        <div style={{ marginTop: '0.5em' }}>
                          <strong><LocalizedText source={"Memberships by Role:"} /></strong>
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
                    <LocalizedText source={"Failed to load membership stats:"} />{" "}{membershipStats.error}
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
                <LocalizedText source={"Pod Membership Verification"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Verify membership status, message authenticity, and role permissions for pod security"} /></Card.Description>
              <PodWorkflowNotice
                color="blue"
                icon="check circle"
                title={interfaceText("Read-only verification")}
               {...interfaceTextProps("Read-only verification")}>
                <LocalizedText source={"Verification checks should not mutate pod state, but pasted messages and membership records can still contain sensitive peer or signature data."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Membership Verification */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Verify Membership Status"} /></Header>
              <Form>
                <Form.Group widths="equal">
                  <Form.Input
                    label={interfaceText("Pod ID")}
                    onChange={(e) => setVerifyPodId(e.target.value)}
                    placeholder="pod:artist:mb:daft-punk-hash"
                    value={verifyPodId}
                   {...interfaceTextProps("Pod ID")}/>
                  <Form.Input
                    label={interfaceText("Peer ID")}
                    onChange={(e) => setVerifyPeerId(e.target.value)}
                    placeholder={interfaceText("alice")}
                    value={verifyPeerId}
                   {...interfaceTextProps("Peer ID")}/>
                </Form.Group>
                <Button
                  tooltip={interfaceText("Check the selected peer’s membership proof and signature for this pod before relying on the claimed membership.")}
                  disabled={
                    verifyingMembership ||
                    !verifyPodId.trim() ||
                    !verifyPeerId.trim()
                  }
                  fluid
                  loading={verifyingMembership}
                  onClick={handleVerifyPodMembership}
                >
                  <LocalizedText source={"Verify Membership"} /></Button>
              </Form>

              {membershipVerificationResult && (
                <div style={{ marginTop: '1em' }}>
                  {membershipVerificationResult.error ? (
                    <Message error>
                      <p>
                        <LocalizedText source={"Failed to verify membership:"} />{' '}
                        {membershipVerificationResult.error}
                      </p>
                    </Message>
                  ) : (
                    <Message success>
                      <Message.Header>
                        <LocalizedText source={"Membership Verification Result"} /></Message.Header>
                      <p>
                        <strong><LocalizedText source={"Valid Member:"} /></strong>{' '}
                        {membershipVerificationResult.isValidMember
                          ? <LocalizedText source={"Yes"} />
                          : <LocalizedText source={"No"} />}
                        <br />
                        <strong><LocalizedText source={"Role:"} /></strong>{' '}
                        {membershipVerificationResult.role || 'None'}
                        <br />
                        <strong><LocalizedText source={"Banned:"} /></strong>{' '}
                        {membershipVerificationResult.isBanned ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
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
                  <Header size="small"><LocalizedText source={"Verify Message Authenticity"} /></Header>
                  <Form>
                    <Form.TextArea
                      label={interfaceText("Pod Message JSON")}
                      onChange={(e) => setMessageToVerify(e.target.value)}
                      placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello everyone!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                      rows={4}
                      value={messageToVerify}
                     {...interfaceTextProps("Pod Message JSON")}/>
                    <Button
                      tooltip={interfaceText("Validate the supplied message signature so you can detect altered or untrusted pod messages.")}
                      disabled={verifyingMessage || !messageToVerify.trim()}
                      fluid
                      loading={verifyingMessage}
                      onClick={handleVerifyMessage}
                    >
                      <LocalizedText source={"Verify Message"} /></Button>
                  </Form>

                  {messageVerificationResult && (
                    <div style={{ marginTop: '1em' }}>
                      {messageVerificationResult.error ? (
                        <Message error>
                          <p>
                            <LocalizedText source={"Failed to verify message:"} />{' '}
                            {messageVerificationResult.error}
                          </p>
                        </Message>
                      ) : (
                        <Message info>
                          <Message.Header>
                            <LocalizedText source={"Message Verification Result"} /></Message.Header>
                          <p>
                            <strong><LocalizedText source={"Valid:"} /></strong>{' '}
                            {messageVerificationResult.isValid ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"From Valid Member:"} /></strong>{' '}
                            {messageVerificationResult.isFromValidMember
                              ? <LocalizedText source={"Yes"} />
                              : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"Not Banned:"} /></strong>{' '}
                            {messageVerificationResult.isNotBanned
                              ? <LocalizedText source={"Yes"} />
                              : <LocalizedText source={"No"} />}
                            <br />
                            <strong><LocalizedText source={"Valid Signature:"} /></strong>{' '}
                            {messageVerificationResult.hasValidSignature
                              ? <LocalizedText source={"Yes"} />
                              : <LocalizedText source={"No"} />}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  {/* Role Checking */}
                  <Header size="small"><LocalizedText source={"Check Role Permissions"} /></Header>
                  <Form>
                    <Form.Group widths="equal">
                      <Form.Input
                        label={interfaceText("Pod ID")}
                        onChange={(e) => setRoleCheckPodId(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={roleCheckPodId}
                       {...interfaceTextProps("Pod ID")}/>
                      <Form.Input
                        label={interfaceText("Peer ID")}
                        onChange={(e) => setRoleCheckPeerId(e.target.value)}
                        placeholder={interfaceText("alice")}
                        value={roleCheckPeerId}
                       {...interfaceTextProps("Peer ID")}/>
                    </Form.Group>
                    <Form.Select
                      label={interfaceText("Required Role")}
                      onChange={(e, { value }) => setRequiredRole(value)}
                      options={[
                        { key: 'member', text: interfaceText("Member"), value: 'member' },
                        { key: 'mod', text: interfaceText("Moderator"), value: 'mod' },
                        { key: 'owner', text: interfaceText("Owner"), value: 'owner' },
                      ]}
                      value={requiredRole}
                     {...interfaceTextProps("Required Role")}/>
                    <Button
                      tooltip={interfaceText("Check whether this peer has the required role in the selected pod before authorizing an operation.")}
                      disabled={
                        checkingRole ||
                        !roleCheckPodId.trim() ||
                        !roleCheckPeerId.trim()
                      }
                      fluid
                      loading={checkingRole}
                      onClick={handleCheckRole}
                    >
                      <LocalizedText source={"Check Role"} /></Button>
                  </Form>

                  {roleCheckResult && (
                    <div style={{ marginTop: '1em' }}>
                      {roleCheckResult.error ? (
                        <Message error>
                          <p><LocalizedText source={"Failed to check role:"} />{" "}{roleCheckResult.error}</p>
                        </Message>
                      ) : (
                        <Message>
                          <Message.Header><LocalizedText source={"Role Check Result"} /></Message.Header>
                          <p>
                            <strong><LocalizedText source={"Has Required Role ("} />{requiredRole}):</strong>{' '}
                            {roleCheckResult.hasRole ? <LocalizedText source={"Yes"} /> : <LocalizedText source={"No"} />}
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
                  tooltip={interfaceText("Load local verification counts and timing so you can review membership and message signature checks.")}
                  disabled={loadingVerificationStats}
                  loading={loadingVerificationStats}
                  onClick={handleLoadVerificationStats}
                  primary
                >
                  <LocalizedText source={"Load Verification Stats"} /></Button>
              </Button.Group>

              {verificationStats && !verificationStats.error && (
                <div style={{ marginTop: '1em' }}>
                  <Message>
                    <Message.Header><LocalizedText source={"Verification Statistics"} /></Message.Header>
                    <p>
                      <strong><LocalizedText source={"Total Verifications:"} /></strong>{' '}
                      {verificationStats.totalVerifications}
                      <br />
                      <strong><LocalizedText source={"Successful:"} /></strong>{' '}
                      {verificationStats.successfulVerifications}
                      <br />
                      <strong><LocalizedText source={"Failed Membership:"} /></strong>{' '}
                      {verificationStats.failedMembershipChecks}
                      <br />
                      <strong><LocalizedText source={"Failed Signatures:"} /></strong>{' '}
                      {verificationStats.failedSignatureChecks}
                      <br />
                      <strong><LocalizedText source={"Banned Rejections:"} /></strong>{' '}
                      {verificationStats.bannedMemberRejections}
                      <br />
                      <strong><LocalizedText source={"Avg Time:"} /></strong>{' '}
                      {verificationStats.averageVerificationTimeMs.toFixed(2)}<LocalizedText source={"ms"} /><br />
                      <strong><LocalizedText source={"Last Verification:"} /></strong>{' '}
                      {verificationStats.lastVerification
                        ? new Date(
                            verificationStats.lastVerification,
                          ).toLocaleString(getRegionalLocale())
                        : <LocalizedText source={"Never"} />}
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
                    <LocalizedText source={"Failed to load verification stats:"} />{" "}{verificationStats.error}
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
                <LocalizedText source={"Pod Discovery"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Discover pods via DHT using name slugs, tags, and content associations"} /></Card.Description>
              <PodWorkflowNotice
                color="blue"
                icon="info circle"
                title={interfaceText("Mostly read-only discovery")}
               {...interfaceTextProps("Mostly read-only discovery")}>
                <LocalizedText source={"Search operations are read-only, but registering, updating, unregistering, or refreshing discovery data changes public pod discovery state."} /></PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message
                info
                size="small"
              >
                <Message.Header><LocalizedText source={"Find pods first"} /></Message.Header>
                <LocalizedText source={"Name, tag, content, and limited registry searches are the normal discovery path. Registry mutation controls are grouped below because they publish or remove public discovery records."} /></Message>
            </Card.Content>

            <Card.Content>
              <Grid>
                <Grid.Column width={4}>
                  {/* Discover by Name */}
                  <Header size="small"><LocalizedText source={"By Name"} /></Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByName(e.target.value)}
                      placeholder="daft-punk-fans"
                      value={discoverByName}
                    />
                    <Button
                      tooltip={interfaceText("Run a manual discovery lookup for pods matching this name. Use it to find a specific community; the query contacts the pod discovery service.")}
                      disabled={discoveringByName || !discoverByName.trim()}
                      fluid
                      loading={discoveringByName}
                      onClick={handleDiscoverByName}
                    >
                      <LocalizedText source={"Discover"} /></Button>
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
                          <p><LocalizedText source="Found {count} pods" values={{ count: nameDiscoveryResult.totalFound }} /></p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover by Tag */}
                  <Header size="small"><LocalizedText source={"By Tag"} /></Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByTag(e.target.value)}
                      placeholder={interfaceText("electronic")}
                      value={discoverByTag}
                     {...interfaceTextProps("electronic")}/>
                    <Button
                      tooltip={interfaceText("Run a manual discovery lookup for pods with this tag. Use it to browse a topic; the query contacts the pod discovery service.")}
                      disabled={discoveringByTag || !discoverByTag.trim()}
                      fluid
                      loading={discoveringByTag}
                      onClick={handleDiscoverByTag}
                    >
                      <LocalizedText source={"Discover"} /></Button>
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
                          <p><LocalizedText source="Found {count} pods" values={{ count: tagDiscoveryResult.totalFound }} /></p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover by Tags */}
                  <Header size="small"><LocalizedText source={"By Tags (AND)"} /></Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverTags(e.target.value)}
                      placeholder={interfaceText("electronic,french-house")}
                      value={discoverTags}
                     {...interfaceTextProps("electronic,french-house")}/>
                    <Button
                      tooltip={interfaceText("Run a manual lookup for pods matching the entered tags. Use it to narrow discovery to a combination of topics.")}
                      disabled={discoveringByTags || !discoverTags.trim()}
                      fluid
                      loading={discoveringByTags}
                      onClick={handleDiscoverByTags}
                    >
                      <LocalizedText source={"Discover"} /></Button>
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
                          <p><LocalizedText source="Found {count} pods" values={{ count: tagsDiscoveryResult.totalFound }} /></p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={4}>
                  {/* Discover All */}
                  <Header size="small"><LocalizedText source={"All Pods"} /></Header>
                  <Form>
                    <Form.Input
                      label={interfaceText("Limit")}
                      max="1000"
                      min="1"
                      onChange={(e) =>
                        setDiscoverLimit(Number.parseInt(e.target.value) || 50)
                      }
                      type="number"
                      value={discoverLimit}
                     {...interfaceTextProps("Limit")}/>
                    <Button
                      tooltip={interfaceText("Browse a bounded sample of discoverable pods. This performs a manual discovery request using the selected result limit.")}
                      disabled={discoveringAll}
                      fluid
                      loading={discoveringAll}
                      onClick={handleDiscoverAll}
                    >
                      <LocalizedText source={"Discover"} /></Button>
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
                          <p><LocalizedText source="Found {count} pods" values={{ count: allDiscoveryResult.totalFound }} /></p>
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
                  <Header size="small"><LocalizedText source={"By Content ID"} /></Header>
                  <Form>
                    <Form.Input
                      onChange={(e) => setDiscoverByContent(e.target.value)}
                      placeholder="content:audio:artist:daft-punk"
                      value={discoverByContent}
                    />
                    <Button
                      tooltip={interfaceText("Find pods linked to this content ID so you can browse communities about the item. This is a manual discovery lookup.")}
                      disabled={
                        discoveringByContent || !discoverByContent.trim()
                      }
                      fluid
                      loading={discoveringByContent}
                      onClick={handleDiscoverByContent}
                    >
                      <LocalizedText source={"Discover"} /></Button>
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
                          <p><LocalizedText source="Found {count} pods" values={{ count: contentDiscoveryResult.totalFound }} /></p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  {/* Discovery Stats */}
                  <Header size="small"><LocalizedText source={"Discovery Statistics"} /></Header>
                  <Button.Group fluid>
                    <Button
                      tooltip={interfaceText("Load discovery index counts and freshness so you can review the current local index state.")}
                      disabled={loadingDiscoveryStats}
                      loading={loadingDiscoveryStats}
                      onClick={handleLoadDiscoveryStats}
                    >
                      <LocalizedText source={"Load Stats"} /></Button>
                    <Button
                      tooltip={interfaceText("Refresh the pod discovery index and expire stale entries. Use this when discovery results appear out of date.")}
                      color="blue"
                      onClick={handleRefreshDiscovery}
                    >
                      <LocalizedText source={"Refresh"} /></Button>
                  </Button.Group>

                  {discoveryStats && !discoveryStats.error && (
                    <div style={{ marginTop: '0.5em' }}>
                      <Message size="tiny">
                        <p>
                          <strong><LocalizedText source={"Registered Pods:"} /></strong>{' '}
                          {discoveryStats.totalRegisteredPods}
                          <br />
                          <strong><LocalizedText source={"Active Entries:"} /></strong>{' '}
                          {discoveryStats.activeDiscoveryEntries}
                          <br />
                          <strong><LocalizedText source={"Expired Entries:"} /></strong>{' '}
                          {discoveryStats.expiredEntries}
                          <br />
                          <strong><LocalizedText source={"Avg Search Time:"} /></strong>{' '}
                          {discoveryStats.averageDiscoveryTime?.totalMilliseconds.toFixed(
                            0,
                          )}
                          <LocalizedText source={"ms"} /></p>
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
                  <LocalizedText source={"Advanced registry publishing controls"} /></summary>
                <Message
                  size="small"
                  warning
                >
                  <LocalizedText source={"Registering, unregistering, updating, or refreshing pod discovery entries changes public DHT-visible pod metadata."} /></Message>
                <Grid stackable>
                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Register Pod for Discovery"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Pod JSON (must have Visibility: Listed)")}
                        onChange={(e) => setPodToRegister(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "name": "Daft Punk Fans", "visibility": "Listed", "focusContentId": "content:audio:artist:daft-punk", "tags": ["electronic", "french-house"]}'
                        rows={3}
                        value={podToRegister}
                       {...interfaceTextProps("Pod JSON (must have Visibility: Listed)")} dir="ltr"/>
                      <Button
                        tooltip={interfaceText("Publish this pod to the discovery index so others can find it. Check its public metadata and visibility before registering.")}
                        disabled={registeringPod || !podToRegister.trim()}
                        loading={registeringPod}
                        onClick={handleRegisterPodForDiscovery}
                        primary
                      >
                        <LocalizedText source={"Register Pod"} /></Button>
                    </Form>

                    {podRegistrationResult && (
                      <div style={{ marginTop: '1em' }}>
                        {podRegistrationResult.error ? (
                          <Message error>
                            <p>
                              <LocalizedText source={"Failed to register pod:"} />{' '}
                              {podRegistrationResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              <LocalizedText source={"Pod Registered for Discovery"} /></Message.Header>
                            <p>
                              <strong><LocalizedText source={"Pod ID:"} /></strong>{' '}
                              {podRegistrationResult.podId}
                              <br />
                              <strong><LocalizedText source={"Discovery Keys:"} /></strong>{' '}
                              {podRegistrationResult.discoveryKeys?.join(', ')}
                              <br />
                              <strong><LocalizedText source={"Registered:"} /></strong>{' '}
                              {new Date(
                                podRegistrationResult.registeredAt,
                              ).toLocaleString(getRegionalLocale())}
                              <br />
                              <strong><LocalizedText source={"Expires:"} /></strong>{' '}
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
                    <Header size="small"><LocalizedText source={"Unregister Pod from Discovery"} /></Header>
                    <Form>
                      <Form.Input
                        label={interfaceText("Pod ID")}
                        onChange={(e) => setPodToUnregister(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={podToUnregister}
                       {...interfaceTextProps("Pod ID")}/>
                      <Button
                        tooltip={interfaceText("Remove this pod from the discovery index so future lookups stop returning it.")}
                        color="red"
                        disabled={unregisteringPod || !podToUnregister.trim()}
                        loading={unregisteringPod}
                        onClick={handleUnregisterPodFromDiscovery}
                      >
                        <LocalizedText source={"Unregister Pod"} /></Button>
                    </Form>

                    {podUnregistrationResult && (
                      <div style={{ marginTop: '1em' }}>
                        {podUnregistrationResult.error ? (
                          <Message error>
                            <p>
                              <LocalizedText source={"Failed to unregister pod:"} />{' '}
                              {podUnregistrationResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <p><LocalizedText source={"Pod unregistered from discovery successfully"} /></p>
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
                <LocalizedText source={"Pod Join/Leave Operations"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Manage signed pod membership operations with cryptographic Ed25519 verification and role-based approvals"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Publishes join and leave events")} {...interfaceTextProps("Publishes join and leave events")}>
                <LocalizedText source={"Join and leave requests can expose peer IDs, requested roles, public keys, signatures, and operator-provided messages."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Pending Requests */}
            <Card.Content>
              <Message info>
                <Message.Header><LocalizedText source={"Review pending requests first"} /></Message.Header>
                <p>
                  <LocalizedText source={"Loading pending join and leave requests only reads local pod state. The signed request and approval actions below publish membership events."} /></p>
                <p>
                  <LocalizedText source={"In Enforce mode, signatures must use the"} /><code>ed25519:&lt;base64 signature&gt;</code> <LocalizedText source={"format over the canonical join/leave payload and the supplied public key."} /></p>
              </Message>
              <Form>
                <Form.Input
                  label={interfaceText("Pod ID")}
                  onChange={(e) => setPendingPodId(e.target.value)}
                  placeholder="pod:artist:mb:daft-punk-hash"
                  value={pendingPodId}
                 {...interfaceTextProps("Pod ID")}/>
                <Button
                  tooltip={interfaceText("Load pending join and leave requests for this pod so you can review them before accepting a membership change.")}
                  disabled={loadingPendingRequests || !pendingPodId.trim()}
                  loading={loadingPendingRequests}
                  onClick={handleLoadPendingRequests}
                >
                  <LocalizedText source={"Load Pending Requests"} /></Button>
              </Form>

              {pendingJoinRequests && !pendingJoinRequests.error && (
                <div style={{ marginTop: '0.5em' }}>
                  <Message size="tiny">
                    <strong><LocalizedText source={"Join Requests:"} /></strong>{' '}
                    {pendingJoinRequests.pendingJoinRequests?.length || 0}
                  </Message>
                </div>
              )}

              {pendingLeaveRequests && !pendingLeaveRequests.error && (
                <div style={{ marginTop: '0.5em' }}>
                  <Message size="tiny">
                    <strong><LocalizedText source={"Leave Requests:"} /></strong>{' '}
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
                  <p><LocalizedText source={"Failed to load pending requests"} /></p>
                </Message>
              )}
            </Card.Content>

            <Card.Content>
              <details>
                <summary><LocalizedText source={"Advanced signed membership event controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"These controls submit signed JSON payloads and can publish pod membership changes. Use them after checking the pending request list for the target pod."} /></Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Request to Join Pod"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Join Request JSON (signed by requester)")}
                        onChange={(e) => setJoinRequestData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "requestedRole": "member", "publicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "nonce": "unique-request-nonce", "message": "Please let me join!"}'
                        rows={4}
                        value={joinRequestData}
                       {...interfaceTextProps("Join Request JSON (signed by requester)")}/>
                      <Button
                        tooltip={interfaceText("Submit a signed request to join the pod. Use this to ask its owner or moderators for membership; the request includes the supplied identity details.")}
                        disabled={requestingJoin || !joinRequestData.trim()}
                        loading={requestingJoin}
                        onClick={handleRequestJoin}
                        primary
                      >
                        <LocalizedText source={"Submit Join Request"} /></Button>
                    </Form>

                    {joinRequestResult && (
                      <div style={{ marginTop: '1em' }}>
                        {joinRequestResult.error ? (
                          <Message error>
                            <p>
                              <LocalizedText source={"Failed to submit join request:"} />{' '}
                              {joinRequestResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              <LocalizedText source={"Join Request Submitted"} /></Message.Header>
                            <p>
                              <strong><LocalizedText source={"Pod ID:"} /></strong> {joinRequestResult.podId}
                              <br />
                              <strong><LocalizedText source={"Peer ID:"} /></strong>{' '}
                              {joinRequestResult.peerId}
                              <br />
                              <strong><LocalizedText source={"Status:"} /></strong>{' '}
                              {joinRequestResult.success
                                ? <LocalizedText source={"Pending approval"} />
                                : <LocalizedText source={"Failed"} />}
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Accept Join Request"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Acceptance JSON (signed by owner/mod)")}
                        onChange={(e) => setAcceptanceData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "acceptedRole": "member", "acceptorPeerId": "bob", "acceptorPublicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Welcome!"}'
                        rows={4}
                        value={acceptanceData}
                       {...interfaceTextProps("Acceptance JSON (signed by owner/mod)")}/>
                      <Button
                        tooltip={interfaceText("Accept the signed join request and publish the membership change so the peer can participate. Verify the peer and requested role first.")}
                        disabled={acceptingJoin || !acceptanceData.trim()}
                        loading={acceptingJoin}
                        onClick={handleAcceptJoin}
                        positive
                      >
                        <LocalizedText source={"Accept Join"} /></Button>
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
                            <p><LocalizedText source={"Join accepted successfully"} /></p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Request to Leave Pod"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Leave Request JSON (signed by member)")}
                        onChange={(e) => setLeaveRequestData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "publicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Goodbye!"}'
                        rows={4}
                        value={leaveRequestData}
                       {...interfaceTextProps("Leave Request JSON (signed by member)")}/>
                      <Button
                        tooltip={interfaceText("Submit a signed request to leave the pod so its owner or moderators can review the membership change.")}
                        disabled={requestingLeave || !leaveRequestData.trim()}
                        loading={requestingLeave}
                        onClick={handleRequestLeave}
                      >
                        <LocalizedText source={"Submit Leave Request"} /></Button>
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
                            <p><LocalizedText source={"Leave request submitted"} /></p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small">
                      <LocalizedText source={"Accept Leave Request (Owner/Mod Only)"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Leave Acceptance JSON (signed by owner/mod)")}
                        onChange={(e) => setAcceptanceData(e.target.value)}
                        placeholder='{"podId": "pod:artist:mb:daft-punk-hash", "peerId": "alice", "acceptorPeerId": "bob", "acceptorPublicKey": "base64-ed25519-public-key", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature", "message": "Farewell!"}'
                        rows={4}
                        value={acceptanceData}
                       {...interfaceTextProps("Leave Acceptance JSON (signed by owner/mod)")}/>
                      <Button
                        tooltip={interfaceText("Accept the signed leave request and publish the membership removal. Verify the peer and request before accepting.")}
                        disabled={acceptingLeave || !acceptanceData.trim()}
                        loading={acceptingLeave}
                        negative
                        onClick={handleAcceptLeave}
                      >
                        <LocalizedText source={"Accept Leave"} /></Button>
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
                            <p><LocalizedText source={"Leave accepted successfully"} /></p>
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
                <LocalizedText source={"Pod Message Routing"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Decentralized message routing via overlay network with fanout and deduplication for reliable pod communication"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Sends pod messages")} {...interfaceTextProps("Sends pod messages")}>
                <LocalizedText source={"Routing actions can transmit message bodies and sender identifiers to selected peers or overlay routes. Use deduplication checks before resending."} /></PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header><LocalizedText source={"Check routing state before sending"} /></Message.Header>
                <p>
                  <LocalizedText source={"Deduplication checks and routing statistics are read-only. Sending messages, marking messages as seen, and cleanup are grouped below as advanced routing controls."} /></p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  <Header size="small"><LocalizedText source={"Message Deduplication"} /></Header>
                  <Form>
                    <Form.Group widths="equal">
                      <Form.Input
                        label={interfaceText("Message ID")}
                        onChange={(e) => setCheckMessageId(e.target.value)}
                        placeholder={interfaceText("msg123")}
                        value={checkMessageId}
                       {...interfaceTextProps("Message ID")}/>
                      <Form.Input
                        label={interfaceText("Pod ID")}
                        onChange={(e) => setCheckPodId(e.target.value)}
                        placeholder="pod:artist:mb:daft-punk-hash"
                        value={checkPodId}
                       {...interfaceTextProps("Pod ID")}/>
                    </Form.Group>
                    <Button
                      tooltip={interfaceText("Check whether a seen receipt exists for this message and pod before registering another one.")}
                      disabled={
                        checkingMessageSeen ||
                        !checkMessageId.trim() ||
                        !checkPodId.trim()
                      }
                      fluid
                      loading={checkingMessageSeen}
                      onClick={handleCheckMessageSeen}
                    >
                      <LocalizedText source={"Check Seen"} /></Button>
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
                            <LocalizedText source={"Message"} />{' '}
                            {messageSeenResult.isSeen
                              ? <LocalizedText source={"has been"} />
                              : <LocalizedText source={"has not been"} />}{' '}
                            <LocalizedText source={"seen in pod"} />{" "}{messageSeenResult.podId}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>

                <Grid.Column width={8}>
                  <Header size="small"><LocalizedText source={"Routing Statistics"} /></Header>
                  <Button
                    tooltip={interfaceText("Load message-routing counts and outcomes so you can review recent Pod delivery activity.")}
                    disabled={loadingRoutingStats}
                    fluid
                    loading={loadingRoutingStats}
                    onClick={handleLoadRoutingStats}
                    primary
                  >
                    <LocalizedText source={"Load Routing Stats"} /></Button>

                  {routingStats && !routingStats.error && (
                    <div style={{ marginTop: '1em' }}>
                      <Message>
                        <Message.Header><LocalizedText source={"Message Routing Statistics"} /></Message.Header>
                        <p>
                          <strong><LocalizedText source={"Total Messages Routed:"} /></strong>{' '}
                          {routingStats.totalMessagesRouted}
                          <br />
                          <strong><LocalizedText source={"Total Routing Attempts:"} /></strong>{' '}
                          {routingStats.totalRoutingAttempts}
                          <br />
                          <strong><LocalizedText source={"Successful Routes:"} /></strong>{' '}
                          {routingStats.successfulRoutingCount}
                          <br />
                          <strong><LocalizedText source={"Failed Routes:"} /></strong>{' '}
                          {routingStats.failedRoutingCount}
                          <br />
                          <strong><LocalizedText source={"Avg Routing Time:"} /></strong>{' '}
                          {routingStats.averageRoutingTimeMs.toFixed(2)}<LocalizedText source={"ms"} /><br />
                          <strong><LocalizedText source={"Deduplication Items:"} /></strong>{' '}
                          {routingStats.activeDeduplicationItems}
                          <br />
                          <strong><LocalizedText source={"Bloom Filter Fill:"} /></strong>{' '}
                          {(routingStats.bloomFilterFillRatio * 100).toFixed(1)}%
                          <br />
                          <strong><LocalizedText source={"Est. False Positive:"} /></strong>{' '}
                          {(routingStats.estimatedFalsePositiveRate * 100).toFixed(4)}%
                          <br />
                          <strong><LocalizedText source={"Last Operation:"} /></strong>{' '}
                          {routingStats.lastRoutingOperation
                            ? new Date(
                                routingStats.lastRoutingOperation,
                              ).toLocaleString(getRegionalLocale())
                            : <LocalizedText source={"Never"} />}
                        </p>
                      </Message>
                    </div>
                  )}

                  {routingStats?.error && (
                    <Message
                      error
                      style={{ marginTop: '1em' }}
                    >
                      <p><LocalizedText source={"Failed to load routing stats:"} />{" "}{routingStats.error}</p>
                    </Message>
                  )}
                </Grid.Column>
              </Grid>
            </Card.Content>

            <Card.Content>
              <details>
                <summary><LocalizedText source={"Advanced message routing controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Routing sends message bodies and sender identifiers to pod peers or overlay routes. Confirm deduplication state before resending messages."} /></Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Manual Message Routing"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Pod Message JSON")}
                        onChange={(e) => setRouteMessageData(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                        rows={4}
                        value={routeMessageData}
                       {...interfaceTextProps("Pod Message JSON")}/>
                      <Button
                        tooltip={interfaceText("Route this message through the pod messaging service to its eligible recipients. Use this to deliver a message to the pod.")}
                        disabled={routingMessage || !routeMessageData.trim()}
                        loading={routingMessage}
                        onClick={handleRouteMessage}
                        primary
                      >
                        <LocalizedText source={"Route Message"} /></Button>
                    </Form>

                    {routingResult && (
                      <div style={{ marginTop: '1em' }}>
                        {routingResult.error ? (
                          <Message error>
                            <p><LocalizedText source={"Failed to route message:"} />{" "}{routingResult.error}</p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              <LocalizedText source={"Message Routed Successfully"} /></Message.Header>
                            <p>
                              <strong><LocalizedText source={"Message ID:"} /></strong>{' '}
                              {routingResult.messageId}
                              <br />
                              <strong><LocalizedText source={"Pod ID:"} /></strong> {routingResult.podId}
                              <br />
                              <strong><LocalizedText source={"Target Peers:"} /></strong>{' '}
                              {routingResult.targetPeerCount}
                              <br />
                              <strong><LocalizedText source={"Successfully Routed:"} /></strong>{' '}
                              {routingResult.successfullyRoutedCount}
                              <br />
                              <strong><LocalizedText source={"Failed:"} /></strong>{' '}
                              {routingResult.failedRoutingCount}
                              <br />
                              <strong><LocalizedText source={"Duration:"} /></strong>{' '}
                              {routingResult.routingDuration?.totalMilliseconds?.toFixed(
                                0,
                              )}
                              <LocalizedText source={"ms"} /></p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Route to Specific Peers"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Pod Message JSON")}
                        onChange={(e) => setRouteToPeersMessage(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Direct message", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                        rows={3}
                        value={routeToPeersMessage}
                       {...interfaceTextProps("Pod Message JSON")}/>
                      <Form.Input
                        label={interfaceText("Target Peer IDs (comma-separated)")}
                        onChange={(e) => setRouteToPeersIds(e.target.value)}
                        placeholder={interfaceText("bob,charlie,diana")}
                        value={routeToPeersIds}
                       {...interfaceTextProps("Target Peer IDs (comma-separated)")}/>
                      <Button
                        tooltip={interfaceText("Route this message only to the listed peer IDs. Confirm the recipients because each selected peer receives the payload.")}
                        disabled={
                          routingToPeers ||
                          !routeToPeersMessage.trim() ||
                          !routeToPeersIds.trim()
                        }
                        fluid
                        loading={routingToPeers}
                        onClick={handleRouteMessageToPeers}
                      >
                        <LocalizedText source={"Route to Peers"} /></Button>
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
                              <LocalizedText source={"Routed to"} />{' '}
                              {routingToPeersResult.successfullyRoutedCount}/
                              {routingToPeersResult.targetPeerCount} <LocalizedText source={"peers"} /></p>
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
                <summary><LocalizedText source={"Advanced seen-state cleanup controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Marking messages as seen and cleanup mutate local routing deduplication state. Use them only after checking the target message and pod IDs."} /></Message>
                <Button
                  tooltip={interfaceText("Record a seen receipt for this message and pod so the message state reflects that it was observed.")}
                  color="blue"
                  disabled={!checkMessageId.trim() || !checkPodId.trim()}
                  onClick={handleRegisterMessageSeen}
                >
                  <LocalizedText source={"Mark Seen"} /></Button>
                <Button
                  tooltip={interfaceText("Remove expired seen-message receipts from local state to clear stale routing records.")}
                  color="red"
                  onClick={handleCleanupSeenMessages}
                >
                  <LocalizedText source={"Cleanup Seen Messages"} /></Button>
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
                <LocalizedText source={"Pod Message Storage"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"SQLite-backed message storage with full-text search and retention policies"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Mutates local message storage")} {...interfaceTextProps("Mutates local message storage")}>
                <LocalizedText source={"Cleanup, rebuild, and vacuum actions affect local pod message storage. Search and count actions are read-only."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Message Storage */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Storage Review"} /></Header>
              <Message info>
                <Message.Header><LocalizedText source={"Review storage before maintenance"} /></Message.Header>
                <p>
                  <LocalizedText source={"Storage statistics and message search are read-only. Cleanup, index rebuild, and vacuum operations are grouped below as advanced local maintenance actions."} /></p>
              </Message>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip={interfaceText("Load local message-storage counts so you can review database usage before cleanup or maintenance.")}
                  color="teal"
                  loading={storageStatsLoading}
                  onClick={() => handleGetStorageStats()}
                  size="small"
                >
                  <LocalizedText source={"Get Storage Stats"} /></Button>
              </div>

              <details style={{ marginBottom: '1em' }}>
                <summary><LocalizedText source={"Advanced storage maintenance controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Cleanup, search-index rebuild, and vacuum operations mutate local pod message storage. Review storage stats before running maintenance."} /></Message>
                <Button
                  tooltip={interfaceText("Permanently remove local pod messages older than 30 days. Use this to reclaim storage after reviewing the retention period.")}
                  color="purple"
                  loading={cleanupLoading}
                  onClick={() => handleCleanupMessages()}
                  size="small"
                >
                  <LocalizedText source={"Cleanup Old Messages (30 days)"} /></Button>

                <Button
                  tooltip={interfaceText("Rebuild the local message search index from stored messages if search results are stale or incomplete.")}
                  color="blue"
                  loading={rebuildIndexLoading}
                  onClick={() => handleRebuildSearchIndex()}
                  size="small"
                >
                  <LocalizedText source={"Rebuild Search Index"} /></Button>

                <Button
                  tooltip={interfaceText("Run SQLite vacuum to compact the local message database and reclaim unused file space. This may take time.")}
                  color="orange"
                  loading={vacuumLoading}
                  onClick={() => handleVacuumDatabase()}
                  size="small"
                >
                  <LocalizedText source={"Vacuum Database"} /></Button>
              </details>

              {storageStats && (
                <Message
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header><LocalizedText source={"Message Storage Statistics"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Messages:"} /></strong>{' '}
                    {storageStats.totalMessages?.toLocaleString(getRegionalLocale()) || 0}
                    <br />
                    <strong><LocalizedText source={"Estimated Size:"} /></strong>{' '}
                    {(storageStats.totalSizeBytes / (1_024 * 1_024)).toFixed(2)}{' '}
                    MB
                    <br />
                    <strong><LocalizedText source={"Oldest Message:"} /></strong>{' '}
                    {storageStats.oldestMessage
                      ? new Date(storageStats.oldestMessage).toLocaleString(getRegionalLocale())
                      : <LocalizedText source={"None"} />}
                    <br />
                    <strong><LocalizedText source={"Newest Message:"} /></strong>{' '}
                    {storageStats.newestMessage
                      ? new Date(storageStats.newestMessage).toLocaleString(getRegionalLocale())
                      : <LocalizedText source={"None"} />}
                    <br />
                    <strong><LocalizedText source={"Pods with Messages:"} /></strong>{' '}
                    {Object.keys(storageStats.messagesPerPod || {}).length}
                    <br />
                    <strong><LocalizedText source={"Active Channels:"} /></strong>{' '}
                    {Object.keys(storageStats.messagesPerChannel || {}).length}
                  </p>
                </Message>
              )}

              <Header size="small"><LocalizedText source={"Message Search"} /></Header>
              <Input
                action={
                  <Button
                    tooltip={interfaceText("Search stored pod messages locally for the entered text. Use this to find prior messages without contacting peers.")}
                    color="green"
                    disabled={!searchQuery.trim()}
                    loading={searchLoading}
                    onClick={() => handleSearchMessages()}
                  >
                    <LocalizedText source={"Search"} /></Button>
                }
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={interfaceText("Search messages...")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={searchQuery}
               {...interfaceTextProps("Search messages...")}/>

              {searchResults && searchResults.length > 0 && (
                <Message size="small">
                  <Message.Header>
                    <LocalizedText source={"Search Results ("} />{searchResults.length})
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
                  <LocalizedText source={"No messages found matching \""} />{searchQuery}"
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
                <LocalizedText source={"Pod Message Backfill"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Synchronize missed messages when peers rejoin pods"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Syncs local pod state")} {...interfaceTextProps("Syncs local pod state")}>
                <LocalizedText source={"Backfill sync uses last-seen timestamps to request missed messages. Confirm the target pod before syncing all channels."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Message Backfill */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Backfill Management"} /></Header>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip={interfaceText("Load local backfill status so you can see which pod histories may need to catch up.")}
                  color="purple"
                  loading={backfillStatsLoading}
                  onClick={() => handleGetBackfillStats()}
                  size="small"
                >
                  <LocalizedText source={"Get Backfill Stats"} /></Button>
              </div>

              {backfillStats && (
                <Message
                  size="small"
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header><LocalizedText source={"Backfill Statistics"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Requests Sent:"} /></strong>{' '}
                    {backfillStats.totalBackfillRequestsSent?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong><LocalizedText source={"Requests Received:"} /></strong>{' '}
                    {backfillStats.totalBackfillRequestsReceived?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong><LocalizedText source={"Messages Backfilled:"} /></strong>{' '}
                    {backfillStats.totalMessagesBackfilled?.toLocaleString(getRegionalLocale()) ||
                      0}
                    <br />
                    <strong><LocalizedText source={"Data Transferred:"} /></strong>{' '}
                    {(
                      backfillStats.totalBackfillBytesTransferred /
                      (1_024 * 1_024)
                    ).toFixed(2)}{' '}
                    MB
                    <br />
                    <strong><LocalizedText source={"Avg Duration:"} /></strong>{' '}
                    {backfillStats.averageBackfillDurationMs?.toFixed(2) || 0}<LocalizedText source={"ms"} /><br />
                    <strong><LocalizedText source={"Last Operation:"} /></strong>{' '}
                    {backfillStats.lastBackfillOperation
                      ? new Date(
                          backfillStats.lastBackfillOperation,
                        ).toLocaleString(getRegionalLocale())
                      : <LocalizedText source={"Never"} />}
                  </p>
                </Message>
              )}

              <Header size="small"><LocalizedText source={"Pod Backfill Review"} /></Header>
              <Input
                action={
                  <Button
                    tooltip={interfaceText("Read the latest stored message timestamps for this pod so you can inspect its current history position.")}
                    color="blue"
                    disabled={!backfillPodId.trim()}
                    onClick={() => handleGetLastSeenTimestamps()}
                  >
                    <LocalizedText source={"Get Timestamps"} /></Button>
                }
                onChange={(e) => setBackfillPodId(e.target.value)}
                placeholder={interfaceText("Pod ID for backfill sync")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={backfillPodId}
               {...interfaceTextProps("Pod ID for backfill sync")}/>

              <details style={{ marginBottom: '1em' }}>
                <summary><LocalizedText source={"Advanced backfill sync controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Backfill sync can request missed messages for the selected pod. Confirm timestamps and pod ID before starting sync."} /></Message>
                <Button
                  tooltip={interfaceText("Request missing message history for this pod from its backfill sources. Run it manually when history is missing; it can transfer data over the network.")}
                  color="green"
                  disabled={!backfillPodId.trim()}
                  loading={syncBackfillLoading}
                  onClick={() => handleSyncPodBackfill()}
                >
                  <LocalizedText source={"Sync Backfill"} /></Button>
              </details>

              {Object.keys(asObject(lastSeenTimestamps)).length > 0 && (
                  <Message size="small">
                    <Message.Header>
                      <LocalizedText source={"Last Seen Timestamps for Pod"} />{" "}{backfillPodId}
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
                    <LocalizedText source={"No last seen timestamps recorded for pod"} />{" "}{backfillPodId}
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
                <LocalizedText source={"Pod Channel Management"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Create, update, and manage channels within pods for organized messaging"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Mutates pod structure")} {...interfaceTextProps("Mutates pod structure")}>
                <LocalizedText source={"Channel create, update, and delete actions change how pod messages are organized. Deleting channels can disrupt routing and history workflows."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Channel Management */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Load Pod Channels"} /></Header>
              <Message info>
                <Message.Header><LocalizedText source={"Review channels before changing them"} /></Message.Header>
                <p>
                  <LocalizedText source={"Loading channels only reads local pod structure. Create, edit, and delete controls are grouped below as advanced operations because they change pod routing and history shape."} /></p>
              </Message>

              <Input
                action={
                  <Button
                    tooltip={interfaceText("Load the selected pod’s channel list so you can review its current discussion spaces.")}
                    color="blue"
                    disabled={!channelPodId.trim()}
                    loading={channelsLoading}
                    onClick={() => handleGetChannels()}
                  >
                    <LocalizedText source={"Load Channels"} /></Button>
                }
                onChange={(e) => setChannelPodId(e.target.value)}
                placeholder={interfaceText("Pod ID for channel management")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={channelPodId}
               {...interfaceTextProps("Pod ID for channel management")}/>

              <details style={{ marginBottom: '1em' }}>
                <summary><LocalizedText source={"Advanced channel mutation controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Creating, renaming, or deleting channels changes how pod messages are organized for members. Confirm the target pod ID before applying changes."} /></Message>

                {/* Create New Channel */}
                <Header size="tiny"><LocalizedText source={"Create New Channel"} /></Header>
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
                        <option value="General"><LocalizedText source={"General"} /></option>
                        <option value="Custom"><LocalizedText source={"Custom"} /></option>
                        <option value="Bound"><LocalizedText source={"Bound"} /></option>
                      </select>
                      <Button
                        tooltip={interfaceText("Create a channel in this pod so members can use a new discussion space.")}
                        color="green"
                        disabled={!newChannelName.trim() || !channelPodId.trim()}
                        loading={createChannelLoading}
                        onClick={() => handleCreateChannel()}
                      >
                        <LocalizedText source={"Create"} /></Button>
                    </>
                  }
                  onChange={(e) => setNewChannelName(e.target.value)}
                  placeholder={interfaceText("Channel name")}
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={newChannelName}
                 {...interfaceTextProps("Channel name")}/>
              </details>

              {/* Channels List */}
              {channels.length > 0 && (
                <div>
                  <Header size="tiny"><LocalizedText source={"Existing Channels"} /></Header>
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
                                      tooltip={interfaceText("Save the channel name and kind changes to the selected pod.")}
                                      color="green"
                                      disabled={!editChannelName.trim()}
                                      loading={updateChannelLoading}
                                      onClick={() =>
                                        handleUpdateChannel(channel.channelId)
                                      }
                                      size="small"
                                    >
                                      <LocalizedText source={"Save"} /></Button>
                                    <Button
                                      tooltip={interfaceText("Discard the unsaved channel edits and return to the channel list.")}
                                      onClick={() => cancelEditingChannel()}
                                      size="small"
                                    >
                                      <LocalizedText source={"Cancel"} /></Button>
                                  </>
                                }
                                onChange={(e) =>
                                  setEditChannelName(e.target.value)
                                }
                                placeholder={interfaceText("Channel name")}
                                style={{ width: '100%' }}
                                value={editChannelName}
                               {...interfaceTextProps("Channel name")}/>
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
                                  ID: {channel.channelId} <LocalizedText source={"• Type:"} />{" "}{channel.kind}
                                  {channel.bindingInfo &&
                                    ` • Binding: ${channel.bindingInfo}`}
                                </div>
                              </div>
                              <details>
                                <summary><LocalizedText source={"Actions"} /></summary>
                                <Button
                                  tooltip={interfaceText("Open this channel’s details for editing; changes are not saved until you choose Save.")}
                                  disabled={
                                    channel.name.toLowerCase() === 'general' &&
                                    channel.kind === 'General'
                                  }
                                  onClick={() => startEditingChannel(channel)}
                                  size="tiny"
                                >
                                  <LocalizedText source={"Edit"} /></Button>
                                <Button
                                  tooltip={interfaceText("Permanently delete this channel from the pod after confirmation. Use this only when the discussion space is no longer needed.")}
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
                                  <LocalizedText source={"Delete"} /></Button>
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
                  <LocalizedText source={"No channels found in pod"} />{" "}{channelPodId}<LocalizedText source={". Use advanced channel mutation controls to create the first channel."} /></Message>
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
                <LocalizedText source={"Pod Content Linking"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Create pods linked to specific content (music, videos, etc.) for focused discussions"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Can create content-linked pods")} {...interfaceTextProps("Can create content-linked pods")}>
                <LocalizedText source={"Content search and validation are read-only. Creating a content-linked pod can publish content identifiers and pod metadata depending on visibility settings."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Content Linking */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Content Search & Validation"} /></Header>

              {/* Content Search */}
              <Input
                action={
                  <Button
                    tooltip={interfaceText("Search content metadata so you can choose the exact item to link with a pod.")}
                    color="blue"
                    disabled={!contentSearchQuery.trim()}
                    loading={contentSearchLoading}
                    onClick={() => handleSearchContent()}
                  >
                    <LocalizedText source={"Search"} /></Button>
                }
                onChange={(e) => setContentSearchQuery(e.target.value)}
                placeholder={interfaceText("Search for content (artist, album, movie, etc.)")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={contentSearchQuery}
               {...interfaceTextProps("Search for content (artist, album, movie, etc.)")}/>

              {/* Search Results */}
              {contentSearchResults.length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny"><LocalizedText source={"Search Results"} /></Header>
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
                    tooltip={interfaceText("Validate this content ID and load its metadata before creating a linked pod.")}
                    color="green"
                    disabled={!contentId.trim()}
                    loading={contentValidationLoading}
                    onClick={() => handleValidateContentId()}
                  >
                    <LocalizedText source={"Validate"} /></Button>
                }
                onChange={(e) => setContentId(e.target.value)}
                placeholder={interfaceText("Content ID (e.g., content:audio:album:mb-release-id)")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={contentId}
               {...interfaceTextProps("Content ID (e.g., content:audio:album:mb-release-id)")}/>

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
                      ? <LocalizedText source={"✓ Valid Content ID"} />
                      : <LocalizedText source={"✗ Invalid Content ID"} />}
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
                  <Message.Header><LocalizedText source={"Content Metadata"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Title:"} /></strong> {contentMetadata.title}
                    <br />
                    <strong><LocalizedText source={"Artist:"} /></strong> {contentMetadata.artist}
                    <br />
                    <strong><LocalizedText source={"Type:"} /></strong> {contentMetadata.type} (
                    {contentMetadata.domain})
                  </p>
                </Message>
              )}

              {/* Pod Creation */}
              {contentValidation?.isValid && (
                <details>
                  <summary><LocalizedText source={"Advanced content-linked pod creation controls"} /></summary>
                  <Message warning>
                    <LocalizedText source={"Creating a content-linked pod can publish the selected content identifier, pod name, and visibility setting. Keep private or draft discussions unlisted unless public discovery is intended."} /></Message>
                  <Header size="small"><LocalizedText source={"Create Content-Linked Pod"} /></Header>

                  <Input
                    onChange={(e) => setNewPodName(e.target.value)}
                    placeholder={interfaceText("Pod name (auto-filled from content)")}
                    style={{ marginBottom: '1em', width: '100%' }}
                    value={newPodName}
                   {...interfaceTextProps("Pod name (auto-filled from content)")}/>

                  <div style={{ marginBottom: '1em' }}>
                    <label style={{ marginRight: '1em' }}><LocalizedText source={"Visibility:"} /></label>
                    <select
                      onChange={(e) => setNewPodVisibility(e.target.value)}
                      value={newPodVisibility}
                    >
                      <option value="Unlisted"><LocalizedText source={"Unlisted"} /></option>
                      <option value="Listed"><LocalizedText source={"Listed"} /></option>
                      <option value="Private"><LocalizedText source={"Private"} /></option>
                    </select>
                  </div>

                  <Button
                    tooltip={interfaceText("Create a pod linked to this content ID so members can discuss the item. Review its visibility before creation.")}
                    color="teal"
                    disabled={!newPodName.trim()}
                    loading={createPodLoading}
                    onClick={() => handleCreateContentLinkedPod()}
                  >
                    <LocalizedText source={"Create Content-Linked Pod"} /></Button>
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
                <LocalizedText source={"Pod Opinion Management"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Publish and view opinions on content variants within pods for quality assessment and community feedback"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Publishes opinion data")} {...interfaceTextProps("Publishes opinion data")}>
                <LocalizedText source={"Opinion publishing can expose peer preferences, ratings, confidence values, and content identifiers to other pod participants."} /></PodWorkflowNotice>
            </Card.Content>

            {/* Opinion Management */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Review Opinions"} /></Header>
              <Message info>
                <Message.Header><LocalizedText source={"Read pod opinions first"} /></Message.Header>
                <p>
                  <LocalizedText source={"Refreshing, listing, and aggregating opinions reads pod opinion state. Publishing opinions and recalculating affinity data are grouped below as advanced operations."} /></p>
              </Message>

              {/* Pod Selection */}
              <Input
                onChange={(e) => setOpinionPodId(e.target.value)}
                placeholder={interfaceText("Pod ID")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={opinionPodId}
               {...interfaceTextProps("Pod ID")}/>

              <Button
                tooltip={interfaceText("Refresh opinion records for this pod and update the current view. Use this when displayed community ratings may be stale.")}
                color="blue"
                disabled={!opinionPodId.trim()}
                loading={refreshOpinionsLoading}
                onClick={() => handleRefreshOpinions()}
                style={{ marginBottom: '1em' }}
              >
                <LocalizedText source={"Refresh Pod Opinions"} /></Button>

              {/* Content Opinions */}
              <Header size="tiny"><LocalizedText source={"Content Opinions"} /></Header>
              <Input
                onChange={(e) => setOpinionContentId(e.target.value)}
                placeholder={interfaceText("Content ID (e.g., content:audio:album:mb-id)")}
                style={{ marginBottom: '1em', width: '100%' }}
                value={opinionContentId}
               {...interfaceTextProps("Content ID (e.g., content:audio:album:mb-id)")}/>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip={interfaceText("Load opinions for this pod and content ID so you can review the available ratings and notes.")}
                  color="teal"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getOpinionsLoading}
                  onClick={() => handleGetOpinions()}
                  style={{ marginRight: '0.5em' }}
                >
                  <LocalizedText source={"Get Opinions"} /></Button>

                <Button
                  tooltip={interfaceText("Load rating counts and distribution for this pod and content item so you can review the data before publishing.")}
                  color="purple"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getStatsLoading}
                  onClick={() => handleGetOpinionStatistics()}
                >
                  <LocalizedText source={"Get Statistics"} /></Button>
              </div>

              {/* Opinion Statistics */}
              {opinionStatistics && (
                <Message
                  info
                  style={{ marginBottom: '1em' }}
                >
                  <Message.Header><LocalizedText source={"Opinion Statistics"} /></Message.Header>
                  <p>
                    <strong><LocalizedText source={"Total Opinions:"} /></strong>{' '}
                    {opinionStatistics.totalOpinions}
                    <br />
                    <strong><LocalizedText source={"Unique Variants:"} /></strong>{' '}
                    {opinionStatistics.uniqueVariants}
                    <br />
                    <strong><LocalizedText source={"Average Score:"} /></strong>{' '}
                    {opinionStatistics.averageScore.toFixed(1)}
                    <br />
                    <strong><LocalizedText source={"Score Range:"} /></strong> {opinionStatistics.minScore} -{' '}
                    {opinionStatistics.maxScore}
                    <br />
                    <strong><LocalizedText source={"Last Updated:"} /></strong>{' '}
                    {new Date(opinionStatistics.lastUpdated).toLocaleString(getRegionalLocale())}
                  </p>
                </Message>
              )}

              {/* Opinions List */}
              {opinions.length > 0 && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny"><LocalizedText source={"Opinions ("} />{opinions.length})</Header>
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
                            <strong><LocalizedText source={"Variant:"} /></strong>{' '}
                            {opinion.variantHash.slice(0, 8)}...
                            <br />
                            <strong><LocalizedText source={"Score:"} /></strong> {opinion.score}/10
                            {opinion.note && (
                              <>
                                <br />
                                <strong><LocalizedText source={"Note:"} /></strong> {opinion.note}
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
                <summary><LocalizedText source={"Advanced opinion publishing controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Publishing an opinion can expose the selected content ID, variant hash, score, note, and peer preference signal to pod participants."} /></Message>

                {/* Publish Opinion */}
                <Header size="small"><LocalizedText source={"Publish New Opinion"} /></Header>

                <Input
                  onChange={(e) => setOpinionVariantHash(e.target.value)}
                  placeholder={interfaceText("Variant Hash")}
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={opinionVariantHash}
                 {...interfaceTextProps("Variant Hash")}/>

                <div style={{ marginBottom: '1em' }}>
                  <label style={{ marginRight: '1em' }}><LocalizedText source={"Score (0-10):"} /></label>
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
                  placeholder={interfaceText("Optional note about this variant")}
                  style={{ marginBottom: '1em', width: '100%' }}
                  value={opinionNote}
                 {...interfaceTextProps("Optional note about this variant")}/>

                <Button
                  tooltip={interfaceText("Publish your score and note for this content to the pod. Review the content ID and variant hash because other participants may see this opinion.")}
                  color="green"
                  disabled={
                    !opinionPodId.trim() ||
                    !opinionContentId.trim() ||
                    !opinionVariantHash.trim()
                  }
                  loading={publishOpinionLoading}
                  onClick={() => handlePublishOpinion()}
                >
                  <LocalizedText source={"Publish Opinion"} /></Button>
              </details>
            </Card.Content>

            {/* Opinion Aggregation */}
            <Card.Content>
              <Header size="small"><LocalizedText source={"Opinion Aggregation & Consensus"} /></Header>

              <div style={{ marginBottom: '1em' }}>
                <Button
                  tooltip={interfaceText("Request the combined opinion view for this pod and content item to compare member feedback.")}
                  color="purple"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getAggregatedLoading}
                  onClick={() => handleGetAggregatedOpinions()}
                  style={{ marginRight: '0.5em' }}
                >
                  <LocalizedText source={"Get Aggregated Opinions"} /></Button>

                <Button
                  tooltip={interfaceText("Load member affinity scores for this pod so you can understand how current recommendations are ranked.")}
                  color="blue"
                  disabled={!opinionPodId.trim()}
                  loading={getAffinitiesLoading}
                  onClick={() => handleGetMemberAffinities()}
                  style={{ marginRight: '0.5em' }}
                >
                  <LocalizedText source={"Get Member Affinities"} /></Button>

                <Button
                  tooltip={interfaceText("Load recommendations derived from pod consensus so you can review what members collectively favor.")}
                  color="teal"
                  disabled={!opinionPodId.trim() || !opinionContentId.trim()}
                  loading={getRecommendationsLoading}
                  onClick={() => handleGetConsensusRecommendations()}
                  style={{ marginRight: '0.5em' }}
                >
                  <LocalizedText source={"Get Recommendations"} /></Button>

              </div>

              <details style={{ marginBottom: '1em' }}>
                <summary><LocalizedText source={"Advanced affinity recalculation controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"Updating member affinities recalculates stored relationship weights from pod opinion history. Review current opinions and affinities before running it."} /></Message>
                <Button
                  tooltip={interfaceText("Recompute stored member affinity values from available pod opinion data after ratings change.")}
                  color="orange"
                  disabled={!opinionPodId.trim()}
                  loading={updateAffinitiesLoading}
                  onClick={() => handleUpdateMemberAffinities()}
                >
                  <LocalizedText source={"Update Affinities"} /></Button>
              </details>

              {/* Aggregated Opinions */}
              {aggregatedOpinions && (
                <div style={{ marginBottom: '1em' }}>
                  <Header size="tiny"><LocalizedText source={"Aggregated Opinion Results"} /></Header>
                  <Message info>
                    <strong><LocalizedText source={"Weighted Average:"} /></strong>{' '}
                    {aggregatedOpinions.weightedAverageScore.toFixed(2)}/10
                    <br />
                    <strong><LocalizedText source={"Unweighted Average:"} /></strong>{' '}
                    {aggregatedOpinions.unweightedAverageScore.toFixed(2)}/10
                    <br />
                    <strong><LocalizedText source={"Consensus Strength:"} /></strong>{' '}
                    {(aggregatedOpinions.consensusStrength * 100).toFixed(1)}%
                    <br />
                    <strong><LocalizedText source={"Total Opinions:"} /></strong>{' '}
                    {aggregatedOpinions.totalOpinions}
                    <br />
                    <strong><LocalizedText source={"Unique Variants:"} /></strong>{' '}
                    {aggregatedOpinions.uniqueVariants}
                    <br />
                    <strong><LocalizedText source={"Contributing Members:"} /></strong>{' '}
                    {aggregatedOpinions.contributingMembers}
                  </Message>

                  {/* Variant Breakdown */}
                  {aggregatedOpinions.variantAggregates.length > 0 && (
                    <div style={{ marginTop: '1em' }}>
                      <Header size="tiny"><LocalizedText source={"Variant Analysis"} /></Header>
                      {asArray(aggregatedOpinions.variantAggregates).map(
                        (variant, index) => (
                          <Card
                            key={index}
                            style={{ marginBottom: '0.5em' }}
                          >
                            <Card.Content style={{ padding: '0.5em' }}>
                              <div>
                                <strong><LocalizedText source={"Variant:"} /></strong>{' '}
                                {variant.variantHash.slice(0, 8)}...
                                <br />
                                <strong><LocalizedText source={"Weighted Score:"} /></strong>{' '}
                                {variant.weightedAverageScore.toFixed(2)}/10
                                <br />
                                <strong><LocalizedText source={"Unweighted Score:"} /></strong>{' '}
                                {variant.unweightedAverageScore.toFixed(2)}/10
                                <br />
                                <strong><LocalizedText source={"Opinions:"} /></strong>{' '}
                                {variant.opinionCount}
                                <br />
                                <strong><LocalizedText source={"Agreement:"} /></strong>{' '}
                                {(
                                  1 -
                                  variant.scoreStandardDeviation / 5
                                ).toFixed(2)}{' '}
                                <LocalizedText source={"(lower std dev = higher agreement)"} /></div>
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
                  <Header size="tiny"><LocalizedText source={"Consensus Recommendations"} /></Header>
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
                          <strong><LocalizedText source={"Variant:"} /></strong>{' '}
                          {rec.variantHash.slice(0, 8)}...
                          <br />
                          <strong><LocalizedText source={"Recommendation:"} /></strong>{' '}
                          {rec.recommendation
                            .replaceAll(/([A-Z])/g, ' $1')
                            .trim()}
                          <br />
                          <strong><LocalizedText source={"Consensus Score:"} /></strong>{' '}
                          {(rec.consensusScore * 100).toFixed(1)}%<br />
                          <strong><LocalizedText source={"Reasoning:"} /></strong> {rec.reasoning}
                          <br />
                          <small>
                            <strong><LocalizedText source={"Factors:"} /></strong>{' '}
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
                    <LocalizedText source={"Member Affinities ("} />{Object.keys(asObject(memberAffinities)).length})
                  </Header>
                  {Object.entries(asObject(memberAffinities)).map(
                    ([peerId, affinity], index) => (
                      <Card
                        key={index}
                        style={{ marginBottom: '0.5em' }}
                      >
                        <Card.Content style={{ padding: '0.5em' }}>
                          <div>
                            <strong><LocalizedText source={"Peer:"} /></strong> {peerId.slice(0, 8)}...
                            <br />
                            <strong><LocalizedText source={"Affinity Score:"} /></strong>{' '}
                            {(affinity.affinityScore * 100).toFixed(1)}%<br />
                            <strong><LocalizedText source={"Trust Score:"} /></strong>{' '}
                            {(affinity.trustScore * 100).toFixed(1)}%<br />
                            <strong><LocalizedText source={"Messages:"} /></strong> {affinity.messageCount}
                            <br />
                            <strong><LocalizedText source={"Opinions:"} /></strong> {affinity.opinionCount}
                            <br />
                            <small>
                              <LocalizedText source={"Last Activity:"} />{' '}
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
                <LocalizedText source={"Pod Message Signing"} /></Card.Header>
              <Card.Description>
                <LocalizedText source={"Cryptographic signing and verification of pod messages for authenticity and integrity"} /></Card.Description>
              <PodWorkflowNotice title={interfaceText("Handles key material")} {...interfaceTextProps("Handles key material")}>
                <LocalizedText source={"Signing and key generation workflows may expose private keys or signed payloads in the browser. Treat pasted keys and generated output as sensitive."} /></PodWorkflowNotice>
            </Card.Content>

            <Card.Content>
              <Message info>
                <Message.Header><LocalizedText source={"Verify before generating signatures"} /></Message.Header>
                <p>
                  <LocalizedText source={"Signature verification and signing statistics do not expose private key material. Signing and key generation controls are grouped below as advanced operations."} /></p>
              </Message>
              <Grid>
                <Grid.Column width={8}>
                  {/* Signature Verification */}
                  <Header size="small"><LocalizedText source={"Verify Message Signature"} /></Header>
                  <Form>
                    <Form.TextArea
                      label={interfaceText("Pod Message JSON (with signature)")}
                      onChange={(e) => setMessageToVerify(e.target.value)}
                      placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789, "signature": "ed25519:base64-signature"}'
                      rows={4}
                      value={messageToVerify}
                     {...interfaceTextProps("Pod Message JSON (with signature)")}/>
                    <Button
                      tooltip={interfaceText("Verify the supplied message signature locally so you can check authenticity without routing the message.")}
                      disabled={verifyingSignature || !messageToVerify.trim()}
                      fluid
                      loading={verifyingSignature}
                      onClick={handleVerifySignature}
                    >
                      <LocalizedText source={"Verify Signature"} /></Button>
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
                            <LocalizedText source={"Message"} />{" "}{verificationResult.messageId}<LocalizedText source={": Signature is"} />{' '}
                            {verificationResult.isValid ? 'VALID' : 'INVALID'}
                          </p>
                        </Message>
                      )}
                    </div>
                  )}
                </Grid.Column>
                <Grid.Column width={8}>
                  {/* Signing Statistics */}
                  <Header size="small"><LocalizedText source={"Signing Statistics"} /></Header>
                  <Button.Group fluid>
                    <Button
                      tooltip={interfaceText("Load local signing and verification counts so you can review recent signature operations.")}
                      disabled={loadingSigningStats}
                      loading={loadingSigningStats}
                      onClick={handleLoadSigningStats}
                    >
                      <LocalizedText source={"Load Stats"} /></Button>
                  </Button.Group>

                  {signingStats && !signingStats.error && (
                    <div style={{ marginTop: '0.5em' }}>
                      <Message size="tiny">
                        <p>
                          <strong><LocalizedText source={"Signatures Created:"} /></strong>{' '}
                          {signingStats.totalSignaturesCreated}
                          <br />
                          <strong><LocalizedText source={"Signatures Verified:"} /></strong>{' '}
                          {signingStats.totalSignaturesVerified}
                          <br />
                          <strong><LocalizedText source={"Successful:"} /></strong>{' '}
                          {signingStats.successfulVerifications}
                          <br />
                          <strong><LocalizedText source={"Failed:"} /></strong>{' '}
                          {signingStats.failedVerifications}
                          <br />
                          <strong><LocalizedText source={"Avg Sign Time:"} /></strong>{' '}
                          {signingStats.averageSigningTimeMs.toFixed(2)}<LocalizedText source={"ms"} /><br />
                          <strong><LocalizedText source={"Avg Verify Time:"} /></strong>{' '}
                          {signingStats.averageVerificationTimeMs.toFixed(2)}<LocalizedText source={"ms"} /></p>
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
                <summary><LocalizedText source={"Advanced key material and signing controls"} /></summary>
                <Message warning>
                  <LocalizedText source={"These controls handle private keys or create signed payloads that may be routed to other pod members. Keep generated private keys out of logs and screenshots."} /></Message>
                <Grid>
                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Sign Pod Message"} /></Header>
                    <Form>
                      <Form.TextArea
                        label={interfaceText("Pod Message JSON")}
                        onChange={(e) => setMessageToSign(e.target.value)}
                        placeholder='{"messageId": "msg123", "channelId": "pod:artist:mb:daft-punk-hash:general", "senderPeerId": "alice", "body": "Hello pod!", "timestampUnixMs": 1703123456789}'
                        rows={3}
                        value={messageToSign}
                       {...interfaceTextProps("Pod Message JSON")}/>
                      <Form.Input
                        label={interfaceText("Private Key")}
                        onChange={(e) => setPrivateKeyForSigning(e.target.value)}
                        placeholder={interfaceText("base64-encoded private key")}
                        type="password"
                        value={privateKeyForSigning}
                       {...interfaceTextProps("Private Key")}/>
                      <Button
                        tooltip={interfaceText("Sign this message with the supplied private key so it can be authenticated before routing. Signing does not send it to pod members.")}
                        disabled={
                          signingMessage ||
                          !messageToSign.trim() ||
                          !privateKeyForSigning.trim()
                        }
                        loading={signingMessage}
                        onClick={handleSignMessage}
                        primary
                      >
                        <LocalizedText source={"Sign Message"} /></Button>
                    </Form>

                    {signedMessageResult && (
                      <div style={{ marginTop: '1em' }}>
                        {signedMessageResult.error ? (
                          <Message error>
                            <p>
                              <LocalizedText source={"Failed to sign message:"} />{' '}
                              {signedMessageResult.error}
                            </p>
                          </Message>
                        ) : (
                          <Message success>
                            <Message.Header>
                              <LocalizedText source={"Message Signed Successfully"} /></Message.Header>
                            <p>
                              <strong><LocalizedText source={"Message ID:"} /></strong>{' '}
                              {signedMessageResult.messageId}
                              <br />
                              <strong><LocalizedText source={"Channel:"} /></strong>{' '}
                              {signedMessageResult.channelId}
                              <br />
                              <strong><LocalizedText source={"Signature:"} /></strong>{' '}
                              {signedMessageResult.signature?.slice(0, 50)}...
                            </p>
                          </Message>
                        )}
                      </div>
                    )}
                  </Grid.Column>

                  <Grid.Column width={8}>
                    <Header size="small"><LocalizedText source={"Generate Key Pair"} /></Header>
                    <Form>
                      <Button
                        tooltip={interfaceText("Generate a new key pair for pod message signing. Keep the private key secret and store it securely before clearing this result.")}
                        disabled={generatingKeyPair}
                        fluid
                        loading={generatingKeyPair}
                        onClick={handleGenerateKeyPair}
                      >
                        <LocalizedText source={"Generate New Key Pair"} /></Button>
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
                            <Message.Header><LocalizedText source={"Key Pair Generated"} /></Message.Header>
                            <p>
                              <strong><LocalizedText source={"Public Key:"} /></strong>{' '}
                              {generatedKeyPair.publicKey?.slice(0, 30)}...
                              <br />
                              <strong><LocalizedText source={"Private Key:"} /></strong>{' '}
                              {generatedKeyPair.privateKey?.slice(0, 30)}...
                              <br />
                              <em><LocalizedText source={"Keep private key secure."} /></em>
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
                <LocalizedText source={"Supported Hash Algorithms"} /></Header>
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
