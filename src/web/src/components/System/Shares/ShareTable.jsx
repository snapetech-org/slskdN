import LocalizedText from "../../Shared/LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../../lib/interfaceLocale";
import { Switch } from '../../Shared';
import React from 'react';
import { Button, Icon, Popup, Table } from 'semantic-ui-react';

const ShareTable = ({ onClick, shares }) => {
  useInterfaceLanguage();
  return (
    <div
      aria-label={interfaceText("Configured shares")}
      className="system-shares-table-scroll"
      role="region"
      tabIndex={0}
     {...interfaceTextProps("Configured shares")}>
      <Table>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell><LocalizedText source={"Host"} /></Table.HeaderCell>
            <Table.HeaderCell><LocalizedText source={"Local Path"} /></Table.HeaderCell>
            <Table.HeaderCell className="share-count-column">
              <LocalizedText source={"Directories"} /></Table.HeaderCell>
            <Table.HeaderCell className="share-count-column">
              <LocalizedText source={"Files"} /></Table.HeaderCell>
            <Table.HeaderCell><LocalizedText source={"Alias"} /></Table.HeaderCell>
            <Table.HeaderCell><LocalizedText source={"Remote Path"} /></Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          <Switch
            empty={
              shares.length === 0 && (
                <Table.Row>
                  <Table.Cell
                    colSpan={6}
                    style={{
                      opacity: 0.5,
                      padding: '10px !important',
                      textAlign: 'center',
                    }}
                  >
                    <LocalizedText source={"No shares configured"} /></Table.Cell>
                </Table.Row>
              )
            }
          >
            {shares.map((share) => {
              const label = `View files in share ${share.localPath}`;
              const description = `Open the file list for share ${share.localPath}.`;

              return (
                <Table.Row key={`${share.host}+${share.localPath}`}>
                  <Table.Cell>{share.host}</Table.Cell>
                  <Table.Cell>
                    <Popup
                      content={description}
                      position="top left"
                      trigger={(
                        <Button
                          aria-label={label}
                          basic
                          className="share-path-button"
                          onClick={() => onClick(share)}
                          title={description}
                        >
                          <Icon name="folder" />
                          {share.localPath}
                        </Button>
                      )}
                    />
                  </Table.Cell>
                  <Table.Cell>{share.directories ?? '?'}</Table.Cell>
                  <Table.Cell>{share.files ?? '?'}</Table.Cell>
                  <Table.Cell>{share.alias}</Table.Cell>
                  <Table.Cell>{share.remotePath}</Table.Cell>
                </Table.Row>
              );
            })}
          </Switch>
        </Table.Body>
      </Table>
    </div>
  );
};

export default ShareTable;
