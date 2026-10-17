import './Files.css';
import Explorer from './Explorer';
import LocalizedText from '../../Shared/LocalizedText';
import React, { useState } from 'react';
import { Tab } from 'semantic-ui-react';

const Files = ({ options } = {}) => {
  const { remoteFileManagement } = options;
  const [activeIndex, setActiveIndex] = useState(0);

  const panes = [
    {
      menuItem: { key: 'downloads', content: <LocalizedText source="Downloads" /> },
      pane: (
        <Tab.Pane key="downloads">
          <Explorer
            active={activeIndex === 0}
            remoteFileManagement={remoteFileManagement}
            root="downloads"
          />
        </Tab.Pane>
      ),
      route: 'downloads',
    },
    {
      menuItem: { key: 'incomplete', content: <LocalizedText source="Incomplete" /> },
      pane: (
        <Tab.Pane key="incomplete">
          <Explorer
            active={activeIndex === 1}
            remoteFileManagement={remoteFileManagement}
            root="incomplete"
          />
        </Tab.Pane>
      ),
      route: 'incomplete',
    },
  ];

  return (
    <div>
      <Tab
        activeIndex={activeIndex}
        onTabChange={(_event, { activeIndex: nextIndex }) =>
          setActiveIndex(nextIndex)
        }
        panes={panes}
        renderActiveOnly={false}
      />
    </div>
  );
};

export default Files;
