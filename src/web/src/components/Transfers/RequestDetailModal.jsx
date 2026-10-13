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
      toast.error(`Failed to load request: ${error.message}`);
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
      toast.success('Renamed');
    } catch (error) {
      toast.error(`Rename failed: ${error.message}`);
    } finally {
      setRenaming(false);
    }
  };

  const handleCancel = async () => {
    if (!requestId) return;
    try {
      await downloadRequests.cancel(requestId);
      toast.success('Request cancelled');
      await load();
    } catch (error) {
      toast.error(`Cancel failed: ${error.message}`);
    }
  };

  const request = detail?.request;
  const attempts = detail?.attempts ?? [];

  return (
    <Modal onClose={onClose} open={open} size="small">
      <Modal.Header>
        <Icon name="folder open" />
        Download request
      </Modal.Header>
      <Modal.Content scrolling>
        {loading && <Icon loading name="spinner" />}
        {!loading && !request && <p>Request not found.</p>}
        {!loading && request && (
          <>
            <Header as="h5" style={{ marginBottom: '0.25em' }}>Name</Header>
            <div style={{ display: 'flex', gap: '0.5em', marginBottom: '1em' }}>
              <Input
                fluid
                onChange={(_, { value }) => setNameDraft(value)}
                placeholder="Display label"
                value={nameDraft}
              />
              <TooltipButton
                disabled={!nameDraft.trim() || nameDraft.trim() === request.name}
                loading={renaming}
                onClick={handleRename}
                primary
                size="small"
                tooltip="Save the changed display label for this request."
              >
                Save
              </TooltipButton>
            </div>

            <Header as="h5" style={{ marginBottom: '0.25em' }}>Status</Header>
            <div style={{ marginBottom: '1em' }}>
              <Label color={request.state === 'Completed' ? 'green' : request.state === 'Cancelled' ? 'grey' : request.state === 'Failed' ? 'red' : 'blue'}>
                {formatState(request.state)}
              </Label>
              <span style={{ marginLeft: '0.5em', fontSize: '0.85em', opacity: 0.8 }}>
                Created {formatTime(request.createdAt)}
                {request.completedAt && ` • Completed ${formatTime(request.completedAt)}`}
              </span>
            </div>

            <Header as="h5" style={{ marginBottom: '0.25em' }}>
              Attempts <Label circular>{attempts.length}</Label>
            </Header>
            {attempts.length === 0 ? (
              <p style={{ color: '#999', fontStyle: 'italic' }}>No attempts recorded.</p>
            ) : (
              <Table basic="very" compact size="small">
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell>When</Table.HeaderCell>
                    <Table.HeaderCell>Source</Table.HeaderCell>
                    <Table.HeaderCell>State</Table.HeaderCell>
                    <Table.HeaderCell>Filename</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {attempts.map((attempt) => (
                    <Table.Row key={attempt.id}>
                      <Table.Cell>{formatTime(attempt.requestedAt)}</Table.Cell>
                      <Table.Cell>{attempt.username}</Table.Cell>
                      <Table.Cell>
                        {attempt.removed ? <Label color="grey" size="mini">removed</Label> : <span>{formatState(attempt.state)}</span>}
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
            Cancel request
          </TooltipButton>
        )}
        <TooltipButton
          onClick={onClose}
          tooltip="Close these request details and return to transfers."
        >
          Close
        </TooltipButton>
      </Modal.Actions>
    </Modal>
  );
};

export default RequestDetailModal;
