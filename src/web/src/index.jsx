import 'semantic-ui-less/semantic.less';
import App from './components/App';
import { urlBase } from './config';
import { cleanUpServiceWorker } from './registerServiceWorker';
import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { createRoot } from 'react-dom/client';
import { applyInitialInterfaceLanguage } from './lib/interfaceLocale';

// Expose router history/location for E2E diagnostics
// BrowserRouter uses browser history, so we expose window.location
if (typeof window !== 'undefined') {
  window.__APP_LOCATION__ = window.location;
}

// Set basename only if urlBase is non-empty and not '/'
// When urlBase is empty or '/', don't set basename (undefined)
const basename = urlBase && urlBase !== '/' ? urlBase : undefined;

applyInitialInterfaceLanguage();

createRoot(document.querySelector('#root')).render(
  <Router basename={basename}>
    <App />
  </Router>,
);

cleanUpServiceWorker();
