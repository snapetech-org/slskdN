import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const nodeModulesDirectory = fs.realpathSync(path.resolve(__dirname, 'node_modules'));
const repositoryRoot = fs.realpathSync(path.resolve(__dirname, '../..'));

const isWithinDirectory = (directory, candidate) => {
  const relative = path.relative(directory, candidate);
  return (
    relative === '' ||
    (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`))
  );
};

// Custom Less plugin to handle semantic-ui-less webpack-style aliases.
// @semantic-ui-react/craco-less previously provided these via webpack Less loader.
// Handles:
//   - '../../theme.config' (imported by node_modules/semantic-ui-less/semantic.less)
//     → src/semantic-ui/theme.config
//   - '~foo/bar' (webpack-style node_modules imports in Less files)
//     → node_modules/foo/bar
class SemanticUILessFileManager {
  install(less, pluginManager) {
    const themeConfigPath = path.resolve(__dirname, 'src/semantic-ui/theme.config');

    class AliasFileManager extends less.FileManager {
      supports(filename) {
        return filename === '../../theme.config' || filename.startsWith('~');
      }

      loadFile(filename, _currentDirectory, options, environment) {
        if (filename === '../../theme.config') {
          const contents = fs.readFileSync(themeConfigPath, 'utf-8');
          return Promise.resolve({ filename: themeConfigPath, contents });
        }
        if (filename.startsWith('~')) {
          // nosemgrep: javascript.lang.security.audit.path-traversal.path-join-resolve-traversal.path-join-resolve-traversal -- the normalized alias is checked lexically and after realpath before it is read.
          const resolved = path.resolve(nodeModulesDirectory, filename.slice(1));
          if (!isWithinDirectory(nodeModulesDirectory, resolved)) {
            return Promise.reject(new Error('Less package imports must stay inside node_modules.'));
          }
          const canonicalResolved = fs.realpathSync(resolved);
          if (!isWithinDirectory(repositoryRoot, canonicalResolved)) {
            return Promise.reject(new Error('Less package imports must stay inside the repository.'));
          }
          const contents = fs.readFileSync(canonicalResolved, 'utf-8');
          return Promise.resolve({ filename: canonicalResolved, contents });
        }
        return super.loadFile(filename, _currentDirectory, options, environment);
      }
    }

    pluginManager.addFileManager(new AliasFileManager());
  }

  get minVersion() {
    return [2, 7, 0];
  }
}

export default defineConfig({
  base: '/',
  plugins: [react()],

  css: {
    preprocessorOptions: {
      less: {
        math: 'always',
        relativeUrls: true,
        javascriptEnabled: true,
        paths: [path.resolve(__dirname, 'node_modules')],
        plugins: [new SemanticUILessFileManager()],
      },
    },
  },

  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:5099',
        changeOrigin: true,
      },
      '/hub': {
        target: 'http://localhost:5099',
        ws: true,
        changeOrigin: true,
      },
    },
  },

  build: {
    outDir: 'build',
    emptyOutDir: true,
    // check-bundle-size.mjs enforces 600 KiB for normal assets and explicitly
    // allows the larger MilkDrop preset pack because it loads on activation.
    // Keep Vite's advisory threshold above that documented lazy-only exception.
    chunkSizeWarningLimit: 700,
    // Vite 8 defaults to lightningcss for CSS minification, which rejects some
    // valid-but-unusual CSS emitted by semantic-ui-less (e.g. 0.0px dimensions).
    // Use esbuild CSS minifier instead, which is tolerant of this output.
    cssMinify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;

          if (id.includes('butterchurn-presets')) return 'milkdrop-presets';
          if (id.includes('butterchurn')) return 'milkdrop';
          // React 19 aliases semantic-ui-react to react-fomantic-ui (ADR-0026).
          if (id.includes('semantic-ui') || id.includes('react-fomantic-ui')) {
            return 'semantic-ui';
          }
          if (
            id.includes('/react/') ||
            id.includes('/react-dom/') ||
            id.includes('/react-router') ||
            id.includes('/scheduler/')
          ) {
            return 'react-vendor';
          }
          if (id.includes('@microsoft/signalr')) return 'signalr';
          if (id.includes('axios')) return 'api-vendor';

          return 'vendor';
        },
      },
    },
  },

  define: {
    // Shim for any remaining process.env.NODE_ENV references
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
  },

  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
    exclude: ['e2e/**', 'node_modules/**'],
    // Lazy-loaded route modules and large jsdom components can exceed five
    // seconds on the shared self-hosted CI runners while remaining healthy.
    testTimeout: 15_000,
  },
});
