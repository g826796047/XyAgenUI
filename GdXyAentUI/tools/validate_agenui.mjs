import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JsonlStream, validateMessages} from '../renderer/core.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(await readFile(path.join(root, 'references/agenui/gdxy_catalog.json'), 'utf8'));
const [, , inputPath, contextPath] = process.argv;
if (!inputPath) { console.error('用法：node tools/validate_agenui.mjs <jsonl> [context.json]'); process.exit(2); }
const source = await readFile(path.resolve(inputPath), 'utf8');
const messages = [];
const parser = new JsonlStream(message => messages.push(message));
try {
  const lines = source.split(/\r?\n/).filter((line, index, all) => !(index === all.length - 1 && line === ''));
  for (const line of lines) parser.push(`${line}\n`);
  parser.finish();
  let context = {};
  if (contextPath) context = JSON.parse(await readFile(path.resolve(contextPath), 'utf8'));
  const result = validateMessages(messages, catalog, context);
  if (result.errors.length) { console.error(`校验失败（${result.errors.length} 项）：`); for (const error of result.errors) console.error(`- ${error}`); process.exit(1); }
  console.log(`A2UI 校验通过：${result.nodes.size} 个组件，surface=${result.surfaceId}`);
} catch (error) { console.error(error.message || String(error)); process.exit(1); }
