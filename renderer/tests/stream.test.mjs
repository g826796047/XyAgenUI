import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JsonlStream, schemaErrors, evaluateExpression, pathValue, setPathValue} from '../app.js';

test('任意分块、中文、CRLF 和末行无换行', () => {
  const source = '{"content":"你好👋"}\r\n{"value":2}', messages = [];
  for (let size = 1; size <= source.length; size++) {
    const stream = new JsonlStream((message, line) => messages.push([message, line]));
    for (let i = 0; i < source.length; i += size) stream.push(source.slice(i, i + size));
    stream.finish(); assert.deepEqual(messages.slice(-2), [[{content:'你好👋'},1],[{value:2},2]]); assert.throws(() => stream.push('{}'), /流已经结束/);
  }
});

test('没有完整行时不提前输出，空行和不完整 JSON 报告行号', () => {
  const messages = [], stream = new JsonlStream(message => messages.push(message));
  stream.push('{"a":'); assert.equal(messages.length, 0); stream.push('1}\n'); assert.deepEqual(messages, [{a:1}]); stream.finish();
  assert.throws(() => new JsonlStream(() => {}).push('{}\n\n'), /第 2 行.*不能为空行/);
  const invalid = new JsonlStream(() => {}); invalid.push('{}\n{"a":'); assert.throws(() => invalid.finish(), /第 2 行.*JSON 无效/);
});

test('安全表达式只读取数据模型，不执行脚本', () => {
  assert.equal(evaluateExpression('{{ $__dataModel.form.people * $__dataModel.form.perPerson }}', {form:{people:6,perPerson:200}}), 1200);
  assert.equal(evaluateExpression('{{ $__dataModel.form.people >= 4 && !$__dataModel.form.done }}', {form:{people:6,done:false}}), true);
  assert.equal(evaluateExpression('{{ 4 + 2 * 3 }}', {}), 10);
  assert.throws(() => evaluateExpression('{{ 1 / 0 }}', {}), /除以零/);
  assert.throws(() => evaluateExpression('{{ eval(1) }}', {}), /安全子集/);
  assert.deepEqual(schemaErrors({component:'Text',invented:1},{type:'object',properties:{component:{const:'Text'}},additionalProperties:false},{}), ['组件：不支持属性 invented']);
});

test('JSON Pointer 支持局部设置、转义路径和删除', () => {
  let model = {form:{people:4}, values:{'a/b':1}};
  model = setPathValue(model, '/form/people', 6);
  model = setPathValue(model, '/values/a~1b', undefined, true);
  assert.equal(pathValue(model, '/form/people'), 6);
  assert.equal(pathValue(model, '/values/a~1b'), undefined);
});

test('所有样例保持 JSONL 可逐行解析', async () => {
  const scenarios = JSON.parse(await readFile(new URL('../../examples/scenarios.json', import.meta.url), 'utf8'));
  for (const {id} of scenarios) {
    const source = await readFile(new URL(`../../examples/${id}.jsonl`, import.meta.url), 'utf8');
    const stream = new JsonlStream(() => {}); stream.push(source); stream.finish();
  }
});
