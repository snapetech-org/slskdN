import LocalizedText from "../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../lib/apiErrorMessages';
import { getRegionalLocale } from '../../lib/regionalFormat';
import React, { useCallback, useEffect, useState } from 'react';
import { Header, Icon, Input, Label, Modal, Table } from 'semantic-ui-react';
import { toast } from 'react-toastify';
import * as downloadRequests from '../../lib/downloadRequests';
import TooltipButton from '../Shared/TooltipButton';

const formatTime = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString(getRegionalLocale());
};

const formatState = (state) => state ?? '—';

const RequestDetailModal = ({ open, requestId, onClose }) => {
  useInterfaceLanguage();
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState(null);
  const [nameDraft, setNameDraft] = useState('');
  const [renaming, setRenaming] = useState(false);

  const load = useCallback(async () => {
    if (!requestId) return;
    setLoading(true);
    try {
      const data = await downloadRequests.get(requestId);
      setDetail(data);
      setNameDraft(data?.request?.name ?? '');
    } catch (error) {
      toast.error(interfaceText("Failed to load request: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    if (open && requestId) {
      load();
    } else {
      setDetail(null);
      setNameDraft('');
    }
  }, [open, requestId, load]);

  const handleRename = async () => {
    if (!requestId || !nameDraft.trim()) return;
    if (nameDraft.trim() === detail?.request?.name) return;

    setRenaming(true);
    try {
      const updated = await downloadRequests.rename(requestId, nameDraft.trim());
      setDetail((prev) => (prev ? { ...prev, request: updated } : prev));
      toast.success(interfaceText("Renamed"));
    } catch (error) {
      toast.error(interfaceText("Rename failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    } finally {
      setRenaming(false);
    }
  };

  const handleCancel = async () => {
    if (!requestId) return;
    try {
      await downloadRequests.cancel(requestId);
      toast.success(interfaceText("Request cancelled"));
      await load();
    } catch (error) {
      toast.error(interfaceText("Cancel failed: {message}", { "message": getApiErrorMessage(error, { t: interfaceText }) }));
    }
  };

  const request = detail?.request;
  const attempts = detail?.attempts ?? [];

  return (
    <Modal onClose={onClose} open={open} size="small">
      <Modal.Header>
        <Icon name="folder open" />
        <LocalizedText source={"Download request"} /></Modal.Header>
      <Modal.Content scrolling>
        {loading && <Icon loading name="spinner" />}
        {!loading && !request && <p><LocalizedText source={"Request not found."} /></p>}
        {!loading && request && (
          <>
            <Header as="h5" style={{ marginBottom: '0.25em' }}><LocalizedText source={"Name"} /></Header>
            <div style={{ display: 'flex', gap: '0.5em', marginBottom: '1em' }}>
              <Input
                fluid
                onChange={(_, { value }) => setNameDraft(value)}
                placeholder={interfaceText("Display label")}
                value={nameDraft}
               {...interfaceTextProps("Display label")}/>
              <TooltipButton
                disabled={!nameDraft.trim() || nameDraft.trim() === request.name}
                loading={renaming}
                onClick={handleRename}
                primary
                size="small"
                tooltip="Save the changed display label for this request."
              >
                <LocalizedText source={"Save"} /></TooltipButton>
            </div>

            <Header as="h5" style={{ marginBottom: '0.25em' }}><LocalizedText source={"Status"} /></Header>
            <div style={{ marginBottom: '1em' }}>
              <Label color={request.state === 'Completed' ? 'green' : request.state === 'Cancelled' ? 'grey' : request.state === 'Failed' ? 'red' : 'blue'}>
                <LocalizedText source={formatState(request.state)} />
              </Label>
              <span style={{ marginLeft: '0.5em', fontSize: '0.85em', opacity: 0.8 }}>
                <LocalizedText source={"Created"} />{" "}{formatTime(request.createdAt)}
                {request.completedAt && ` • Completed ${formatTime(request.completedAt)}`}
              </span>
            </div>

            <Header as="h5" style={{ marginBottom: '0.25em' }}>
              <LocalizedText source={"Attempts"} />{" "}<Label circular>{attempts.length}</Label>
            </Header>
            {attempts.length === 0 ? (
              <p style={{ color: '#999', fontStyle: 'italic' }}><LocalizedText source={"No attempts recorded."} /></p>
            ) : (
              <Table basic="very" compact size="small">
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell><LocalizedText source={"When"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Source"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"State"} /></Table.HeaderCell>
                    <Table.HeaderCell><LocalizedText source={"Filename"} /></Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {attempts.map((attempt) => (
                    <Table.Row key={attempt.id}>
                      <Table.Cell>{formatTime(attempt.requestedAt)}</Table.Cell>
                      <Table.Cell>{attempt.username}</Table.Cell>
                      <Table.Cell>
                        {attempt.removed ? <Label color="grey" size="mini"><LocalizedText source={"removed"} /></Label> : <span><LocalizedText source={formatState(attempt.state)} /></span>}
                      </Table.Cell>
                      <Table.Cell className="truncate-cell" title={attempt.filename}>
                        {attempt.filename}
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            )}
          </>
        )}
      </Modal.Content>
      <Modal.Actions>
        {request && request.state !== 'Completed' && request.state !== 'Cancelled' && (
          <TooltipButton
            color="red"
            onClick={handleCancel}
            tooltip="Cancel the current attempt and mark this request cancelled."
          >
            <LocalizedText source={"Cancel request"} /></TooltipButton>
        )}
        <TooltipButton
          onClick={onClose}
          tooltip="Close these request details and return to transfers."
        >
          <LocalizedText source={"Close"} /></TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

export default RequestDetailModal;
