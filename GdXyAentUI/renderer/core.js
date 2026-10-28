export class JsonlStream {
  constructor(onMessage) { this.onMessage = onMessage; this.buffer = ''; this.line = 0; this.closed = false; }
  push(chunk) {
    if (this.closed) throw new Error('流已经结束');
    if (typeof chunk !== 'string') throw new Error('流片段必须是字符串');
    this.buffer += chunk;
    let index;
    while ((index = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, index).replace(/\r$/, '');
      this.buffer = this.buffer.slice(index + 1);
      this.parse(line);
    }
  }
  parse(line) {
    this.line += 1;
    if (!line.trim()) throw new Error(`第 ${this.line} 行：JSONL 不允许空行`);
    try { this.onMessage(JSON.parse(line), this.line); }
    catch (error) { if (error instanceof SyntaxError) throw new Error(`第 ${this.line} 行：JSON 无效，${error.message}`); throw error; }
  }
  finish() {
    if (this.closed) throw new Error('流已经结束');
    if (this.buffer) { this.parse(this.buffer.replace(/\r$/, '')); this.buffer = ''; }
    this.closed = true;
  }
}

export const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const deepEqual = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function pointerTokens(pointer) {
  if (pointer === '/') return [];
  if (typeof pointer !== 'string' || !pointer.startsWith('/') || /~(?![01])/.test(pointer)) throw new Error('JSON Pointer 无效');
  const tokens = pointer.slice(1).split('/').map(token => token.replace(/~1/g, '/').replace(/~0/g, '~'));
  if (tokens.some(token => ['__proto__', 'constructor', 'prototype'].includes(token))) throw new Error('JSON Pointer 不允许对象原型路径');
  return tokens;
}

export function getPath(model, pointer) {
  return pointerTokens(pointer).reduce((value, token) => {
    if (Array.isArray(value)) return value[Number(token)];
    return value == null ? undefined : value[token];
  }, model);
}

export function setPath(model, pointer, value, remove = false) {
  const tokens = pointerTokens(pointer);
  if (!tokens.length) return remove ? {} : value;
  const root = isObject(model) || Array.isArray(model) ? model : {};
  let current = root;
  for (let i = 0; i < tokens.length - 1; i += 1) {
    const key = tokens[i], next = tokens[i + 1];
    if (Array.isArray(current)) {
      const index = Number(key);
      if (!Number.isInteger(index) || index < 0) throw new Error('数组路径索引无效');
      while (current.length <= index) current.push(undefined);
      if (!isObject(current[index]) && !Array.isArray(current[index])) current[index] = /^\d+$/.test(next) ? [] : {};
      current = current[index];
    } else {
      if (!isObject(current[key]) && !Array.isArray(current[key])) current[key] = /^\d+$/.test(next) ? [] : {};
      current = current[key];
    }
  }
  const leaf = tokens.at(-1);
  if (Array.isArray(current)) {
    const index = Number(leaf);
    if (!Number.isInteger(index) || index < 0) throw new Error('数组路径索引无效');
    if (remove) { if (index < current.length) current.splice(index, 1); }
    else { while (current.length <= index) current.push(undefined); current[index] = value; }
  } else if (remove) delete current[leaf];
  else current[leaf] = value;
  return root;
}

function atRef(catalog, ref) {
  if (!ref.startsWith('#/')) return undefined;
  return ref.slice(2).split('/').reduce((value, token) => value?.[token.replace(/~1/g, '/').replace(/~0/g, '~')], catalog);
}

function allowedProperties(schema, catalog, seen = new Set()) {
  if (!isObject(schema)) return new Set();
  const result = new Set(Object.keys(schema.properties || {}));
  if (schema.$ref && !seen.has(schema.$ref)) {
    const target = atRef(catalog, schema.$ref);
    for (const key of allowedProperties(target, catalog, new Set([...seen, schema.$ref]))) result.add(key);
  }
  for (const branch of schema.allOf || []) for (const key of allowedProperties(branch, catalog, seen)) result.add(key);
  for (const keyWord of ['oneOf', 'anyOf']) for (const branch of schema[keyWord] || []) for (const key of allowedProperties(branch, catalog, seen)) result.add(key);
  return result;
}

