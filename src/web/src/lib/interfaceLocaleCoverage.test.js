import * as ts from 'typescript';
import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const sourceRoot = path.join(webRoot, 'src');
const localeRoot = path.join(webRoot, 'public', 'locales');
const localeIds = [
  'es', 'zh-Hans', 'hi', 'de', 'ja', 'fr', 'pt-BR', 'ar', 'ko', 'zh-Hant', 'vi', 'id',
];
const placeholderPattern = /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g;
const rawTechnicalJsxText = new Set([
  'feature.Pods', 'EQ', 'JSON', 'CSV', 'localhost:', 'MB', 'ID:', 'PrivateServiceGateway',
  'POD', 'MESH', 'SCENE', 'OCR', 'IP', 'URL', 'Last.fm', 'VPN', 'Mbit/s', 'chunks/s',
  'ed25519:&lt;base64 signature&gt;', 'TTL:', 'KB', 'ops/sec', 'mesh.enableSoulseekRendezvous',
  'dhtRendezvous.lanOnly: true', 'dhtRendezvous.lanOnly: false', '50300/tcp',
  'dht.lan_only=true', 'DHT', 'multi_source', 'hash_db', 'mesh_sync', '/hr',
  's:', 'T:', 'S:', 'M:', '/s',
]);

const placeholders = (value) => [...value.matchAll(placeholderPattern)].map((match) => match[1]).sort();
const staticStrings = (expression, values) => {
  if (!expression) return [];
  if (ts.isStringLiteralLike(expression) || ts.isNoSubstitutionTemplateLiteral(expression)) {
    return [expression.text];
  }
  if (ts.isParenthesizedExpression(expression) || ts.isAsExpression(expression) || ts.isSatisfiesExpression(expression)) {
    return staticStrings(expression.expression, values);
  }
  if (ts.isIdentifier(expression)) return values.get(expression.text) || [];
  if (ts.isConditionalExpression(expression)) {
    return [...staticStrings(expression.whenTrue, values), ...staticStrings(expression.whenFalse, values)];
  }
  if (ts.isBinaryExpression(expression) && [ts.SyntaxKind.BarBarToken, ts.SyntaxKind.QuestionQuestionToken].includes(expression.operatorToken.kind)) {
    return [...staticStrings(expression.left, values), ...staticStrings(expression.right, values)];
  }
  if (ts.isCallExpression(expression) && ts.isIdentifier(expression.expression)) {
    const sourceCount = ['interfaceTextPlural', 'tPlural', 'tp'].includes(expression.expression.text) ? 2 : 1;
    return expression.arguments.slice(0, sourceCount).flatMap((argument) => staticStrings(argument, values));
  }
  return [];
};

const walkSourceFiles = (directory, visit) => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (!['e2e', 'test', '__tests__', 'node_modules'].includes(entry.name)) walkSourceFiles(fullPath, visit);
      continue;
    }
    if (!/\.(?:js|jsx|ts|tsx)$/.test(entry.name) || /\.(?:test|spec)\./.test(entry.name)) continue;
    visit(fullPath);
  }
};

const attributeValue = (attribute) => {
  if (!attribute.initializer) return true;
  if (ts.isStringLiteral(attribute.initializer)) return attribute.initializer.text;
  if (ts.isJsxExpression(attribute.initializer)) return attribute.initializer.expression;
  return undefined;
};
const jsxTagName = (openingElement) => openingElement.tagName.getText();
const isTrueAttribute = (attributes, name) => {
  const attribute = attributes.find((item) => ts.isJsxAttribute(item) && item.name.getText() === name);
  if (!attribute) return false;
  if (!attribute.initializer) return true;
  return ts.isJsxExpression(attribute.initializer) && attribute.initializer.expression?.kind === ts.SyntaxKind.TrueKeyword;
};
const localizedTags = new Set(['LocalizedText', 'LocalizedPopup', 'LocalizedPluralText', 'PlaceholderSegment']);

