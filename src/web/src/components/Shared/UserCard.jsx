import LocalizedText from "./LocalizedText";
import { formatRegionalNumber, useRegionalLocale } from '../../lib/regionalFormat';
import { interfaceText } from '../../lib/interfaceLocale';
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import './UserCard.css';
import * as opinions from '../../lib/opinions';
import * as security from '../../lib/security';
import * as soulseekDiscovery from '../../lib/soulseekDiscovery';
import * as users from '../../lib/users';
import React, { Component } from 'react';
import { Icon, Popup } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const USER_DATA_CACHE_TTL_MS = 5 * 60 * 1000;
const USER_DATA_MAX_CONCURRENT = 4;
const userDataCache = new Map();
const userDataInflight = new Map();
const userDataQueue = [];
let activeUserDataRequests = 0;

const getCachedUserData = (username) => {
  const cached = userDataCache.get(username);

  if (!cached || cached.expiresAt <= Date.now()) {
    userDataCache.delete(username);
    return null;
  }

  return cached.data;
};

const setCachedUserData = (username, data) => {
  userDataCache.set(username, {
    data,
    expiresAt: Date.now() + USER_DATA_CACHE_TTL_MS,
  });
};

const runNextUserDataRequest = () => {
  while (
    activeUserDataRequests < USER_DATA_MAX_CONCURRENT &&
    userDataQueue.length > 0
  ) {
    const request = userDataQueue.shift();
    activeUserDataRequests += 1;

    request()
      .catch(() => {})
      .finally(() => {
        activeUserDataRequests -= 1;
        runNextUserDataRequest();
      });
  }
};

const enqueueUserDataRequest = (request) => {
  userDataQueue.push(request);
  runNextUserDataRequest();
};

const scheduleAfterPaint = (callback) => {
  if (typeof window === 'undefined') {
    callback();
    return undefined;
  }

  if (typeof window.requestIdleCallback === 'function') {
    const idleHandle = window.requestIdleCallback(callback, { timeout: 1_500 });
    return () => window.cancelIdleCallback?.(idleHandle);
  }

  const timeout = window.setTimeout(callback, 250);
  return () => window.clearTimeout(timeout);
};

class UserCard extends Component {
  constructor(props) {
    super(props);
    this.state = {
      info: this.props.info || null,
      interests: null,
      interestsError: null,
      interestsLoading: false,
      loading: false,
      opinionSummary: null,
      reputation: null,
    };
    this.cancelScheduledFetch = null;
    this.mounted = false;
    this.userDataRequested = false;
  }

  componentDidMount() {
    this.mounted = true;
    const cached = getCachedUserData(this.props.username);
    if (cached) {
      this.userDataRequested = true;
      this.setState({ ...cached, info: this.props.info || cached.info });
    } else if (!this.props.deferSupplementalData) {
      this.scheduleUserDataFetch();
    }
  }

  componentDidUpdate(previousProps) {
    if (previousProps.username !== this.props.username) {
      this.cancelScheduledFetch?.();
      this.userDataRequested = false;
      const cached = getCachedUserData(this.props.username);
      const nextState = {
        interests: null,
        interestsError: null,
        interestsLoading: false,
        info: this.props.info || null,
        loading: false,
        opinionSummary: null,
        reputation: null,
      };

      if (cached) {
        this.userDataRequested = true;
        this.setState({ ...nextState, ...cached, info: this.props.info || cached.info });
      } else {
        this.setState(nextState);
      }

      if (!cached && !this.props.deferSupplementalData) {
        this.scheduleUserDataFetch();
      }
    } else if (previousProps.info !== this.props.info) {
      this.setState({ info: this.props.info || null });
    }

    if (
      previousProps.deferSupplementalData &&
      !this.props.deferSupplementalData
    ) {
      this.scheduleUserDataFetch();
    }
  }

  componentWillUnmount() {
    this.mounted = false;
    this.cancelScheduledFetch?.();
  }

  scheduleUserDataFetch = () => {
    const { username } = this.props;
    if (!username || this.userDataRequested) return;

    this.userDataRequested = true;

    const cached = getCachedUserData(username);
    if (cached) {
      this.setState({ ...cached, info: this.props.info || cached.info });
      return;
    }

    this.cancelScheduledFetch = scheduleAfterPaint(() => {
      enqueueUserDataRequest(() => this.fetchUserData(username));
    });
  };