export function schemaErrors(value, schema, catalog, path = 'value', refs = new Set()) {
  if (schema === false) return [`${path}: 不允许此值`];
  if (schema === true || !isObject(schema)) return [];
  if (schema.$ref) {
    if (refs.has(schema.$ref)) return [];
    const target = atRef(catalog, schema.$ref);
    if (!target) return [`${path}: 无法解析 schema 引用 ${schema.$ref}`];
    return schemaErrors(value, target, catalog, path, new Set([...refs, schema.$ref]));
  }
  const errors = [];
  if (schema.allOf) for (const part of schema.allOf) errors.push(...schemaErrors(value, part, catalog, path, new Set(refs)));
  for (const keyWord of ['oneOf', 'anyOf']) if (schema[keyWord]) {
    const results = schema[keyWord].map(branch => schemaErrors(value, branch, catalog, path, new Set(refs)));
    const successes = results.filter(result => result.length === 0).length;
    if ((keyWord === 'oneOf' && successes !== 1) || (keyWord === 'anyOf' && successes < 1)) errors.push(`${path}: 值不符合 ${keyWord} catalog schema`);
  }
  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const ok = types.some(type => ({
      object: isObject(value), array: Array.isArray(value), string: typeof value === 'string',
      number: typeof value === 'number' && Number.isFinite(value), integer: Number.isInteger(value),
      boolean: typeof value === 'boolean', null: value === null,
    })[type]);
    if (!ok) return [...errors, `${path}: 类型不符合 catalog`];
  }
  if ('const' in schema && !deepEqual(value, schema.const)) errors.push(`${path}: 必须为 ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.some(item => deepEqual(value, item))) errors.push(`${path}: 值不在 catalog enum 中`);
  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) errors.push(`${path}: 字符串短于最小长度 ${schema.minLength}`);
    if (schema.maxLength !== undefined && value.length > schema.maxLength) errors.push(`${path}: 字符串长于最大长度 ${schema.maxLength}`);
    if (schema.pattern && !(new RegExp(schema.pattern).test(value))) errors.push(`${path}: 字符串不符合 pattern`);
    if (schema.format === 'uri' && !/^[a-z][a-z\d+.-]*:/i.test(value)) errors.push(`${path}: 需要 URI`);
  }
  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) errors.push(`${path}: 小于最小值 ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum) errors.push(`${path}: 大于最大值 ${schema.maximum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) errors.push(`${path}: 少于最小项目数 ${schema.minItems}`);
    if (schema.maxItems !== undefined && value.length > schema.maxItems) errors.push(`${path}: 超过最大项目数 ${schema.maxItems}`);
    if (schema.uniqueItems && value.some((item, i) => value.slice(i + 1).some(next => deepEqual(item, next)))) errors.push(`${path}: 项目必须唯一`);
    if (schema.items) value.forEach((item, i) => errors.push(...schemaErrors(item, schema.items, catalog, `${path}[${i}]`, new Set())));
  }
  if (isObject(value)) {
    for (const key of schema.required || []) if (!(key in value)) errors.push(`${path}: 缺少 ${key}`);
    const properties = schema.properties || {};
    for (const [key, child] of Object.entries(properties)) if (key in value) errors.push(...schemaErrors(value[key], child, catalog, `${path}.${key}`, new Set()));
    for (const [pattern, child] of Object.entries(schema.patternProperties || {})) {
      for (const key of Object.keys(value)) if (new RegExp(pattern).test(key)) errors.push(...schemaErrors(value[key], child, catalog, `${path}.${key}`, new Set()));
    }
    if (schema.additionalProperties === false) {
      const localAllowed = new Set([...Object.keys(properties), ...Object.keys(schema.patternProperties || {})]);
      for (const key of Object.keys(value)) if (![...localAllowed].some(item => item.startsWith('^') ? new RegExp(item).test(key) : item === key)) errors.push(`${path}: 不支持属性 ${key}`);
    } else if (isObject(schema.additionalProperties)) {
      for (const [key, item] of Object.entries(value)) if (!(key in properties)) errors.push(...schemaErrors(item, schema.additionalProperties, catalog, `${path}.${key}`, new Set()));
    }
    if (schema.unevaluatedProperties === false) {
      const allAllowed = allowedProperties(schema, catalog, refs);
      for (const key of Object.keys(value)) if (!allAllowed.has(key)) errors.push(`${path}: 不支持属性 ${key}`);
    }
  }
  return errors;
}

function validateCustomCall(call, args, context, errors, path) {
  const allowed = context?.a2ui?.allowedFunctions;
  if (!Array.isArray(allowed) || !allowed.includes(call)) errors.push(`${path}: ${call} 未在 a2ui.allowedFunctions 中声明`);
  if (!isObject(args)) { errors.push(`${path}: functionCall.args 必须是对象`); return; }
  if (call === 'sendMsgToXiaoyi') {
    if (typeof args.query !== 'string' || !args.query.trim()) { errors.push(`${path}: query 必须是非空字符串`); return; }
    const names = [...args.query.matchAll(/\$\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map(match => match[1]);
    const residual = args.query.replace(/\$\{[A-Za-z][A-Za-z0-9_]*\}/g, '');
    if (residual.includes('${') || residual.includes('{') || residual.includes('}')) errors.push(`${path}: query 模板占位符格式错误`);
    if (new Set(names).size !== names.length) errors.push(`${path}: query 占位符重复`);
    const parameters = Object.keys(args).filter(key => key !== 'query');
    if (names.length !== parameters.length || names.some(name => !parameters.includes(name)) || parameters.some(name => !names.includes(name))) errors.push(`${path}: query 占位符必须和参数名一一对应`);
  }
  if (call === 'openSuperlink' || call === 'openApplink') {
    if (typeof args.url !== 'string' || !/^(https?:|app:)/i.test(args.url)) errors.push(`${path}: url 必须是有效链接字符串`);
  }
  if (call === 'openDeeplink' && (typeof args.bundleName !== 'string' || typeof args.url !== 'string')) errors.push(`${path}: bundleName 和 url 必须是字符串`);
}

function scanFunctionCalls(value, catalog, context, errors, path, visited = new Set()) {
  if (Array.isArray(value)) { value.forEach((item, i) => scanFunctionCalls(item, catalog, context, errors, `${path}[${i}]`, visited)); return; }
  if (!isObject(value)) return;
  if (isObject(value.functionCall)) {
    const fc = value.functionCall;
    if (typeof fc.call !== 'string') errors.push(`${path}.functionCall.call 必须是字符串`);
    else {
      const schema = catalog.functions?.[fc.call];
      if (!schema) errors.push(`${path}: 未知函数 ${fc.call}`);
      else errors.push(...schemaErrors(fc, schema, catalog, `${path}.functionCall`));
      validateCustomCall(fc.call, fc.args || {}, context, errors, `${path}.functionCall`);
    }
  } else if (typeof value.call === 'string' && isObject(value.args)) {
    const schema = catalog.functions?.[value.call];
    if (!schema) errors.push(`${path}: 未知嵌套函数 ${value.call}`);
    else errors.push(...schemaErrors(value, schema, catalog, path));
    validateCustomCall(value.call, value.args, context, errors, path);
  }
  for (const [key, child] of Object.entries(value)) {
    if (key === 'event') errors.push(`${path}.event: 本项目只允许 action.functionCall`);
    scanFunctionCalls(child, catalog, context, errors, `${path}.${key}`, visited);
  }
}

function componentReferences(node) {
  const refs = [];
  if (Array.isArray(node.children)) refs.push(...node.children);
  else if (isObject(node.children) && typeof node.children.componentId === 'string') refs.push(node.children.componentId);
  if (node.component === 'Card' && node.child) refs.push(node.child);
  if (node.component === 'Button' && node.child) refs.push(node.child);
  if (node.component === 'Tabs' && Array.isArray(node.tabs)) refs.push(...node.tabs.map(tab => tab.child).filter(Boolean));
  if (node.component === 'Modal') refs.push(node.trigger, node.content);
  return refs.filter(value => typeof value === 'string');
}

function graphErrors(nodes) {
  const errors = [], edges = new Map(), parents = new Map();
  for (const [id, node] of nodes) {
    const refs = componentReferences(node); edges.set(id, refs);
    for (const child of refs) {
      if (!nodes.has(child)) errors.push(`${id}: 引用了不存在的组件 ${child}`);
      if (parents.has(child)) errors.push(`组件 ${child} 有重复或多个父节点：${parents.get(child)}、${id}`);
      else parents.set(child, id);
    }
  }
  if (!nodes.has('root')) errors.push('缺少 id 为 root 的根组件');
  const visiting = new Set(), visited = new Set();
  function visit(id) {
    if (visiting.has(id)) { errors.push(`组件引用存在循环：${id}`); return; }
    if (visited.has(id) || !nodes.has(id)) return;
    visiting.add(id); for (const child of edges.get(id) || []) visit(child); visiting.delete(id); visited.add(id);
  }
  visit('root');
  for (const id of nodes.keys()) if (!visited.has(id)) errors.push(`组件 ${id} 没有从 root 引用（孤立组件）`);
  return errors;
}

function bindingErrors(node, model) {
  const errors = [], types = {
    Text: {text: 'string'}, Markdown: {content: 'string'}, RichText: {text: 'string'},
    Image: {url: 'string'}, Video: {url: 'string'}, AudioPlayer: {url: 'string'},
    Web: {url: 'string'}, Lottie: {url: 'string'}, TextField: {value: 'string'},
    CheckBox: {value: 'boolean'}, ChoicePicker: {value: 'strings'},
    Slider: {value: 'number'}, DateTimeInput: {value: 'string'},
  };
  for (const [key, expected] of Object.entries(types[node.component] || {})) {
    const raw = node[key]; if (raw === undefined) continue;
    if (isObject(raw) && typeof raw.call === 'string') continue;
    if (isObject(raw) && typeof raw.path === 'string' && !raw.path.startsWith('/')) continue;
    let value;
    try { value = resolveDynamic(raw, model); } catch (error) { errors.push(`${node.id}.${key}: ${error.message}`); continue; }
    const ok = expected === 'strings' ? Array.isArray(value) && value.every(item => typeof item === 'string') : typeof value === expected && (expected !== 'number' || Number.isFinite(value));
    if (!ok) errors.push(`${node.id}.${key}: 数据模型绑定必须为 ${expected === 'strings' ? '字符串数组（单选也使用数组）' : expected}`);
  }
  if (node.component === 'ChoicePicker') {
    const values = (node.options || []).map(option => option?.value);
    if (new Set(values).size !== values.length) errors.push(`${node.id}: ChoicePicker 选项 value 必须唯一`);
    let selected; try { selected = resolveDynamic(node.value, model); } catch {}
    if (Array.isArray(selected)) {
      if (node.variant !== 'multipleSelection' && selected.length > 1) errors.push(`${node.id}: 单选不能选择多个值`);
      if (new Set(selected).size !== selected.length || selected.some(value => !values.includes(value))) errors.push(`${node.id}: 选中值重复或不在 options 中`);
    }
  }
  const scan = value => {
    if (Array.isArray(value)) return value.forEach(scan);
    if (!isObject(value)) return;
    if (typeof value.path === 'string') try { pointerTokens(value.path.startsWith('/') ? value.path : `/${value.path}`); } catch (error) { errors.push(`${node.id}: ${error.message}`); }
    Object.values(value).forEach(scan);
  };
  scan(node);
  return errors;
}

export function validateMessages(messages, catalog, context = {}) {
  const errors = [], nodes = new Map(); let surfaceId = null, created = false, deleted = false, model = {};
  if (!Array.isArray(messages) || messages.length === 0) return {errors: ['JSONL 至少需要一条消息'], nodes, model, surfaceId};
  for (const [index, message] of messages.entries()) {
    const line = index + 1, kinds = isObject(message) ? ['createSurface', 'updateComponents', 'updateDataModel', 'deleteSurface'].filter(kind => kind in message) : [];
    if (!isObject(message) || message.version !== 'v0.9' || kinds.length !== 1 || Object.keys(message).length !== 2) {
      errors.push(`第 ${line} 行：必须是仅包含一个操作的 A2UI v0.9 envelope`); continue;
    }
    const kind = kinds[0], body = message[kind];
    if (!isObject(body)) { errors.push(`第 ${line} 行：${kind} 必须是对象`); continue; }
    const fields = {createSurface:['surfaceId','catalogId','theme','sendDataModel'], updateComponents:['surfaceId','components'], updateDataModel:['surfaceId','path','value'], deleteSurface:['surfaceId']}[kind];
    for (const key of Object.keys(body)) if (!fields.includes(key)) errors.push(`第 ${line} 行：${kind} 不支持属性 ${key}`);
    if (typeof body.surfaceId !== 'string' || !body.surfaceId.trim()) errors.push(`第 ${line} 行：surfaceId 无效`);
    if (kind === 'createSurface') {
      if (created || index !== 0) errors.push(`第 ${line} 行：createSurface 必须且只能是第一条消息`);
      if (typeof body.surfaceId !== 'string' || !body.surfaceId.trim()) errors.push(`第 ${line} 行：surfaceId 无效`);
      if (body.catalogId !== catalog.catalogId) errors.push(`第 ${line} 行：catalogId 必须是 ${catalog.catalogId}`);
      if ('sendDataModel' in body && typeof body.sendDataModel !== 'boolean') errors.push(`第 ${line} 行：sendDataModel 必须是布尔值`);
      if ('theme' in body && !catalog.$defs?.theme) errors.push(`第 ${line} 行：当前 catalog 没有声明 theme schema`);
      surfaceId = body.surfaceId; created = true; continue;
    }
    if (!created || deleted) { errors.push(`第 ${line} 行：surface 尚未创建或已删除`); continue; }
    if (body.surfaceId !== surfaceId) errors.push(`第 ${line} 行：surfaceId 与 createSurface 不一致`);
    if (kind === 'updateComponents') {
      if (!Array.isArray(body.components) || body.components.length === 0) { errors.push(`第 ${line} 行：components 必须是非空数组`); continue; }
      const ids = new Set();
      for (const [componentIndex, node] of body.components.entries()) {
        const p = `第 ${line} 行 components[${componentIndex}]`;
        if (!isObject(node) || typeof node.id !== 'string' || !node.id.trim()) { errors.push(`${p}: 缺少有效 id`); continue; }
        if (ids.has(node.id)) errors.push(`${p}: 同一条更新中组件 ID 重复 ${node.id}`);
        ids.add(node.id);
        if (typeof node.component !== 'string' || !catalog.components[node.component]) { errors.push(`${p}: 未知组件 ${node.component}`); continue; }
        if (Array.isArray(context?.a2ui?.allowedComponents) && !context.a2ui.allowedComponents.includes(node.component)) errors.push(`${p}: ${node.component} 未在 a2ui.allowedComponents 中声明`);
        if (['Markdown', 'Chart', 'Lottie'].includes(node.component)) {
          const enabled = context?.a2ui?.allowedComponents;
          if (!Array.isArray(enabled) || !enabled.includes(node.component)) errors.push(`${p}: ${node.component} 需要在 a2ui.allowedComponents 中声明`);
        }
        errors.push(...schemaErrors(node, catalog.components[node.component], catalog, p));
        nodes.set(node.id, node);
        scanFunctionCalls(node, catalog, context, errors, p);
      }
    } else if (kind === 'updateDataModel') {
      const pointer = body.path ?? '/';
      try { pointerTokens(pointer); } catch (error) { errors.push(`第 ${line} 行：${error.message}`); continue; }
      try { model = setPath(model, pointer, body.value, !('value' in body)); }
      catch (error) { errors.push(`第 ${line} 行：${error.message}`); }
    } else if (kind === 'deleteSurface') deleted = true;
  }
  if (!created) errors.push('缺少 createSurface');
  if (!deleted) {
    errors.push(...graphErrors(nodes));
    for (const node of nodes.values()) errors.push(...bindingErrors(node, model));
  }
  return {errors: [...new Set(errors)], nodes, model, surfaceId, deleted};
}

export function resolveDynamic(value, model, scope = {}) {
  if (Array.isArray(value)) return value.map(item => resolveDynamic(item, model, scope));
  if (!isObject(value)) return value;
  if (Object.keys(value).length === 1 && typeof value.path === 'string') {
    if (value.path.startsWith('/')) return getPath(model, value.path);
    return value.path.split('/').reduce((item, key) => item == null ? undefined : item[key], scope);
  }
  if (typeof value.call === 'string' && isObject(value.args)) return evaluateCatalogFunction(value.call, value.args, model, scope);
  return value;
}

export function resolveCallArguments(value, model, scope = {}, allowedFunctions = []) {
  if (Array.isArray(value)) return value.map(item => resolveCallArguments(item, model, scope, allowedFunctions));
  if (!isObject(value)) return value;
  if (Object.keys(value).length === 1 && typeof value.path === 'string') return resolveDynamic(value, model, scope);
  if (typeof value.call === 'string') {
    if (!Array.isArray(allowedFunctions) || !allowedFunctions.includes(value.call)) throw new Error(`函数 ${value.call} 未在运行时白名单中声明`);
    const args = resolveCallArguments(value.args || {}, model, scope, allowedFunctions);
    return evaluateCatalogFunction(value.call, args, model, scope);
  }
  return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, resolveCallArguments(child, model, scope, allowedFunctions)]));
}

function evaluateCatalogFunction(name, args, model, scope) {
  const resolved = Object.fromEntries(Object.entries(args).map(([key, value]) => [key, resolveDynamic(value, model, scope)]));
  if (name === 'calculateNumber') {
    if ([resolved.left, resolved.right].some(value => (typeof value !== 'number' && typeof value !== 'string') || String(value).trim() === '')) throw new Error('calculateNumber 参数不是数字');
    const left = Number(resolved.left), right = Number(resolved.right);
    if (!Number.isFinite(left) || !Number.isFinite(right)) throw new Error('calculateNumber 参数不是数字');
    let result;
    if (resolved.operator === 'add') result = left + right;
    else if (resolved.operator === 'subtract') result = left - right;
    else if (resolved.operator === 'multiply') result = left * right;
    else if (resolved.operator === 'divide' && right !== 0) result = left / right;
    else throw new Error('calculateNumber 运算无效');
    if (!Number.isFinite(result)) throw new Error('calculateNumber 结果溢出');
    return result;
  }
  if (name === 'required') return resolved.value !== undefined && resolved.value !== null && resolved.value !== '' && !(Array.isArray(resolved.value) && resolved.value.length === 0);
  if (name === 'length') { const n = String(resolved.value ?? '').length; return (resolved.min === undefined || n >= resolved.min) && (resolved.max === undefined || n <= resolved.max); }
  if (name === 'numeric') { const value = resolved.value; if (!['number','string'].includes(typeof value) || String(value).trim() === '') return false; const n = Number(value); return Number.isFinite(n) && (resolved.min === undefined || n >= resolved.min) && (resolved.max === undefined || n <= resolved.max); }
  if (name === 'email') return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(resolved.value ?? ''));
  if (name === 'regex') { try { return new RegExp(resolved.pattern).test(String(resolved.value ?? '')); } catch { return false; } }
  if (name === 'and') return resolved.values.every(Boolean);
  if (name === 'or') return resolved.values.some(Boolean);
  if (name === 'not') return !resolved.value;
  if (name === 'formatString') return String(resolved.value ?? '').replace(/\$\{(\/[^}]+)\}/g, (_m, pointer) => String(getPath(model, pointer) ?? ''));
  if (name === 'formatNumber') {
    if (!['number','string'].includes(typeof resolved.value) || String(resolved.value).trim() === '') return '';
    const number = Number(resolved.value);
    if (!Number.isFinite(number)) return '';
    const decimals = Number.isInteger(Number(resolved.decimals)) ? Number(resolved.decimals) : 0;
    return number.toLocaleString('zh-CN', {useGrouping: resolved.grouping !== false, minimumFractionDigits: decimals, maximumFractionDigits: decimals});
  }
  if (name === 'formatCurrency') {
    const number = Number(resolved.value);
    if (!Number.isFinite(number)) return '';
    try { return new Intl.NumberFormat('zh-CN', {style: 'currency', currency: resolved.currency, maximumFractionDigits: Number(resolved.decimals ?? 2)}).format(number); }
    catch { return `${resolved.currency} ${number}`; }
  }
  if (name === 'pluralize') return resolved.other ?? '';
  if (name === 'token') return String(resolved.name ?? '');
  throw new Error(`本地预览不执行宿主函数 ${name}`);
}

export function interpolateQuery(args) {
  if (!isObject(args) || typeof args.query !== 'string' || !args.query.trim()) throw new Error('sendMsgToXiaoyi.query 必须是非空字符串');
  const names = [...args.query.matchAll(/\$\{([A-Za-z][A-Za-z0-9_]*)\}/g)].map(match => match[1]);
  if (/[{}]/.test(args.query.replace(/\$\{[A-Za-z][A-Za-z0-9_]*\}/g, ''))) throw new Error('query 模板占位符格式错误');
  if (new Set(names).size !== names.length) throw new Error('query 占位符重复');
  const params = Object.keys(args).filter(key => key !== 'query');
  if (names.length !== params.length || names.some(name => !params.includes(name))) throw new Error('query 参数映射不完整');
  const format = value => {
    if (typeof value === 'string' && value.trim()) return value;
    if (Array.isArray(value) && value.length && value.every(item => typeof item === 'string' && item.trim())) {
      if (value.length === 1) return value[0];
      if (value.length === 2) return `${value[0]}和${value[1]}`;
      return `${value.slice(0, -1).join('、')}和${value.at(-1)}`;
    }
    throw new Error('query 参数必须解析为非空字符串或字符串数组');
  };
  return args.query.replace(/\$\{([A-Za-z][A-Za-z0-9_]*)\}/g, (_match, name) => format(args[name]));
}
