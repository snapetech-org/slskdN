import LocalizedText from "./LocalizedText";
import { interfaceText, interfaceTextProps, useInterfaceLanguage } from "../../lib/interfaceLocale";
// <copyright file="DownloadDestinationSelector.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import './DownloadDestinationSelector.css';
import * as destinations from '../../lib/destinations';
import {
  getLocalStorageItem,
  setLocalStorageItem,
} from '../../lib/storage';
import React, { useEffect, useState } from 'react';
import { Dropdown, Icon, Popup } from 'semantic-ui-react';

export const DOWNLOAD_DESTINATION_STORAGE_KEY =
  'slskd-download-destination';

export const chooseDownloadDestination = (configured, storedPath) => {
  const available = Array.isArray(configured) ? configured : [];
  const stored = available.find(({ path }) => path === storedPath);

  return stored?.path
    ?? available.find(({ isDefault }) => isDefault)?.path
    ?? available[0]?.path;
};

const DownloadDestinationSelector = ({ onChange }) => {
  useInterfaceLanguage();
  const [configured, setConfigured] = useState([]);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState(undefined);

  useEffect(() => {
    let active = true;

    destinations.getAll()
      .then((result) => {
        if (!active) return;

        const available = Array.isArray(result) ? result : [];
        const next = chooseDownloadDestination(
          available,
          getLocalStorageItem(DOWNLOAD_DESTINATION_STORAGE_KEY),
        );
        setConfigured(available);
        setSelected(next);
        setError(false);
        onChange(next);
      })
      .catch(() => {
        if (!active) return;

        setError(true);
        onChange(undefined);
      });

    return () => {
      active = false;
    };
  }, [onChange]);

  const handleChange = (_event, { value }) => {
    setSelected(value);
    setLocalStorageItem(DOWNLOAD_DESTINATION_STORAGE_KEY, value);
    onChange(value);
  };

  const options = configured.map((destination) => ({
    key: destination.path,
    text: `${destination.name}${destination.isDefault ? ' (default)' : ''}`,
    value: destination.path,
    description: destination.path,
  }));

  return (
    <div
      className="download-destination-selector"
      data-testid="download-destination-selector"
    >
      <span>
        <Icon name="folder open" />
        <LocalizedText source={"Download to"} /></span>
      <Popup
        content={interfaceText("Choose where new downloads from this browser are saved. The configured default is used until you select another destination.")}
        position="top center"
        trigger={
          <Dropdown
            aria-label={interfaceText("Download destination")}
            disabled={error || options.length === 0}
            error={error}
            loading={!error && options.length === 0}
            onChange={handleChange}
            options={options}
            placeholder={interfaceText(error ? 'Configured default' : 'Loading destinations')}
            selection
            value={selected}
           {...interfaceTextProps("Download destination")}/>
        }
       {...interfaceTextProps("Choose where new downloads from this browser are saved. The configured default is used until you select another destination.")}/>
    </div>
  );
};

export default DownloadDestinationSelector;