  fetchUserData = async (username) => {
    const cached = getCachedUserData(username);
    if (cached) {
      if (this.mounted && this.props.username === username) {
        this.setState({ ...cached, info: this.props.info || cached.info });
      }

      return;
    }

    try {
      if (this.mounted && this.props.username === username) {
        this.setState({ loading: true });
      }

      let userDataPromise = userDataInflight.get(username);

      if (!userDataPromise) {
        userDataPromise = Promise.allSettled([
          this.props.info
            ? Promise.resolve({ data: this.props.info })
            : users.getInfo({ quietUnavailable: true, username }),
          security.getReputation(username).catch(() => null),
          opinions.getOpinionSummary({
            subjectId: username,
            subjectType: 'User',
          }).catch(() => null),
        ]).then(([infoResponse, reputationData, opinionData]) => ({
          info:
            infoResponse.status === 'fulfilled' && infoResponse.value?.data
              ? infoResponse.value.data
              : null,
          loading: false,
          opinionSummary:
            opinionData.status === 'fulfilled' && opinionData.value?.data
              ? opinionData.value.data
              : null,
          reputation:
            reputationData.status === 'fulfilled' && reputationData.value
              ? reputationData.value
              : null,
        }));

        userDataInflight.set(username, userDataPromise);
      }

      const userData = await userDataPromise;

      setCachedUserData(username, userData);
      userDataInflight.delete(username);

      if (this.mounted && this.props.username === username) {
        this.setState({ ...userData, info: this.props.info || userData.info });
      }
    } catch {
      userDataInflight.delete(username);
      if (this.mounted && this.props.username === username) {
        this.setState({ loading: false });
      }
    }
  };

  requestSupplementalData = () => {
    if (this.props.deferSupplementalData) {
      this.scheduleUserDataFetch();
    }
  };

  fetchInterests = async () => {
    const { username } = this.props;
    const { interests, interestsLoading } = this.state;
    if (!username || interests || interestsLoading) return;

    this.setState({ interestsError: null, interestsLoading: true });

    try {
      const response = await soulseekDiscovery.getUserInterests({
        username,
      });
      const responseInterests =
        response.data && typeof response.data === 'object' && !Array.isArray(response.data)
          ? response.data
          : {};

      this.setState({
        interests: responseInterests,
        interestsLoading: false,
      });
    } catch (error) {
      this.setState({
        interestsError: getApiErrorMessage(error, { t: interfaceText }),
        interestsLoading: false,
      });
    }
  };

  getReputationColor = (score) => {
    if (score === null || score === undefined) return 'grey';
    if (score >= 80) return 'purple'; // Amazing (80-100)
    if (score >= 60) return 'green'; // Good (60-79)
    if (score >= 40) return 'olive'; // OK (40-59)
    if (score >= 20) return 'orange'; // Poor (20-39)
    return 'red'; // Very poor (0-19)
  };

  getOpinionColor = (summary) => {
    const score = Number(summary?.weightedScore ?? 0);
    if (!summary || Number(summary.total ?? 0) === 0) return 'grey';
    if (score > 0.15) return 'green';
    if (score < -0.15) return 'red';
    return 'olive';
  };

  getOpinionValue = (summary, formatNumber) => {
    if (!summary || Number(summary.total ?? 0) === 0) return '?';
    const score = Number(summary.weightedScore ?? 0);
    if (Math.abs(score) < 0.05) return formatNumber(0);
    const formattedScore = formatNumber(Math.abs(score), {
      maximumFractionDigits: 1,
      minimumFractionDigits: 1,
    });
    return score > 0 ? `+${formattedScore}` : `-${formattedScore}`;
  };

  renderInterestPopup = () => {
    const { username } = this.props;
    const { interests, interestsError, interestsLoading } = this.state;

    if (interestsLoading) {
      return (
        <span>
          <Icon
            loading
            name="spinner"
          />{' '}
          <LocalizedText source={"Loading native interests"} /></span>
      );
    }

    if (interestsError) {
      return <span>{interestsError}</span>;
    }

    const liked = asArray(interests?.liked ?? interests?.Liked);
    const hated = asArray(interests?.hated ?? interests?.Hated);

    if (!interests) {
      return <span><LocalizedText source={"Click to load native Soulseek interests for"} />{" "}{username}.</span>;
    }

    return (
      <div className="user-card-interest-popup">
        <div className="user-card-interest-section">
          <strong><LocalizedText source={"Liked"} /></strong>
          <div>
            {liked.length === 0
              ? <LocalizedText source={"None reported"} />
              : liked.slice(0, 12).map((interest) => (
                <span
                  className="user-card-interest user-card-interest-liked"
                  key={`liked-${interest}`}
                >
                  {interest}
                </span>
              ))}
          </div>
        </div>
        <div className="user-card-interest-section">
          <strong><LocalizedText source={"Hated"} /></strong>
          <div>
            {hated.length === 0
              ? <LocalizedText source={"None reported"} />
              : hated.slice(0, 12).map((interest) => (
                <span
                  className="user-card-interest user-card-interest-hated"
                  key={`hated-${interest}`}
                >
                  {interest}
                </span>
              ))}
          </div>
        </div>
      </div>
    );
  };

