import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../../lib/interfaceLocale";
import * as sharesLibrary from '../../../lib/shares';
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import { LoaderSegment, ShrinkableButton, Switch } from '../../Shared';
import ContentsModal from './ContentsModal';
import ExclusionTable from './ExclusionTable';
import ShareTable from './ShareTable';
import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import { Divider } from 'semantic-ui-react';

const asArray = (value) => (Array.isArray(value) ? value : []);
const asObject = (value) => (
  value && typeof value === 'object' && !Array.isArray(value) ? value : {}
);

const ScanButton = ({ rescan, scanPending, working }) => (
  <ShrinkableButton
    color={scanPending ? 'yellow' : undefined}
    disabled={working}
    icon="refresh"
    loading={working}
    mediaQuery="(max-width: 516px)"
    onClick={() => rescan()}
    primary={!scanPending}
    tooltip={interfaceText("Recount files in configured shares after changing files or exclusions.")}
  >
    <LocalizedText source={"Rescan Shares"} /></ShrinkableButton>
);

const CancelButton = ({ cancel, working }) => (
  <ShrinkableButton
    color="red"
    disabled={working}
    icon="x"
    mediaQuery="(max-width: 516px)"
    onClick={() => cancel()}
    tooltip={interfaceText("Stop the active share scan; counts may stay incomplete until the next scan.")}
  >
    <LocalizedText source={"Cancel Scan"} /></ShrinkableButton>
);

const Shares = ({ state = {}, theme } = {}) => {
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [shares, setShares] = useState([]);
  const [modal, setModal] = useState(false);
  const refreshTimeoutRef = useRef(null);

  const { directories, files, scanPending, scanProgress, scanning } = state;

  const clearRefreshTimeout = () => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
  };

  const getAll = async (quiet = false) => {
    try {
      if (!quiet) setLoading(true);

      const sharesByHost = await sharesLibrary.getAll();
      const flattened = Object.entries(asObject(sharesByHost)).reduce(
        (accumulator, [host, sharesForHost]) => {
          return accumulator.concat(
            asArray(sharesForHost).map((share) => ({ host, ...share })),
          );
        },
        [],
      );

      setShares(flattened);
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getAll();

    return clearRefreshTimeout;
  }, []);

  useEffect(() => {
    clearRefreshTimeout();
    getAll(true);

    if (!scanning) {
      // the state change out of scanning can fire before
      // shares are updated, which leaves them stale. wait a second
      // and fetch again.
      refreshTimeoutRef.current = setTimeout(() => {
        refreshTimeoutRef.current = null;
        getAll(true);
      }, 1_000);
    }
  }, [scanPending, scanning]);

  const rescan = async () => {
    try {
      setWorking(true);
      await sharesLibrary.rescan();
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }));
    } finally {
      setWorking(false);
    }
  };

  const cancel = async () => {
    try {
      setWorking(true);
      await sharesLibrary.cancel();
    } catch (error) {
      console.error(error);
      toast.error(getApiErrorMessage(error, { t: interfaceText }, 'Failed to cancel the scan'));
    } finally {
      setWorking(false);
    }
  };

  const shared = shares.filter((share) => !share.isExcluded);
  const excluded = shares.filter((share) => share.isExcluded);

  return (
    <Switch loading={loading && <LoaderSegment />}>
      <div className="header-buttons">
        <Switch
          scanning={
            scanning && (
              <CancelButton
                cancel={cancel}
                working={working}
              />
            )
          }
        >
          <ScanButton
            rescan={rescan}
            scanPending={scanPending}
            working={working}
          />
        </Switch>
      </div>
      <Divider />
      <Switch
        filling={
          scanning && (
            <LoaderSegment>
              <div>
                <div>{Math.round(scanProgress * 100)}%</div>
                <div className="share-scan-detail">
                  <LocalizedText
                    source="Found {files} files in {directories} directories"
                    values={{ files, directories }}
                  /></div>
              </div>
            </LoaderSegment>
          )
        }
      >
        <ShareTable
          onClick={setModal}
          shares={shared}
        />
        <ExclusionTable exclusions={excluded} />
      </Switch>
      <ContentsModal
        onClose={() => setModal(false)}
        share={modal}
        theme={theme}
      />
    </Switch>
  );
};

export default Shares;
