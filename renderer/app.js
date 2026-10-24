// A2UI v0.9 browser reference renderer for the pinned A2UIRender Extended catalog.
// Model text is rendered as text and expressions use a small parser, never eval.
export class JsonlStream {
  constructor(onMessage) { this.onMessage = onMessage; this.buffer = ""; this.line = 0; this.closed = false; }
  push(chunk) {
    if (this.closed) throw new Error("流已经结束");
    if (typeof chunk !== "string") throw new Error("流片段必须是字符串");
    this.buffer += chunk;
    let index;
    while ((index = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, index).replace(/\r$/, ""); this.buffer = this.buffer.slice(index + 1); this.parse(line);
    }
  }
  parse(line) {
    this.line += 1; if (!line.trim()) throw new Error(`第 ${this.line} 行：JSONL 消息不能为空行`);
    try { this.onMessage(JSON.parse(line), this.line); } catch (error) { if (error instanceof SyntaxError) throw new Error(`第 ${this.line} 行：JSON 无效，${error.message}`); throw error; }
  }
  finish() { if (this.closed) throw new Error("流已经结束"); if (this.buffer) { this.parse(this.buffer.replace(/\r$/, "")); this.buffer = ""; } this.closed = true; }
}

const $ = id => typeof document === "undefined" ? null : document.getElementById(id);
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const cleanId = value => typeof value === "string" && value.trim() && value === value.trim();
const html = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = String(text); return node; };

function pointerTokens(path) {
  if (path === "/") return [];
  if (typeof path !== "string" || !path.startsWith("/") || /~(?![01])/.test(path)) throw new Error("JSON Pointer 无效");
  return path.slice(1).split("/").map(token => token.replace(/~1/g, "/").replace(/~0/g, "~"));
}

export function pathValue(model, path) {
  return pointerTokens(path).reduce((value, key) => value == null ? undefined : value[key], model);
}

export function setPathValue(model, path, value, remove = false) {
  const tokens = pointerTokens(path);
  if (!tokens.length) return remove ? {} : value;
  let root = object(model) || Array.isArray(model) ? model : {};
  let current = root;
  for (let index = 0; index < tokens.length - 1; index += 1) {
    const key = tokens[index], next = tokens[index + 1];
    if (Array.isArray(current)) {
      const itemIndex = Number(key);
      if (!Number.isInteger(itemIndex) || itemIndex < 0) throw new Error("数组 JSON Pointer 索引无效");
      while (current.length <= itemIndex) current.push(undefined);
      if (current[itemIndex] == null || typeof current[itemIndex] !== "object") current[itemIndex] = /^\d+$/.test(next) ? [] : {};
      current = current[itemIndex];
    } else {
      if (current[key] == null || typeof current[key] !== "object") current[key] = /^\d+$/.test(next) ? [] : {};
      current = current[key];
    }
  }
  const leaf = tokens.at(-1);
  if (Array.isArray(current)) {
    const index = Number(leaf);
    if (!Number.isInteger(index) || index < 0) throw new Error("数组 JSON Pointer 索引无效");
    if (remove) { if (index < current.length) current.splice(index, 1); }
    else { while (current.length <= index) current.push(undefined); current[index] = value; }
  } else if (remove) delete current[leaf];
  else current[leaf] = value;
  return root;
}

