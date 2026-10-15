import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { TooltipButton } from '../Shared';
import { Form, Message, Segment } from 'semantic-ui-react';
import api from '../../lib/api';

export default function SolidSettings() {
  const [status, setStatus] = useState(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState('');
  const [webId, setWebId] = useState('');
  const [resolved, setResolved] = useState(null);
  const [resolveError, setResolveError] = useState('');
  const [resolving, setResolving] = useState(false);
  const statusRequestId = useRef(0);

  const formatError = (error) =>
    getApiErrorMessage(error, { t: interfaceText });

  const loadStatus = useCallback(async () => {
    const requestId = ++statusRequestId.current;
    setStatusLoading(true);
    setStatusError('');
    try {
      const res = await api.get('/solid/status');
      if (requestId === statusRequestId.current) setStatus(res.data);
    } catch (e) {
      if (requestId !== statusRequestId.current) return;
      if (e?.response?.status === 404) {
        setStatus({ enabled: false });
      } else {
        setStatusError(formatError(e));
      }
    } finally {
      if (requestId === statusRequestId.current) setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    return () => {
      statusRequestId.current += 1;
    };
  }, [loadStatus]);

  const resolveWebId = async () => {
    setResolveError('');
    setResolved(null);
    setResolving(true);
    try {
      const res = await api.post('/solid/resolve-webid', { webId });
      setResolved(res.data);
    } catch (e) {
      setResolveError(formatError(e));
    } finally {
      setResolving(false);
    }
  };

  return (
    <Segment data-testid="solid-root">
      <h2><LocalizedText source={"Solid"} /></h2>

      {statusLoading && (
        <Message info role="status"><LocalizedText source={"Checking Solid integration…"} /></Message>
      )}

      {statusError && (
        <Message negative role="alert">
          <Message.Content>{statusError}</Message.Content>
          <TooltipButton
            onClick={loadStatus}
            tooltip="Retry checking whether the Solid integration is enabled."
          >
            <LocalizedText source={"Retry Status"} /></TooltipButton>
        </Message>
      )}

      {status && !status.enabled && (
        <Message warning>
          <LocalizedText source={"Solid integration is disabled (Feature.Solid=false)."} /></Message>
      )}

      {status && status.enabled && (
        <Message info>
          <LocalizedText source={"Client ID:"} />{' '}
          {status.clientId ? (
            <code>{status.clientId}</code>
          ) : (
            <span><LocalizedText source={"Not configured; endpoint disabled."} /></span>
          )}
          <br />
          <LocalizedText source={"Redirect path:"} />{" "}<code>{status.redirectPath}</code>
        </Message>
      )}

      {resolveError && <Message negative role="alert">{resolveError}</Message>}

      <Form>
        <Form.Field>
          <label htmlFor="solid-webid"><LocalizedText source={"WebID"} /></label>
          <Form.Input
            id="solid-webid"
            placeholder="https://example.com/profile/card#me"
            value={webId}
            onChange={(e) => {
              setWebId(e.target.value);
              setResolveError('');
            }}
            data-testid="solid-webid-input"
          />
        </Form.Field>
        <TooltipButton
          primary
          type="button"
          onClick={resolveWebId}
          data-testid="solid-resolve-webid"
          disabled={statusLoading || status?.enabled !== true || !webId.trim() || resolving}
          loading={resolving}
          tooltip="Resolve this WebID and show the Solid identity document returned by the server."
        >
          <LocalizedText source={"Resolve WebID"} /></TooltipButton>
      </Form>

      {resolved && (
        <Segment>
          <pre style={{ whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(resolved, null, 2)}
          </pre>
        </Segment>
      )}
    </Segment>
  );
}
