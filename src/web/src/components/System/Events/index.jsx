import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { getApiErrorMessage } from '../../../lib/apiErrorMessages';
import '../System.css';
import { list } from '../../../lib/events';
import React, { useEffect, useState } from 'react';
import { Button, Header, Icon, Message, Pagination, Popup, Table } from 'semantic-ui-react';

const PER_PAGE = 10;

const replaceHyphensWithNonBreakingEquivalent = (string) =>
  string?.replaceAll('-', '‑');

const formatEventData = (data) => {
  try {
    return JSON.stringify(JSON.parse(data), null, 2);
  } catch {
    return `${data || ''}`;
  }
};

const Events = () => {
  useInterfaceLanguage();
  const [page, setPage] = useState(1);
  const [retrySequence, setRetrySequence] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    let active = true;

    const loadEvents = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await list({
          limit: PER_PAGE,
          offset: (page - 1) * PER_PAGE,
        });
        if (!active) return;

        const items = Array.isArray(response?.events) ? response.events : [];
        const totalCount = Number(response?.totalCount);
        const nextTotalPages = Number.isFinite(totalCount)
          ? Math.ceil(totalCount / PER_PAGE)
          : 0;

        setEvents(items);
        setTotalPages(nextTotalPages);
        if (nextTotalPages > 0 && page > nextTotalPages) {
          setPage(nextTotalPages);
        }
      } catch (error_) {
        if (!active) return;
        setEvents([]);
        setError(getApiErrorMessage(error_, { t: interfaceText }));
      } finally {
        if (active) setLoading(false);
      }
    };

    loadEvents();
    return () => {
      active = false;
    };
  }, [page, retrySequence]);

  const changePage = (_event, { activePage }) => {
    const nextPage = Number(activePage);
    if (Number.isInteger(nextPage) && nextPage >= 1) {
      setPage(nextPage);
    }
  };

  if (error) {
    return (
      <div className="events-error">
        <Message
          error
          header={interfaceText("Failed to load events")}
          content={error}
         {...interfaceTextProps("Failed to load events")}/>
        <Popup
          content={interfaceText("Try loading this page of system events again after the current request error.")}
          position="top center"
          trigger={(
            <Button
              onClick={() => setRetrySequence((previous) => previous + 1)}
              primary
            >
              <Icon name="refresh" />
              <LocalizedText source={"Try Again"} /></Button>
          )}
         {...interfaceTextProps("Try loading this page of system events again after the current request error.")}/>
      </div>
    );
  }

  return (
    <div className="events-page">
      <Header as="h2">
        <Icon name="history" />
        <LocalizedText source={"System Events"} /><Header.Subheader>
          <LocalizedText source={"Review recorded events and their diagnostic details."} /></Header.Subheader>
      </Header>

      <div className="events-controls">
        {totalPages > 1 && (
          <Popup
            content={interfaceText("Choose a page to review another batch of system events.")}
            on={['hover', 'focus']}
            position="top center"
            trigger={(
              <Pagination
                activePage={page}
                aria-label={interfaceText("Event pages")}
                boundaryRange={1}
                className="events-pagination"
                firstItem={{ 'aria-label': interfaceText("First events page"), content: '«' }}
                lastItem={{ 'aria-label': interfaceText("Last events page"), content: '»' }}
                nextItem={{ 'aria-label': interfaceText("Next events page"), content: '›' }}
                onPageChange={changePage}
                prevItem={{ 'aria-label': interfaceText("Previous events page"), content: '‹' }}
                siblingRange={1}
                totalPages={totalPages}
               {...interfaceTextProps("Event pages")}/>
            )}
           {...interfaceTextProps("Choose a page to review another batch of system events.")}/>
        )}
        {totalPages > 0 && (
          <span
            aria-live="polite"
            className="events-page-status"
          >
            <LocalizedText source={"Page"} />{" "}{page} <LocalizedText source={"of"} />{" "}{totalPages}
          </span>
        )}
      </div>

      <div
        aria-label={interfaceText("System event records")}
        className="events-table-scroll"
        role="region"
        tabIndex={0}
       {...interfaceTextProps("System event records")}>
        <Table
          aria-label={interfaceText("System events")}
          className="events-table"
          compact="very"
          unstackable
         {...interfaceTextProps("System events")}>
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell className="events-list-id"><LocalizedText source={"Id"} /></Table.HeaderCell>
              <Table.HeaderCell className="events-list-timestamp">
                <LocalizedText source={"Timestamp"} /></Table.HeaderCell>
              <Table.HeaderCell className="events-list-type">
                <LocalizedText source={"Type"} /></Table.HeaderCell>
              <Table.HeaderCell><LocalizedText source={"Data"} /></Table.HeaderCell>
            </Table.Row>
          </Table.Header>
          <Table.Body className="events-table-body">
            {events.length === 0 ? (
              <Table.Row>
                <Table.Cell colSpan={4}>
                  {loading ? <LocalizedText source={"Loading events"} /> : <LocalizedText source={"No events"} />}
                </Table.Cell>
              </Table.Row>
            ) : (
              events.map((event) => (
                <Table.Row key={event.id}>
                  <Table.Cell className="events-list-id">
                    <Popup
                      content={interfaceText("Use this ID to find the {type} event in diagnostics: {id}", { "type": (event.type), "id": (event.id) })}
                      on={['hover', 'focus']}
                      position="top left"
                      trigger={(
                        <Button
                          aria-label={interfaceText("Show identifier for event {id}", { "id": (event.id) })}
                          basic
                          icon="info circle"
                          size="small"
                         {...interfaceTextProps("Show identifier for event {id}")}/>
                      )}
                      wide="very"
                     {...interfaceTextProps("Use this ID to find the {type} event in diagnostics: {id}")}/>
                  </Table.Cell>
                  <Table.Cell className="events-list-timestamp">
                    {replaceHyphensWithNonBreakingEquivalent(event.timestamp)}
                  </Table.Cell>
                  <Table.Cell className="events-list-type">{event.type}</Table.Cell>
                  <Table.Cell className="events-table-data">
                    <pre>{formatEventData(event.data)}</pre>
                  </Table.Cell>
                </Table.Row>
              ))
            )}
          </Table.Body>
        </Table>
      </div>
    </div>
  );
};

export default Events;