function tokenizeExpression(expression) {
  expression = expression.trim();
  const pattern = /\s*(\$__dataModel(?:\.[A-Za-z_$][\w$]*)*|(?:\d+\.\d+|\d+)|'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|true|false|null|===|!==|==|!=|<=|>=|&&|\|\||[()+\-*/%<>!?])/gy;
  const tokens = []; let offset = 0;
  while (offset < expression.length) {
    pattern.lastIndex = offset;
    const match = pattern.exec(expression);
    if (!match) throw new Error("表达式语法无效或不在安全子集内");
    tokens.push(match[1]); offset = pattern.lastIndex;
  }
  return tokens;
}

export function evaluateExpression(source, model) {
  const match = typeof source === "string" && source.match(/^\{\{\s*([^{}]+?)\s*\}\}$/);
  if (!match) return source;
  const tokens = tokenizeExpression(match[1]);
  if (!tokens.length || tokens.length > 256) throw new Error("表达式为空或过长");
  let cursor = 0, depth = 0;
  const take = expected => { if (tokens[cursor] !== expected) return false; cursor += 1; return true; };
  const primary = () => {
    if (take("!")) return !primary();
    if (take("+")) return +primary();
    if (take("-")) return -primary();
    if (take("(")) {
      depth += 1; if (depth > 20) throw new Error("表达式嵌套过深");
      const value = logicalOr(); if (!take(")")) throw new Error("表达式括号不匹配"); depth -= 1; return value;
    }
    const token = tokens[cursor++];
    if (token === undefined) throw new Error("表达式值缺失");
    if (token.startsWith("$__dataModel")) {
      const path = token.slice("$__dataModel".length).split(".").filter(Boolean);
      return path.reduce((value, key) => value == null ? undefined : value[key], model);
    }
    if (/^\d/.test(token)) return Number(token);
    if (token === "true") return true;
    if (token === "false") return false;
    if (token === "null") return null;
    if (token.startsWith("\"")) return JSON.parse(token);
    if (token.startsWith("'")) return token.slice(1, -1).replace(/\\(['\\])/g, "$1").replace(/\\n/g, "\n").replace(/\\r/g, "\r");
    throw new Error("表达式值无效");
  };
  const chain = (next, operators, apply) => { let value = next(); while (operators.includes(tokens[cursor])) { const operator = tokens[cursor++], right = next(); value = apply(operator, value, right); } return value; };
  const multiplicative = () => chain(primary, ["*", "/", "%"], (op, left, right) => { if (op === "/" && right === 0) throw new Error("表达式不能除以零"); const value = op === "*" ? left * right : op === "/" ? left / right : left % right; if (typeof value === "number" && !Number.isFinite(value)) throw new Error("表达式结果不是有限数值"); return value; });
  const additive = () => chain(multiplicative, ["+", "-"], (op, left, right) => op === "+" ? left + right : left - right);
  const relational = () => chain(additive, ["<", ">", "<=", ">="], (op, left, right) => op === "<" ? left < right : op === ">" ? left > right : op === "<=" ? left <= right : left >= right);
  const equality = () => chain(relational, ["==", "===", "!=", "!=="], (op, left, right) => op === "==" || op === "===" ? left === right : left !== right);
  const logicalAnd = () => chain(equality, ["&&"], (_op, left, right) => Boolean(left) && Boolean(right));
  const logicalOr = () => chain(logicalAnd, ["||"], (_op, left, right) => Boolean(left) || Boolean(right));
  const result = logicalOr();
  if (cursor !== tokens.length) throw new Error("表达式尾部无效");
  return result;
}

function resolve(value, model) {
  if (object(value) && Object.keys(value).length === 1 && typeof value.path === "string") return pathValue(model, value.path);
  if (object(value) && value.functionCall) throw new Error("本地参考 renderer 不执行扩展函数");
  return typeof value === "string" && /^\{\{/.test(value) ? evaluateExpression(value, model) : value;
}

export function schemaErrors(value, schema, catalog, path = "组件", refs = new Set()) {
  if (schema === true || !object(schema)) return [];
  if (schema === false) return [`${path}：不允许此值`];
  if (schema.$ref) {
    if (refs.has(schema.$ref)) return [];
    const target = schema.$ref.slice(2).split("/").reduce((item, key) => item?.[key.replace(/~1/g, "/").replace(/~0/g, "~")], catalog);
    return schemaErrors(value, target, catalog, path, new Set([...refs, schema.$ref]));
  }
  for (const keyword of ["oneOf", "anyOf"]) if (schema[keyword]) {
    const results = schema[keyword].map(branch => schemaErrors(value, branch, catalog, path, refs));
    const valid = results.filter(errors => errors.length === 0).length;
    if ((keyword === "oneOf" && valid !== 1) || (keyword === "anyOf" && valid < 1)) return [`${path}：属性值不符合组件目录`];
  }
  if (schema.allOf) { const errors = schema.allOf.flatMap(branch => schemaErrors(value, branch, catalog, path, refs)); if (errors.length) return errors; }
  const typeOk = {object: object(value), array: Array.isArray(value), string: typeof value === "string", number: typeof value === "number" && Number.isFinite(value), integer: Number.isInteger(value), boolean: typeof value === "boolean", null: value === null};
  if (schema.type && !(Array.isArray(schema.type) ? schema.type.some(type => typeOk[type]) : typeOk[schema.type])) return [`${path}：类型不符合 catalog`];
  if ("const" in schema && value !== schema.const) return [`${path}：必须为 ${schema.const}`];
  if (schema.enum && !schema.enum.includes(value)) return [`${path}：值不在 catalog enum 中`];
  const errors = [];
  if (object(value)) {
    for (const required of schema.required || []) if (!(required in value)) errors.push(`${path}：缺少 ${required}`);
    const properties = schema.properties || {};
    if (schema.additionalProperties === false) for (const key of Object.keys(value)) if (!(key in properties)) errors.push(`${path}：不支持属性 ${key}`);
    for (const [key, child] of Object.entries(properties)) if (key in value) errors.push(...schemaErrors(value[key], child, catalog, `${path}.${key}`, refs));
    for (const [pattern, child] of Object.entries(schema.patternProperties || {})) for (const key of Object.keys(value)) if (new RegExp(pattern).test(key)) errors.push(...schemaErrors(value[key], child, catalog, `${path}.${key}`, refs));
  }
  if (Array.isArray(value) && schema.items) value.forEach((item, index) => errors.push(...schemaErrors(item, schema.items, catalog, `${path}[${index}]`, refs)));
  return errors;
}

function dimension(value) { return typeof value === "number" ? `${value}px` : value === "matchParent" ? "100%" : value === "wrapContent" ? "fit-content" : String(value || ""); }
function safeUrl(value, context = {}) {
  if (typeof value !== "string") return "";
  try {
    const url = new URL(value, location.href);
    if (url.origin === location.origin && url.pathname.startsWith("/examples/")) return url.href;
    const allowed = context.a2ui?.allowedResourceDomains || [];
    return ["https:", "http:"].includes(url.protocol) && allowed.includes(url.hostname) ? url.href : "";
  } catch { return ""; }
}

function applyStyles(node, component, model) {
  const styles = component.styles || {};
  const mapping = {fontColor: "color", backgroundColor: "backgroundColor", textAlign: "textAlign", fontWeight: "fontWeight", fontSize: "fontSize", width: "width", height: "height", minWidth: "minWidth", minHeight: "minHeight", maxWidth: "maxWidth", maxHeight: "maxHeight", opacity: "opacity", padding: "padding", margin: "margin", borderColor: "borderColor"};
  for (const [key, css] of Object.entries(mapping)) if (styles[key] !== undefined) {
    let value; try { value = resolve(styles[key], model); } catch { continue; }
    node.style[css] = ["width", "height", "minWidth", "minHeight", "maxWidth", "maxHeight", "fontSize", "padding", "margin"].includes(key) ? dimension(value) : String(value);
  }
}

export class Playground {
  constructor(catalog, defaultContext) { this.catalog = catalog; this.defaultContext = defaultContext; this.reset(); }
  status(text, state = "") { if ($("status")) { $("status").textContent = text; $("status").dataset.state = state; } }
  reset() {
    clearTimeout(this.timer); this.session = (this.session || 0) + 1; this.messages = []; this.nodes = new Map(); this.model = {}; this.surfaceId = null;
    this.started = false; this.complete = false; this.failed = false; this.deleted = false; this.cursor = 0; this.lines = []; this.parser = null; this.expressionFailure = false;
    this.selections = {radio: {}, checkbox: {}, select: {}, toggle: {}}; this.inputs = {}; this.tabs = {}; this.submitting = new Set(); this.submitted = new Set(); this.results = [];
    if ($("preview")) $("preview").replaceChildren(html("div", "empty-state", "粘贴 A2UI JSONL 后开始渲染"));
    if ($("error-panel")) $("error-panel").hidden = true; if ($("result-panel")) $("result-panel").replaceChildren(html("p", "inspector-empty", "选择或填写后点击回答中的确认按钮，这里会显示下一轮 query。"));
    if ($("result-count")) $("result-count").textContent = "0"; if ($("copy-result")) $("copy-result").disabled = true; if ($("status")) this.status("准备就绪");
  }
  error(error) { this.failed = true; this.complete = false; if ($("error-text")) $("error-text").textContent = error.message || String(error); if ($("error-panel")) $("error-panel").hidden = false; this.status("校验失败", "error"); }
  begin(context) { this.reset(); this.context = structuredClone(context || this.defaultContext); this.started = true; this.parser = new JsonlStream((message, line) => this.accept(message, line)); this.status("等待消息", "streaming"); }
  prepare() {
    let context; try { context = JSON.parse($("context").value); } catch { throw new Error("运行时上下文不是有效 JSON"); }
    const source = $("source").value; if (!source.trim()) throw new Error("请先粘贴 A2UI JSONL 内容"); this.begin(context);
    this.lines = source.split("\n").filter((line, index, all) => !(index === all.length - 1 && line === ""));
  }
  accept(message, line) {
    if (!object(message) || message.version !== "v0.9") throw new Error(`第 ${line} 行：必须使用 v0.9`);
    const keys = Object.keys(message).filter(key => key !== "version"); if (keys.length !== 1) throw new Error(`第 ${line} 行：每条消息只能包含一种操作`);
    const kind = keys[0], data = message[kind]; if (!object(data)) throw new Error(`第 ${line} 行：消息内容必须是对象`);
    if (kind === "createSurface") {
      if (this.messages.length || data.catalogId !== "ohos.a2ui.extended.catalog" || !cleanId(data.surfaceId)) throw new Error(`第 ${line} 行：createSurface 无效`);
      this.surfaceId = data.surfaceId;
    } else {
      if (data.surfaceId !== this.surfaceId) throw new Error(`第 ${line} 行：surfaceId 不一致`);
      if (kind === "updateComponents") {
        if (!Array.isArray(data.components) || !data.components.length) throw new Error(`第 ${line} 行：components 不能为空`);
        for (const node of data.components) { if (!object(node) || !cleanId(node.id) || !this.catalog.components[node.component]) throw new Error(`第 ${line} 行：组件或 ID 无效`); this.nodes.set(node.id, node); }
      } else if (kind === "updateDataModel") {
        if ("value" in data) this.model = setPathValue(this.model, data.path || "/", data.value);
        else this.model = setPathValue(this.model, data.path || "/", undefined, true);
      } else if (kind === "deleteSurface") { this.nodes.clear(); this.model = {}; this.deleted = true; }
      else throw new Error(`第 ${line} 行：不支持 ${kind}`);
    }
    this.messages.push(message); this.render(); if ($("message-count")) $("message-count").textContent = String(this.messages.length);
    if ($("surface-label")) $("surface-label").textContent = this.surfaceId || "等待创建 surface";
    if ($("progress-label")) $("progress-label").textContent = `${this.messages.length} / ${this.lines.length || 0} 条消息`;
    if ($("messages-panel")) { const entry = html("div", "message-entry", `${line} ${kind}`); $("messages-panel").append(entry); }
  }
  childrenOf(node) {
    const children = node.component === "If" ? (evaluateExpression(node.condition, this.model) ? node.childrenIf : node.childrenElse) : node.children;
    return Array.isArray(children) ? children : [];
  }
  listForGroup(kind, group) { return [...this.nodes.values()].filter(node => node.component === kind && resolve(node.group, this.model) === group); }
  interactionLocked() { return !this.complete || this.submitting.size > 0 || this.expressionFailure; }
  controlEnabled(node) { try { return resolve(node.enabled, this.model) !== false; } catch { return false; } }
  ensureChoice(kind, group) {
    const nodes = this.listForGroup(kind === "radio" ? "Radio" : "Checkbox", group);
    if (kind === "radio") {
      if (!(group in this.selections.radio)) {
        const checked = nodes.find(node => { try { return Boolean(resolve(node.checked, this.model)); } catch { return false; } });
        if (checked) this.selections.radio[group] = resolve(checked.value, this.model);
      }
      return this.selections.radio[group];
    }
    if (!(group in this.selections.checkbox)) {
      this.selections.checkbox[group] = nodes.filter(node => { try { return Boolean(resolve(node.select, this.model)); } catch { return false; } }).map(node => resolve(node.value, this.model));
    }
    return this.selections.checkbox[group];
  }
  renderNode(id, ancestors = new Set()) {
    if (!this.nodes.has(id)) return html("div", "pending-node", `等待组件 ${id}`);
    if (ancestors.has(id)) return html("div", "component-error", `检测到循环引用：${id}`);
    const node = this.nodes.get(id), next = new Set(ancestors).add(id), type = node.component; let el;
    if (["Row", "Column", "Stack", "Grid", "List", "NavContainer"].includes(type)) {
      el = html("div", `a2ui-${type.toLowerCase()}`);
      if (type === "Grid") el.style.gridTemplateColumns = "repeat(auto-fit,minmax(min(100%,160px),1fr))";
      if (["Row", "Column", "List"].includes(type) && typeof node.itemMargin === "number") el.style.gap = `${node.itemMargin}px`;
      for (const child of this.childrenOf(node)) el.append(this.renderNode(child, next));
    } else if (type === "If") {
      el = html("div", "a2ui-if"); for (const child of this.childrenOf(node)) el.append(this.renderNode(child, next));
    } else if (type === "Tabs") {
      el = html("div", `a2ui-tabs${node.vertical ? " vertical" : ""}`);
      const children = this.childrenOf(node), active = Math.min(Math.max(0, this.tabs[id] ?? node.tabIndex ?? 0), Math.max(children.length - 1, 0));
      const bar = html("div", "a2ui-tab-bar"); bar.setAttribute("role", "tablist");
      for (const [index, childId] of children.entries()) {
        const child = this.nodes.get(childId), tab = html("button", "a2ui-tab", child?.title || `选项 ${index + 1}`);
        tab.type = "button"; tab.setAttribute("role", "tab"); tab.setAttribute("aria-selected", String(index === active)); tab.disabled = this.interactionLocked();
        tab.onclick = () => { this.tabs[id] = index; this.render(); }; bar.append(tab);
      }
      el.append(bar); if (children[active]) el.append(this.renderNode(children[active], next));
    } else if (type === "TabContent") {
      el = html("div", "a2ui-tab-content"); for (const child of this.childrenOf(node)) el.append(this.renderNode(child, next));
    } else if (type === "Text") {
      let content = ""; try { content = resolve(node.content, this.model) ?? ""; } catch (error) { content = `内容表达式无效：${error.message}`; }
      el = html("div", "a2ui-text", content);
    } else if (type === "Image") {
      el = document.createElement("img"); el.className = "a2ui-image"; el.src = safeUrl(node.src, this.context); el.alt = node.accessibility?.label || "图片";
      if (!el.src) el.alt = "图片资源不可用";
    } else if (type === "Divider") el = html("hr", "a2ui-divider");
    else if (type === "Progress") {
      el = document.createElement("progress"); el.className = "a2ui-progress";
      try { el.max = Number(resolve(node.total ?? 1, this.model)); el.value = Number(resolve(node.value ?? 0, this.model)); } catch { el.max = 1; el.value = 0; }
    } else if (type === "Button") {
      el = html("button", "a2ui-button", resolve(node.label, this.model) ?? ""); el.type = "button";
      el.disabled = this.interactionLocked() || !node.action?.event || !this.controlEnabled(node) || this.submitted.has(id);
      el.onclick = () => this.submit(node);
    } else if (type === "TextInput") {
      el = document.createElement("input"); el.className = "a2ui-input"; const inputType = resolve(node.type, this.model);
      el.type = inputType === "number" || inputType === "numberDecimal" ? "number" : inputType === "email" ? "email" : inputType === "url" ? "url" : "text";
      const binding = object(node.text) && typeof node.text.path === "string" ? node.text.path : null;
      const value = binding ? pathValue(this.model, binding) : this.inputs[id];
      el.value = value == null ? (typeof node.text === "string" ? node.text : "") : String(value);
      el.placeholder = String(resolve(node.placeholder, this.model) ?? ""); el.disabled = this.interactionLocked() || !this.controlEnabled(node);
      el.maxLength = Number(resolve(node.maxLength, this.model) || 524288);
      el.setAttribute("aria-label", node.accessibility?.label || el.placeholder || "输入内容"); el.dataset.controlId = id;
      el.addEventListener("input", () => { if (binding) this.model = setPathValue(this.model, binding, el.type === "number" && el.value !== "" ? Number(el.value) : el.value); else this.inputs[id] = el.value; this.renderPreservingFocus(id); });
    } else if (type === "Toggle") {
      el = html("label", "a2ui-toggle"); const input = document.createElement("input"); input.type = "checkbox";
      const binding = object(node.isOn) && typeof node.isOn.path === "string" ? node.isOn.path : null;
      input.checked = Boolean(binding ? pathValue(this.model, binding) : this.selections.toggle[id] ?? resolve(node.isOn, this.model));
      input.disabled = this.interactionLocked() || !this.controlEnabled(node); input.dataset.controlId = id;
      input.onchange = () => { if (binding) this.model = setPathValue(this.model, binding, input.checked); else this.selections.toggle[id] = input.checked; this.render(); };
      el.append(input, html("span", "", resolve(node.label, this.model) || "开启"));
    } else if (type === "Radio") {
      const group = String(resolve(node.group, this.model) ?? ""); const value = String(resolve(node.value, this.model) ?? "");
      el = html("label", "choice-option radio-option"); const input = document.createElement("input"); input.type = "radio"; input.name = `radio-${this.surfaceId}-${group}`; input.value = value;
      input.checked = this.ensureChoice("radio", group) === value; input.disabled = this.interactionLocked() || !this.controlEnabled(node);
      input.onchange = () => { if (!input.checked) return; this.selections.radio[group] = value; for (const choice of this.listForGroup("Radio", group)) if (object(choice.checked) && choice.checked.path) this.model = setPathValue(this.model, choice.checked.path, resolve(choice.value, this.model) === value); this.render(); };
      el.append(input, html("span", "option-label", node.accessibility?.label || value));
    } else if (type === "Checkbox") {
      const group = String(resolve(node.group, this.model) ?? ""); const value = String(resolve(node.value, this.model) ?? "");
      el = html("label", "choice-option"); const input = document.createElement("input"); input.type = "checkbox"; input.value = value;
      input.checked = (this.ensureChoice("checkbox", group) || []).includes(value); input.disabled = this.interactionLocked() || !this.controlEnabled(node);
      input.onchange = () => { const selected = new Set(this.ensureChoice("checkbox", group) || []); if (input.checked) selected.add(value); else selected.delete(value); this.selections.checkbox[group] = this.listForGroup("Checkbox", group).map(choice => String(resolve(choice.value, this.model))).filter(item => selected.has(item)); if (object(node.select) && node.select.path) this.model = setPathValue(this.model, node.select.path, input.checked); this.render(); };
      const label = html("span", "option-label", resolve(node.label, this.model) || value); el.append(input, label);
    } else if (type === "CheckboxGroup") {
      const group = String(resolve(node.group, this.model) ?? ""), choices = this.listForGroup("Checkbox", group), selected = this.ensureChoice("checkbox", group) || [];
      el = html("label", "choice-option checkbox-group-control"); const input = document.createElement("input"); input.type = "checkbox"; input.checked = choices.length > 0 && choices.every(choice => selected.includes(String(resolve(choice.value, this.model)))); input.indeterminate = selected.length > 0 && !input.checked;
      input.disabled = this.interactionLocked() || choices.some(choice => !this.controlEnabled(choice));
      input.onchange = () => { this.selections.checkbox[group] = input.checked ? choices.map(choice => String(resolve(choice.value, this.model))) : []; for (const choice of choices) if (object(choice.select) && choice.select.path) this.model = setPathValue(this.model, choice.select.path, input.checked); this.render(); };
      el.append(input, html("span", "option-label", "全选"));
    } else if (type === "Select") {
      el = document.createElement("select"); el.className = "a2ui-select"; el.disabled = this.interactionLocked() || !this.controlEnabled(node); el.dataset.controlId = id;
      el.setAttribute("aria-label", node.accessibility?.label || "选择一项");
      const options = Array.isArray(node.options) ? node.options : [], binding = object(node.selected) && typeof node.selected.path === "string" ? node.selected.path : null;
      const selected = this.selections.select[id] ?? (binding ? pathValue(this.model, binding) : resolve(node.selected, this.model));
      if (Number.isInteger(Number(selected)) && Number(selected) >= 0) this.selections.select[id] = Number(selected);
      else delete this.selections.select[id];
      const placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "请选择"; placeholder.disabled = true; el.append(placeholder);
      options.forEach((option, index) => { const item = document.createElement("option"); item.value = String(index); item.textContent = String(resolve(option.value, this.model) ?? ""); item.selected = Number(selected) === index; el.append(item); });
      el.value = Number.isInteger(Number(selected)) && Number(selected) >= 0 ? String(Number(selected)) : "";
      el.onchange = () => { const index = Number(el.value); this.selections.select[id] = index; if (binding) this.model = setPathValue(this.model, binding, index); if (object(node.value) && node.value.path) this.model = setPathValue(this.model, node.value.path, String(resolve(options[index]?.value, this.model) ?? "")); this.render(); };
    } else if (type === "Web") el = html("div", "a2ui-web", "Web 资源由宿主策略控制");
    else el = html("div", "component-error", `不支持组件：${type}`);
    el.dataset.componentId = id; applyStyles(el, node, this.model); return el;
  }
  renderPreservingFocus(id) {
    const old = document.activeElement, start = old?.selectionStart, end = old?.selectionEnd; this.render();
    const replacement = document.querySelector(`[data-control-id="${CSS.escape(id)}"]`); replacement?.focus();
    if (typeof start === "number" && typeof replacement?.setSelectionRange === "function") replacement.setSelectionRange(start, end);
  }
  render() {
    if (!$('preview')) return;
    this.expressionFailure = this.hasExpressionErrors();
    if (this.deleted) { $('preview').replaceChildren(html("div", "empty-state", "Surface 已删除")); return; }
    if (this.nodes.has("root")) $('preview').replaceChildren(this.renderNode("root"));
  }
  hasExpressionErrors() {
    const inspect = value => {
      if (typeof value === "string") {
        if (!value.includes("{{") && !value.includes("}}")) return false;
        if (!/^\{\{\s*[^{}]+\s*\}\}$/.test(value)) return true;
        try { const result = evaluateExpression(value, this.model); return typeof result === "number" && !Number.isFinite(result); } catch { return true; }
      }
      if (Array.isArray(value)) return value.some(inspect);
      return object(value) && Object.values(value).some(inspect);
    };
    return [...this.nodes.values()].some(inspect);
  }
  async submit(node) {
    const id = node.id, event = node.action?.event; if (!event || !this.complete || this.submitting.size > 0 || this.submitted.has(id)) return;
    this.submitting.add(id); this.render();
    try {
      const result = await request("/api/submit", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({messages: this.messages, context: this.context, buttonId: id, dataModel: this.model, selections: this.selections, inputs: this.inputs})});
      const detail = {...result, dataModel: structuredClone(this.model), selections: structuredClone(this.selections)};
      if (window.xyA2uiHost?.onEvent) await window.xyA2uiHost.onEvent(detail);
      this.submitted.add(id); this.results.push(detail); this.showResult(detail); window.dispatchEvent(new CustomEvent("a2ui:event", {detail}));
    } catch (error) { const detail = {error: error.message, event, surfaceId: this.surfaceId}; this.results.push(detail); this.showResult(detail); }
    finally { this.submitting.delete(id); this.render(); }
  }
  showResult(detail) {
    const panel = $("result-panel"); if (!panel) return;
    if (this.results.length === 1) panel.replaceChildren();
    const entry = html("article", "query-entry"), header = html("header"); header.append(html("span", "", detail.error ? "提交失败" : detail.event?.name || "交互结果"), html("span", "", detail.surfaceId || ""));
    entry.append(header, html("pre", "", detail.error || detail.query || JSON.stringify(detail.event, null, 2))); panel.append(entry);
    if ($("result-count")) $("result-count").textContent = String(this.results.length);
    if ($("copy-result")) { $("copy-result").disabled = !detail.query; $("copy-result").onclick = () => navigator.clipboard.writeText(detail.query); }
  }
  async finish() {
    this.parser.finish(); const response = await fetch("/api/validate", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({messages: this.messages, context: this.context})});
    const result = await response.json(); if (!response.ok) throw new Error(result.error || "A2UI 校验失败");
    this.complete = true; this.render(); this.status("已完成", "complete");
  }
  async instant() { try { this.prepare(); for (const line of this.lines) this.parser.push(`${line}\n`); await this.finish(); } catch (error) { this.error(error); } }
  async step() { try { if (!this.started) this.prepare(); if (this.cursor < this.lines.length) this.parser.push(`${this.lines[this.cursor++] }\n`); if (this.cursor === this.lines.length) await this.finish(); } catch (error) { this.error(error); } }
  async play() {
    try {
      if (!this.started) this.prepare(); const session = this.session;
      while (this.cursor < this.lines.length && session === this.session) {
        this.parser.push(`${this.lines[this.cursor++] }\n`);
        if ($("speed")) await new Promise(resolve => setTimeout(resolve, Number($("speed").value) || 220));
      }
      if (session === this.session && this.cursor === this.lines.length) await this.finish();
    } catch (error) { this.error(error); }
  }
}

async function request(url, options) { const response = await fetch(url, options); const data = await response.json(); if (!response.ok) throw new Error(data.error || `请求失败：${response.status}`); return data; }
async function bootstrap() {
  if (!$('source')) return;
  try {
    const data = await request('/api/bootstrap'), app = new Playground(data.catalog, data.context);
    for (const scenario of data.scenarios) { const option = document.createElement('option'); option.value = scenario.id; option.textContent = scenario.id; $('sample')?.append(option); }
    async function load() { const id = $('sample')?.value; if (!id) return; const sample = await request(`/api/example?id=${encodeURIComponent(id)}`); $('source').value = sample.text; $('context').value = JSON.stringify(sample.context, null, 2); app.reset(); }
    $('sample')?.addEventListener('change', load); $('load-sample')?.addEventListener('click', load); $('instant')?.addEventListener('click', () => app.instant()); $('step')?.addEventListener('click', () => app.step()); $('play')?.addEventListener('click', () => app.play()); $('reset')?.addEventListener('click', () => app.reset());
    $('default-context')?.addEventListener('click', () => { $('context').value = JSON.stringify(data.context, null, 2); });
    window.xyA2uiPreview = {start: context => app.begin(context), push: chunk => app.parser.push(chunk), finish: () => app.finish(), cancel: () => app.reset(), getState: () => ({complete: app.complete, failed: app.failed, messages: app.messages.length, surfaceId: app.surfaceId})};
    if ($('sample')) { $('sample').value = data.scenarios[0]?.id || ''; await load(); await app.instant(); }
  } catch (error) { if ($('error-text')) $('error-text').textContent = error.message; if ($('error-panel')) $('error-panel').hidden = false; }
}
if (typeof document !== 'undefined') bootstrap();
