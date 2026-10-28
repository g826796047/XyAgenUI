import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const basePath = path.join(root, 'references/agenui/agenui_catalog.json');
const outputPath = path.join(root, 'references/agenui/gdxy_catalog.json');
const catalog = JSON.parse(await readFile(basePath, 'utf8'));
const ref = name => ({$ref: `#/$defs/${name}`});
const hostFunction = (name, description, properties, required, returnType = 'void', additionalProperties = false) => ({
  type: 'object', description,
  properties: {
    call: {const: name},
    args: {type: 'object', properties, required, additionalProperties},
    returnType: {const: returnType},
  },
  required: ['call', 'args'],
  unevaluatedProperties: false,
});

catalog.functions.sendMsgToXiaoyi = hostFunction(
  'sendMsgToXiaoyi',
  '宿主函数：将 query 模板中的命名参数解析为最终用户 query 并发送到当前对话。',
  {query: {type: 'string', minLength: 1}},
  ['query'],
  'void',
  ref('common_types_DynamicValue'),
);
catalog.functions.openSuperlink = hostFunction('openSuperlink', '宿主函数：打开经过宿主安全策略检查的超级链接。', {url: {type: 'string', format: 'uri'}}, ['url']);
catalog.functions.openApplink = hostFunction('openApplink', '宿主函数：打开应用链接。', {url: {type: 'string', format: 'uri'}}, ['url']);
catalog.functions.openDeeplink = hostFunction('openDeeplink', '宿主函数：打开指定 bundle 的 deep link。', {bundleName: {type: 'string', minLength: 1}, url: {type: 'string', minLength: 1}}, ['bundleName', 'url']);
catalog.functions.calculateNumber = hostFunction(
  'calculateNumber',
  '可选宿主函数：对两个数执行受限算术。必须由宿主注册后才能生成。',
  {
    left: ref('common_types_DynamicNumber'),
    right: ref('common_types_DynamicNumber'),
    operator: {type: 'string', enum: ['add', 'subtract', 'multiply', 'divide']},
  },
  ['left', 'right', 'operator'],
  'number',
);

const functions = Object.keys(catalog.functions).sort();
catalog.$defs.anyFunction.oneOf = functions.map(name => ({$ref: `#/functions/${name}`}));
catalog.$id = 'gdxy_catalog.json';
catalog.title = 'GdXyAentUI A2UI Catalog';
catalog.description = 'AGenUI official component catalog plus schema declarations for host functions used by GdXyAentUI.';
await writeFile(outputPath, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
console.log(`Wrote ${path.relative(root, outputPath)} with ${Object.keys(catalog.components).length} components and ${functions.length} functions.`);