const collectLocalizationReferences = () => {
  const references = [];
  const rawJsxText = [];
  walkSourceFiles(sourceRoot, (filePath) => {
    const text = fs.readFileSync(filePath, 'utf8');
    const scriptKind = /\.tsx?$/.test(filePath) ? ts.ScriptKind.TSX : ts.ScriptKind.JSX;
    const sourceFile = ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true, scriptKind);
    const relativeFile = path.relative(sourceRoot, filePath);
    const values = new Map();

    const collectValues = (node) => {
      if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
        const found = staticStrings(node.initializer, values);
        if (found.length) values.set(node.name.text, found);
      }
      ts.forEachChild(node, collectValues);
    };
    collectValues(sourceFile);

    const add = (node, value) => {
      if (typeof value !== 'string' || !value.trim()) return;
      references.push({
        source: value,
        file: relativeFile,
        line: sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1,
      });
    };

    const visit = (node, localizedAncestor = false) => {
      if (ts.isCallExpression(node) && ts.isIdentifier(node.expression)) {
        const helper = node.expression.text;
        const sourceCount = ['interfaceTextPlural', 'tPlural', 'tp'].includes(helper) ? 2 : 1;
        if (['interfaceText', 'interfaceTextProps', 'interfaceTextPlural', 't', 'tp', 'tPlural'].includes(helper)) {
          node.arguments.slice(0, sourceCount).forEach((argument) => {
            staticStrings(argument, values).forEach((value) => add(argument, value));
          });
        }
      }

      if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
        const tag = jsxTagName(node);
        const attrs = [...node.attributes.properties];
        const localized = localizedAncestor || localizedTags.has(tag) || (
          tag === 'ErrorSegment' && isTrueAttribute(attrs, 'translateCaption')
        );
        const attributeNames = tag === 'LocalizedText'
          ? ['source']
          : tag === 'LocalizedPopup'
            ? ['content']
            : tag === 'LocalizedPluralText'
              ? ['singular', 'other']
              : tag === 'PlaceholderSegment'
                ? ['caption']
                : tag === 'ErrorSegment' && isTrueAttribute(attrs, 'translateCaption')
                  ? ['caption']
                  : [];
        for (const name of attributeNames) {
          const attribute = attrs.find((item) => ts.isJsxAttribute(item) && item.name.getText() === name);
          const value = attribute && attributeValue(attribute);
          if (typeof value === 'string') add(attribute, value);
          else staticStrings(value, values).forEach((source) => add(attribute, source));
        }
        if (ts.isJsxOpeningElement(node)) {
          ts.forEachChild(node, (child) => visit(child, localized));
          return;
        }
      }

      if (ts.isJsxText(node) && !localizedAncestor) {
        const value = node.getText(sourceFile).replace(/\s+/g, ' ').trim();
        if (/\p{L}/u.test(value)) {
          rawJsxText.push({
            source: value,
            file: relativeFile,
            line: sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1,
          });
        }
      }
      ts.forEachChild(node, (child) => visit(child, localizedAncestor));
    };
    visit(sourceFile);
  });
  return { references, rawJsxText };
};

const localeCatalogs = Object.fromEntries(localeIds.map((locale) => [
  locale,
  JSON.parse(fs.readFileSync(path.join(localeRoot, `${locale}.json`), 'utf8')),
]));
const { references, rawJsxText } = collectLocalizationReferences();

const formatFailures = () => {
  const failures = [];
  const base = localeCatalogs.es;
  const baseKeys = Object.keys(base).sort();
  for (const locale of localeIds) {
    const catalog = localeCatalogs[locale];
    const keys = Object.keys(catalog).sort();
    if (JSON.stringify(keys) !== JSON.stringify(baseKeys)) {
      failures.push(`${locale}: catalog keys differ from es.json`);
      continue;
    }
    for (const key of baseKeys) {
      const value = catalog[key];
      if (typeof value !== 'string' || !value.trim()) {
        failures.push(`${locale}: empty or non-string value for ${JSON.stringify(key)}`);
      } else if (JSON.stringify(placeholders(value)) !== JSON.stringify(placeholders(key))) {
        failures.push(`${locale}: placeholder mismatch for ${JSON.stringify(key)}`);
      }
    }
  }
  return failures;
};

describe('interface locale coverage', () => {
  it('keeps all locale catalogs in sync with complete placeholder translations', () => {
    expect(formatFailures()).toEqual([]);
  });

  it('provides every fixed source reference in all twelve locale catalogs', () => {
    const missing = [...new Map(references.map((reference) => [reference.source, reference])).values()]
      .flatMap(({ source, file, line }) => localeIds
        .filter((locale) => typeof localeCatalogs[locale][source] !== 'string' || !localeCatalogs[locale][source].trim())
        .map((locale) => `${locale}:${file}:${line}: ${source}`));
    expect(missing).toEqual([]);
  });

  it('keeps fixed prose out of raw JSX text nodes', () => {
    const raw = rawJsxText.filter(({ source }) => !rawTechnicalJsxText.has(source));
    expect(raw).toEqual([]);
  });
});
