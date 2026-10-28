import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateMessages} from '../renderer/core.js';

test('官方快照和项目 overlay 的组件一致，overlay 只扩展宿主函数', async () => {
  const official = JSON.parse(await readFile(new URL('../references/agenui/agenui_catalog.json', import.meta.url), 'utf8'));
  const project = JSON.parse(await readFile(new URL('../references/agenui/gdxy_catalog.json', import.meta.url), 'utf8'));
  assert.equal(project.catalogId, official.catalogId);
  assert.deepEqual(Object.keys(project.components).sort(), Object.keys(official.components).sort());
  for (const [name, schema] of Object.entries(official.functions)) assert.deepEqual(project.functions[name], schema);
  for (const name of ['sendMsgToXiaoyi','openSuperlink','openApplink','openDeeplink','calculateNumber']) assert.ok(project.functions[name]);
  assert.equal(project.$defs.anyFunction.oneOf.length, Object.keys(project.functions).length);
});

test('FunctionCall 必须显式出现在运行时函数白名单中', async () => {
  const official = JSON.parse(await readFile(new URL('../references/agenui/gdxy_catalog.json', import.meta.url), 'utf8'));
  const source = await readFile(new URL('../examples/selection-single.jsonl', import.meta.url), 'utf8');
  const messages = source.trim().split(/\r?\n/).map(line => JSON.parse(line));
  const result = validateMessages(messages, official, {a2ui: {catalogId: official.catalogId}});
  assert.ok(result.errors.some(error => error.includes('sendMsgToXiaoyi 未在 a2ui.allowedFunctions 中声明')));
});