  render() {
    const { children, inline = true, username } = this.props;
    const { info, loading, opinionSummary, reputation } = this.state;

    const reputationScore = reputation?.score ?? null;
    const reputationColor = this.getReputationColor(reputationScore);
    const formatNumber = (value, options) =>
      formatRegionalNumber(value, options, this.props.regionalLocale);

    // Build compact stats display - always show placeholders if no data
    const stats = [];

    // Reputation shield badge (always show, grayed if no data)
    stats.push({
      color: reputationScore === null ? 'grey' : reputationColor,
      glow: reputationScore !== null && reputationScore >= 70, // Glow effect for high reputation
      icon: 'shield alternate',
      key: 'rep',
      tooltip:
        reputationScore === null
          ? <LocalizedText source={"Reputation unavailable"} />
          : <LocalizedText source={"Reputation Score: {score}/100"} values={{ score: formatNumber(reputationScore) }} />,
      value: reputationScore === null ? '?' : formatNumber(reputationScore),
    });

    stats.push({
      color: this.getOpinionColor(opinionSummary),
      icon: 'thumbs up outline',
      key: 'opinion',
      tooltip: opinionSummary?.total
        ? <LocalizedText
          source={"Canonical opinions: {positive} positive, {negative} negative, weighted {weightedScore}"}
          values={{
            positive: formatNumber(opinionSummary.positive || 0),
            negative: formatNumber(opinionSummary.negative || 0),
            weightedScore: formatNumber(Number(opinionSummary.weightedScore || 0), {
              maximumFractionDigits: 2,
              minimumFractionDigits: 2,
            }),
          }}
        />
        : <LocalizedText source={"No canonical opinions recorded"} />,
      value: this.getOpinionValue(opinionSummary, formatNumber),
    });

    // Upload speed (always show, grayed if no data)
    if (info?.uploadSpeed === undefined) {
      stats.push({
        color: 'grey',
        icon: 'arrow up',
        key: 'speed',
        tooltip: <LocalizedText source={"Speed unavailable"} />,
        value: '?',
      });
    } else {
      const speedKbps = Math.round(info.uploadSpeed / 1_024);
      stats.push({
        color: speedKbps > 1_000 ? 'green' : speedKbps > 500 ? 'blue' : 'grey',
        icon: 'arrow up',
        key: 'speed',
        tooltip: <LocalizedText source={"Upload Speed: {speed} KB/s"} values={{ speed: formatNumber(speedKbps) }} />,
        value: formatNumber(speedKbps),
      });
    }

    // Queue length (always show, grayed if no data)
    if (info?.queueLength === undefined) {
      stats.push({
        color: 'grey',
        icon: 'list',
        key: 'queue',
        tooltip: <LocalizedText source={"Queue unavailable"} />,
        value: '?',
      });
    } else {
      stats.push({
        color:
          info.queueLength === 0
            ? 'green'
            : info.queueLength < 5
              ? 'blue'
              : 'orange',
        icon: 'list',
        key: 'queue',
        tooltip: <LocalizedText source={"Queue Length: {length}"} values={{ length: formatNumber(info.queueLength) }} />,
        value: formatNumber(info.queueLength),
      });
    }

    // Free slot (always show, grayed if no data)
    if (info?.hasFreeUploadSlot === undefined) {
      stats.push({
        color: 'grey',
        icon: 'unlock',
        key: 'slot',
        tooltip: <LocalizedText source={"Slot status unavailable"} />,
        value: '?',
      });
    } else {
      stats.push({
        color: info.hasFreeUploadSlot ? 'green' : 'red',
        icon: 'unlock',
        key: 'slot',
        tooltip: info.hasFreeUploadSlot
          ? <LocalizedText source={"Free upload slot available"} />
          : <LocalizedText source={"No free slots"} />,
        value: info.hasFreeUploadSlot ? '✓' : '✗',
      });
    }

    // Render the card
    const cardContent = (
      <span
        className={`user-card ${inline ? 'user-card-inline' : ''}`}
        onFocus={this.requestSupplementalData}
        onMouseEnter={this.requestSupplementalData}
      >
        <span className="user-card-username">{children || username}</span>
        {loading && !info ? (
          <span className="user-card-loading">
            <Icon
              loading
              name="spinner"
              size="small"
            />
          </span>
        ) : (
          <span className="user-card-stats">
            {stats.map((stat) => (
              <Popup
                content={stat.tooltip}
                key={stat.key}
                position="top center"
                size="tiny"
                trigger={
                  <span
                    className={`user-card-stat user-card-stat-${stat.color}${stat.glow ? ' user-card-stat-glow' : ''}`}
                  >
                    <Icon
                      fitted
                      name={stat.icon}
                      size="small"
                    />
                    <span className="user-card-stat-value">{stat.value}</span>
                  </span>
                }
              />
            ))}
            <Popup
              content={this.renderInterestPopup()}
              on="click"
              onOpen={this.fetchInterests}
              position="top center"
              trigger={
                <span className="user-card-stat user-card-stat-red user-card-stat-clickable">
                  <Icon
                    fitted
                    name="heart outline"
                    size="small"
                  />
                  <span className="user-card-stat-value"><LocalizedText source={"i"} /></span>
                </span>
              }
            />
          </span>
        )}
      </span>
    );

    return cardContent;
  }
}

const LocalizedUserCard = (props) => {
  const regionalLocale = useRegionalLocale();
  return <UserCard {...props} regionalLocale={regionalLocale} />;
};

export default LocalizedUserCard;
