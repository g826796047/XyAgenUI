# 鸿蒙智能体UI协议设计

## 1 协议说明

1. 本协议基于A2UI原生协议进行扩展，协议消息格式及数据结构沿用A2UI的设计，能力扩展主要通过组件扩展承载，扩展支持的样式、交互、条件表达式等能力也仅对扩展组件生效。
2. 本协议基于A2UI v0.9版本进行扩展设计。
3. 本协议第2章节主要阐述A2UI原生协议，扩展部分全部在第3章节进行阐述。

## 2 A2UI原生协议

### 2.1 协议消息

#### 2.1.1 协议数据流

1. Create Surface: 服务端发送一个createSurface消息来初始化界面。
2. Update Surface：一旦界面创建好了，服务端通过发送一个或多个包含UI组件定义的updateComponents消息来定义界面。
3. Update Data Model: 一旦界面创建好了，服务端可以在任意时刻发送updateDataModel消息来定义或者修改UI组件的数据。
4. Render：客户端根据updateComponents消息和update_DataModel消息渲染UI界面。
5. Dynamic updates：当用户与应用交互或者有新的信息时，服务端可以发送新增的updateComponents消息和updateDataModel消息来动态调整UI。
6. Delete Surface：当UI界面已经不需要了，服务端可以发送deleteSurface消息移除该界面。

#### 2.1.2 消息顺序

1. updateComponents必须在createSurface之后发出。
2. updateComponents和updateDataModel先后顺序没有约束。
3. 不同的surface之间的消息应该独立。
4. 多个消息可增量修改同一个surface。

消息推荐发送顺序：

#### 2.1.3 createSurface消息

**消息格式**

```json
{
  version: "v0.9";
  createSurface: {
    surfaceId: string;      // Required: Unique surface identifier
    catalogId: string;      // Required: URL of component catalog
    theme?: object;         // Optional: Theme configuration
    send__DataModel?: boolean; // Optional: Request client to send data model updates
  }
}
```

**消息示例**

```json
{
  "version": "v0.9",
  "createSurface": {
    "surfaceId": "main",
    "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json",
    "theme": {
        "primaryColor": "#00BFFF",
        "iconUrl": "https://www.example.com/a.ico",
        "agentDisplayName": "A2UI Agent"
    }
  }
}
```

#### 2.1.4 updateComponents消息

**消息格式**

```json
{
  version: "v0.9";
  updateComponents: {
    surfaceId: string;        // Required: Target surface
    components: Array<{       // Required: List of components
      id: string;             // Required: Component ID
      component: string;      // Required: Component type name
      ...properties           // Component-specific properties (flat)
    }>
  }
}
```

**单组件示例**

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "main",
    "components": [
      {
        "id": "greeting",
        "component": "Text",
        "text": "Hello, World!",
        "variant": "h1"
      }
    ]
  }
}
```

**多组件示例**

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "main",
    "components": [
      {
        "id": "root",
        "component": "Column",
        "children": ["header", "body"]
      },
      {
        "id": "header",
        "component": "Text",
        "text": "Welcome"
      },
      {
        "id": "body",
        "component": "Card",
        "child": "content"
      },
      {
        "id": "content",
        "component": "Text",
        "text": {"path": "/message"}
      }
    ]
  }
}
```

**更新已有组件示例**

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "main",
    "components": [
      {
        "id": "greeting",
        "component": "Text",
        "text": "Hello, Alice!",
        "variant": "h1"
      }
    ]
  }
}
```

#### 2.1.5 updateDataModel消息

**消息格式**

```json
{
  version: "v0.9";
  updateDataModel: {
    surfaceId: string;      // Required: Target surface
    path?: string;          // Optional: JSON Pointer path (defaults to "/")
    value?: any;            // Optional: Value to set (omit to delete)
  }
}
```

**初始化整个数据示例**

```json
{
  "version": "v0.9",
  "updateDataModel": {
    "surfaceId": "main",
    "path": "/",
    "value": {
      "user": {
        "name": "Alice",
        "email": "alice@example.com"
      },
      "items": []
    }
  }
}
```

**更新数据示例**

```json
{
  "version": "v0.9",
  "updateDataModel": {
    "surfaceId": "main",
    "path": "/user/email",
    "value": "alice@newdomain.com"
  }
}
```

#### 2.1.6 deleteSurface 消息

**消息格式**

```json
{
  version: "v0.9";
  deleteSurface: {
    surfaceId: string;        // Required: Surface to delete
  }
}
```

**消息示例**

```json
{
  "version": "v0.9",
  "deleteSurface": {
    "surfaceId": "modal"
  }
}
```

#### 2.1.7 能力协商机制

由于客户端和服务端智能体可以支持多个catalog，所以他们需要通过catalog协商握手机制来决定使用哪个catalog，具体机制如下：

1. **智能体公布其支持的catalog（可选）**：智能体可以公布其支持哪些catalog（比如通过A2A的Agent Card形式）。这个可以帮助客户端知道是否智能体支持客户端特定的能力，但是这个信息仅供客户端参考，客户端不一定要使用，该过程也是可选的。

```json
{
  "name": "Ecommerce Dashboard Agent",
  "description": "This agent visualizes ecommerce data...",
  "capabilities": {
    "extensions": [
      {
        "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
        "description": "Provides agent driven UI using the A2UI JSON format.",
        "params": {
          "supportedCatalogIds": [
            "https://a2ui.org/specification/v0_9/basic_catalog.json",
            "https://github.com/.../rizzcharts_catalog_definition.json"
          ]
        }
      }
    ]
  }
}
```

2. **客户端公布其支持的（必选）Catalog**：客户端可以在每条消息的metadata部分发送其支持的catalog列表给智能体，catalog可以通过偏好来排序。通过这个来精确告知智能体客户端具体的渲染能力。以下是以A2A消息为例：

```json
{
  "parts": [
    {
      "text": "What is the current status of my flight?"
    }
  ],
  "metadata": {
    "a2uiClientCapabilities": {
      "supportedCatalogIds": [
        "https://a2ui.org/specification/v0_9/basic_catalog.json",
        "https://github.com/.../rizzcharts_catalog_definition.json"
      ]
    }
  }
}
```

3. **智能体选用catalog**：当智能体创建新的界面时，需要从客户端发送的支持的catalog列表中选择一个最匹配的来使用。在一个界面的生成过程中（即一次createSurface生命周期过程）仅能按照这一个选定的catalog来生成界面，统一个会话中的多个界面生成可以选用不用的catalog。如果没有匹配的catalog，智能体可以不发送界面。

```json
{
  "createSurface": {
    "surfaceId": "salesDashboard",
    "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"
  }
}
```

### 2.2 A2UI组件

#### 2.2.1 内置组件

A2UI原生支持的组件包括布局组件、展示组件、交互组件、容器组件、高级组件5大类，详细原生组件类型、功能说明及属性见附件A2UI原生组件

| 名称 | 类型 |
|------|------|
| Row | 布局组件 |
| Column | 布局组件 |
| List | 布局组件 |
| Text | 展示组件 |
| Image | 展示组件 |
| Icon | 展示组件 |
| Divider | 展示组件 |
| Button | 交互组件 |
| Toggle | 交互组件 |
| TextField | 交互组件 |
| CheckBox | 交互组件 |
| Slider | 交互组件 |
| DateTimeInput | 交互组件 |
| ChoicePicker | 交互组件 |
| Card | 容器组件 |
| Modal | 容器组件 |
| Tabs | 容器组件 |
| Video | 高级组件 |
| AudioPlayer | 高级组件 |

#### 2.2.2 自定义组件

A2UI原生支持新增自定义组件，可以在catalog新增组件定义，形式如下：

```json
"Image": {
      "type": "object",
      "allOf": [
        {
          "$ref": "common_types.json#/$defs/ComponentCommon"
        },
        {
          "$ref": "#/$defs/CatalogComponentCommon"
        },
        {
          "type": "object",
          "properties": {
            "component": {
              "const": "Image"
            },
            "url": {
              "$ref": "common_types.json#/$defs/DynamicString",
              "description": "The URL of the image to display."
            },
            "fit": {
              "type": "string",
              "description": "Specifies how the image should be resized to fit its container. This corresponds to the CSS 'object-fit' property.",
              "enum": ["contain", "cover", "fill", "none", "scaleDown"],
              "default": "fill"
            },
            "variant": {
              "type": "string",
              "description": "A hint for the image size and style.",
              "enum": [
                "icon",
                "avatar",
                "smallFeature",
                "mediumFeature",
                "largeFeature",
                "header"
              ],
              "default": "mediumFeature"
            }
          },
          "required": ["component", "url"]
        }
      ],
      "unevaluatedProperties": false
    }
```

### 2.3 A2UI交互

#### 2.3.1 交互类型

现有A2UI中定义了两种行为服务端行为和本地行为。

**服务端行为（Server Action）**

通过在交互组件（如Button）中的action属性中设置event字段值定义具体交互，并可以携带可选的context字段上传数据。

```json
{
  "id": "submit-btn",
  "component": "Button",
  "child": "submit-text",
  "variant": "primary",
  "action": {
    "event": {
      "name": "submit_form",
      "context": {
        "itemId": "123",
        "email": { "path": "/formData/email" }
      }
    }
  }
}
```

客户端向服务端发送的消息内容如下所示：

```json
{
  "name": "submit_form",
  "sufaceId": "id",
  "sourceComponentId": "submit-btn",
  "timestamp": " 2026-03-12T06:12:16.444Z ",
  "context":{
    "itemId": "123",
    "email": "abc@abc.com"
  }
}
```

**本地行为（Local Action）**

通过在交互组件（如Button）中的action属性中设置functionCall字段值定义具体交互，并可以携带args字段上传指定参数。

```json
{
  "id": "submit-btn",
  "component": "Button",
  "child": "submit-text",
  "variant": "primary",
  "action": {
    "functionCall": {
      "call": "openUrl",
      "args": {
        "url": "${/url}"
      }
    }
  }
}
```

#### 2.3.2 内置函数

| 名称 | 说明 |
|------|------|
| required | 必填验证 |
| regex | 正则验证 |
| length | 长度验证 |
| numeric | 数值验证 |
| email | 邮箱验证 |
| formatString | 字符串格式化 |
| formatNumber | 数字格式化 |
| formatCurrency | 货币格式化 |
| formatDate | 日期格式化 |
| pluralize | 复数化 |
| openUrl | 打开链接 |
| and | 逻辑与 |
| or | 逻辑或 |
| not | 逻辑非 |

## 3 A2UI扩展设计

### 3.1 扩展原则

1. 整体采用增加自定义组件方式进行能力扩展。
2. 以下扩展的样式属性、交互能力以及表达式均只在扩展组件上提供，A2UI原生组件上不支持上述扩展的能力。
3. 所有的扩展组件均以Extended.为前缀命名，如Extended.Button。

### 3.2 扩展组件

在A2UI原生组件的基础上，扩展更丰富的组件，支撑多样化UI能力。所有扩展组件均以Extended.<Component Name>方式进行命名，新增组件在updateComponents消息中的描述沿袭A2UI数据结构组织方式，详细扩展组件及属性参见：扩展组件。

```json
{
  "id": "submit-btn", // 必选，组件ID
  "component": "Extended.Button", // 必选，组件类型
  "text": "按钮", // 组件必选属性
  "styles": {  // 可选样式属性
    "fontColor":"#33182431",
    "fontSize":12,
    "other prop":"value"
  }
  // 其他组件相关必选和可选组件
}
```

### 3.3 扩展组件样式

在扩展组件中统一添加styles字段，其值为一个对象，内容为需要设置的属性名及值，若没有明确配置，则使用匹配组件的默认值。具体属性名称和值类型参见附件中样式章节。

```json
{
  "id": "submit-btn",
  "component": "Extended.Button",
  "label": "submit-text",
  "styles": {
    "fontColor":"#33182431",
    "fontSize":12,
    "other prop":"value"
  }
}
```

### 3.4 交互扩展

在扩展组件中统一添加listeners属性，其值为一个对象，对象是一个键值对，其中键是预定义的交互事件类型（如onClick），值是事件处理对象，包含handlerGroups数组、condition字段。具体扩展组件支持的事件参见交互事件章节。

```json
{
  "id": "edit-btn",
  "component": "Extended.Button",
  "child": "submit-text",
  "listeners": {
    "onClick": { // 事件类型
      "handlerGroups": [ // 事件触发的行为组列表
        {
          "condition": "{{ $user.canEdit }}", // 可选，是否执行行为组的判断条件，true则执行，false则跳过
          "handlers": [  // 行为组包含的行为列表
            {
              "id": "validate_form",
              "call": "validate",  // 行为，可选范围为附件中交互章节中的交互行为
              "args": {
                "data": "{{ $__DataModel.formData }}"
              }
            }
          ]
        }
      ]
    }
  }
}
```

行为统一采用如下数据结构描述，扩展的交互能力只可在扩展组件中使用。具体扩展组件支持的行为参见交互行为章节：

```json
{
  "handlerGroups": [ // 事件触发的行为组列表
    {
      "condition": "{{ $user.canEdit }}", // 可选，是否执行行为组的判断条件，true则执行，false则跳过
      "handlers": [  // 行为组包含的行为列表
        {
          "id": "validate_form",
          "call": "validate",  // 行为，可选范围为附件中交互章节中的交互行为
          "args": {
            "data": "{{ $__DataModel.formData }}"
          }
        }
      ]
    }
  ]
}
```

### 3.5 表达式

表达式提供了一种动态计算数据值的能力，统一采用字符串类型引用，形如："{{<expression>}}"，具体语法及用法参考：表达式。表达式仅在自定义组件中生效，且须遵循以下约束：

1. 表达式仅支持扩展组件
2. 限定仅在updateComponents消息中支持表达式
3. A2UI原本的数据路径中的path属性不支持使用表达式
4. 组件component、id属性不可使用
5. 交互行为中的id和type不可使用
6. 表达式只能使用在值上，不能在key中使用
7. 具体可使用表达式的场景参见catalog文件

典型使用场景：

**组件属性值采用表达式计算**

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "main",
    "components": [
      {
        "id": "greeting",
        "component": "Extended.Text",
        "text": "{{ 'Hello, ' + $__DataModel.name + '!' }}"
      }
    ]
  }
}
```

**使用表达式设定行为条件和行为参数值**

```json
{
  "condition": "{{ $__handlerResult['confirm_delete'] == 0 }}",
  "handlers": [{
    "id": "delete_item",
    "call": "setDataModel",
    "args": {
      "path": "{{'/items/' + $index }}",
      "value": null
    }
  }]
}
```

**使用表达式表示组件的样式**

```json
{
  "id": "submit-btn",
  "component": "Extended.Button",
  "child": "submit-text",
  "styles": {
    "fontColor":"#33182431",
    "fontSize": "{{ $__DataModel.fontSize }}",
    "other prop":"value"
  }
}
```

### 3.6 多端设备适配

本协议通过多方面能力达成多端适配能力，实现一次开发多端运行的效果。

#### 3.6.1 布局自适应能力

各个组件中提供的属性设置自带布局自适应能力，使得单个组件本身可以在不同尺寸的场景下自动调整布局、尺寸等。

**长度单位支持**：

| 单位 | 说明 | 使用场景 |
|------|------|----------|
| vp | Virtual Pixel，虚拟像素，默认单位 | 通用尺寸设置 |
| fp | Font Pixel，字体像素，随字体大小缩放 | 文字相关尺寸 |
| % | 百分比，相对于父容器 | 相对布局 |

**自适应布局策略**：

| 枚举值 | 说明 | 适用属性 |
|--------|------|----------|
| wrapContent | 组件大小自适应子内容 | width, height |
| matchParent | 组件大小填充父容器 | width, height |
| spaceBetween | 子元素均匀分布，首尾对齐边缘 | Extended.Row, Extended.Column的justifyContent |
| spaceAround | 子元素均匀分布，首尾间距为中间的一半 | Extended.Row, Extended.Column的justifyContent |
| spaceEvenly | 子元素完全均匀分布 | Extended.Row, Extended.Column的justifyContent |

#### 3.6.2 响应式变量与断点系统

协议提供全局变量用于感知当前窗口状态，配合表达式的响应式更新能力，可以实现动态的多端适配。

**全局响应式变量**：

| 变量名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| __WindowSize | object | 当前窗口尺寸 | { width: 390, height: 844 } |
| __WindowBreakpoint | string | 当前窗口断点枚举值 | "sm", "md", "lg", "xl" |

**断点系统定义**：

| 断点 | 屏幕宽度范围 | 典型设备 |
|------|-------------|----------|
| xs | < 576px | 小屏手机 |
| sm | 576px - 768px | 大屏手机 |
| md | 768px - 992px | 平板竖屏 |
| lg | 992px - 1200px | 平板横屏/小屏笔记本 |
| xl | > 1200px | 桌面显示器 |

**响应式更新机制**：

当表达式中使用的变量（如 $__WindowSize、$__WindowBreakpoint）发生改变时，表达式会自动重新计算，并更新对应的组件属性和样式属性。

#### 3.6.3 Extended.If 条件渲染组件

Extended.If 是一个条件渲染组件，可以根据条件表达式的值动态选择渲染不同的组件分支。结合响应式变量（如 $__WindowSize 和 $__WindowBreakpoint），可以实现不同设备上展示完全不同的组件树结构。

#### 3.6.4 综合示例

以下示例综合运用了多种多端适配能力：

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "main",
    "components": [
      {
        "id": "app_root",
        "component": "Extended.Column",
        "children": ["responsive_nav", "page_content"],
        "styles": {
          "width": "matchParent",    // 【布局自适应】填充父容器宽度，自适应不同屏幕
          "height": "matchParent",   // 【布局自适应】填充父容器高度
          "padding": "{{ $__WindowBreakpoint == 'sm' ? 8 : 16 }}"  // 【响应式变量+表达式】小屏8vp间距，大屏16vp
        }
      },
      {
        "id": "responsive_nav",
        "component": "Extended.If",
        "condition": "{{ $__WindowBreakpoint == 'sm' }}",  // 【断点判断】小屏设备
        "childrenIf": ["mobile_navbar"],     // 【条件渲染】小屏显示汉堡菜单
        "childrenElse": ["desktop_navbar"]   // 【条件渲染】大屏显示完整导航
      },
      {
        "id": "mobile_navbar",
        "component": "Extended.Row",
        "children": ["menu_button", "title"],
        "styles": {
          "justifyContent": "space-between",  // 【布局策略】按钮两端对齐
          "padding": 12
        }
      },
      {
        "id": "desktop_navbar",
        "component": "Extended.Row",
        "children": ["logo", "nav_links", "search_button"],
        "styles": {
          "justifyContent": "spaceBetween",  // 【布局策略】元素均匀分布
          "padding": "16 24"
        }
      },
      {
        "id": "page_content",
        "component": "Extended.If",
        "condition": "{{ $__WindowSize.width >= 768 }}",  // 【窗口尺寸判断】768px以上
        "childrenIf": ["two_column_layout"],    // 【条件渲染】平板及以上双列布局
        "childrenElse": ["single_column"]     // 【条件渲染】手机单列布局
      },
      {
        "id": "two_column_layout",
        "component": "Extended.Row",
        "children": ["main_article", "sidebar"],
        "styles": {
          "width": "matchParent",
          "space": 24  // 【布局自适应】主内容与侧边栏间距24vp
        }
      },
      {
        "id": "main_article",
        "component": "Extended.Column",
        "children": ["article_title", "article_content"],
        "styles": {
          "width": "70%",  // 【百分比布局】占父容器宽度的70%
          "layoutWeight": 1  // 【弹性布局】参与剩余空间分配
        }
      },
      {
        "id": "sidebar",
        "component": "Extended.Column",
        "children": ["widget1", "widget2"],
        "styles": {
          "width": "28%",  // 【百分比布局】占父容器宽度的28%
          "display": "{{ $__WindowSize.width >= 992 ? 'flex' : 'none' }}"  // 【响应式样式】992px以下隐藏侧边栏
        }
      },
      {
        "id": "single_column",
        "component": "Extended.Column",
        "children": ["article_title", "article_content"],
        "styles": {
          "width": "100%",  // 【百分比布局】单列时占满宽度
          "padding": 16
        }
      },
      {
        "id": "article_title",
        "component": "Extended.Text",
        "text": "{{ $__DataModel.articleTitle }}",
        "styles": {
          "fontSize": "{{ $__WindowBreakpoint == 'sm' ? 20 : $__WindowBreakpoint == 'md' ? 24 : 32 }}",  // 【响应式字体】小屏20vp、平板24vp、桌面32vp
          "textAlign": "center",  // 【对齐方式】标题居中
          "fontWeight": 600
        }
      },
      {
        "id": "article_content",
        "component": "Extended.Text",
        "text": "{{ $__DataModel.articleContent }}",
        "styles": {
          "fontSize": 14,  // 【响应式单位】fp单位，随系统字体缩放
          "lineHeight": 1.6
        }
      },
      {
        "id": "product_grid",
        "component": "Extended.Grid",
        "children": ["p1", "p2", "p3", "p4", "p5", "p6"],
        "styles": {
          "columnsTemplate": "{{  // 【动态网格列数】根据窗口宽度自动调整
            $__WindowSize.width < 600 ? '1fr 1fr' :
            $__WindowSize.width < 900 ? '1fr 1fr 1fr' :
            '1fr 1fr 1fr 1fr'
          }}",
          "rowsGap": 16,    // 【布局自适应】行间距16vp
          "columnsGap": 16  // 【布局自适应】列间距16vp
        }
      }
    ]
  }
}
```

## 4 附件

### 4.1 组件

#### 4.1.1 A2UI原生组件

| 名称 | 类型 | 组件说明 | 属性 | 类型 | 属性说明 |
|------|------|----------|------|------|----------|
| Row | 布局组件 | 水平布局组件，子组件水平排列 | children | List[String] | 子组件ID列表 |
| | | | weight | number | 相对权重，类似 CSS flex-grow |
| | | | justify | 字符串枚举<br>"start", "center", "end", "spaceAround", "spaceBetween", "spaceEvenly", "stretch" | 定义子组件沿主轴（水平方向）的排列方式。使用 'spaceBetween' 将项目推到边缘，或使用 'start'/'end'/'center' 将它们打包在一起。 |
| | | | align | 字符串枚举<br>"start", "center", "end", "stretch" | 定义子组件沿交叉轴（竖直方向）的对齐方式。这类似于 CSS 的 'align-items' 属性。 |
| Column | 布局组件 | 竖直布局组件，子组件竖直排列 | children | List[String] | 子组件ID列表 |
| | | | weight | number | 相对权重，类似 CSS flex-grow |
| | | | justify | 字符串枚举<br>"start", "center", "end", "spaceAround", "spaceBetween", "spaceEvenly", "stretch" | 定义子组件沿主轴（竖直方向）的排列方式。使用 'spaceBetween' 将项目推到边缘，或使用 'start'/'end'/'center' 将它们打包在一起。 |
| | | | align | 字符串枚举<br>"start", "center", "end", "stretch" | 定义子组件沿交叉轴（水平方向）的对齐方式。这类似于 CSS 的 'align-items' 属性。 |
| List | 布局组件 | 列表布局组件 | children | List[String]或者object { componentId: string, path: string } | 子组件ID列表，或者模板组件ID和循环数据路径 |
| | | | align | 字符串枚举<br>"start", "center", "end", "stretch" | 定义子组件沿交叉轴的对齐方式。这类似于 CSS 的 'align-items' 属性。 |
| | | | direction | 字符串枚举<br>"vertical", "horizontal" | 定义列表项的排列方向 |
| Text | 展示组件 | 文本组件 | text | string | 要显示的文本内容。虽然支持简单的 Markdown 格式（即不含 HTML、图像或链接），但通常建议使用专用的 UI 组件来获得更丰富、更结构化的呈现。 |
| | | | variant | 字符串枚举<br>"h1", "h2", "h3", "h4", "h5", "caption", "body" | 基本文本样式（字号） |
| Image | 展示组件 | 图片组件 | url | string | 要显示的图像URL |
| | | | fit | 字符串枚举<br>"contain", "cover", "fill", "none", "scaleDown" | 指定图像应如何调整大小以适应其容器。这对应于 CSS 的 'object-fit' 属性。 |
| | | | variant | 字符串枚举<br>"icon", "avatar", "smallFeature", "mediumFeature", "largeFeature", "header" | 图像大小和样式。 |
| Icon | 展示组件 | 图标组件 | name | 字符串枚举<br>"accountCircle", "add", "arrowBack", "arrowForward", "attachFile", "calendarToday", "call", "camera", "check", "close", "delete", "download", "edit", "event", "error", "fastForward", "favorite", "favoriteOff", "folder", "help", "home", "info", "locationOn", "lock", "lockOpen", "mail", "menu", "moreVert", "moreHoriz", "notificationsOff", "notifications", "pause", "payment", "person", "phone", "photo", "play", "print", "refresh", "rewind", "search", "send", "settings", "share", "shoppingCart", "skipNext", "skipPrevious", "star", "starHalf", "starOff", "stop", "upload", "visibility", "visibilityOff", "volumeDown", "volumeMute", "volumeOff", "volumeUp", "warning" | 要显示的图标名称。 |
| Divider | 展示组件 | 分隔线 | axis | 字符串枚举<br>"vertical", "horizontal" | 分隔线的方向。 |
| Button | 交互组件 | 按钮 | child | string | 子组件的 ID。对于带标签的按钮，请使用 'Text' 组件。仅当需求明确要求仅图标按钮时才使用 'Icon'。不要内联定义子组件。 |
| | | | variant | 字符串枚举<br>"default", "primary", "borderless" | 按钮样式的提示。如果省略，则使用默认按钮样式。'primary' 表示这是主要的行动号召按钮。'borderless' 表示按钮没有可视边框或背景，使其子内容看起来像可点击的链接。 |
| | | | action | object，下面两种行为的其中一种<br>1. { event: { name: string, context?: object } }<br>2. { functionCall: FunctionCall } | 按钮点击时候执行的行为。 |
| TextField | 交互组件 | 文本框 | label | string | 输入字段的文本标签。 |
| | | | value | string | 文本字段的值。 |
| | | | validationRegexp | string | 用于客户端输入验证的正则表达式。 |
| | | | textFieldType | 字符串枚举<br>"longText", "number", "shortText", "obscured" | 要显示的输入字段类型。 |
| CheckBox | 交互组件 | 复选框 | label | string | 在复选框旁边显示的文本。 |
| | | | value | boolean | 复选框的当前状态（true 表示选中，false 表示未选中）。 |
| Slider | 交互组件 | 滑块 | label | string | 滑块的标签。 |
| | | | min | number | 滑块的最小值。 |
| | | | max | number | 滑块的最大值。 |
| | | | value | number | 滑块的当前值。 |
| DateTimeInput | 交互组件 | 日期时间输入 | label | string | 输入字段的文本标签。 |
| | | | min | string | ISO 8601 格式的允许的最小日期/时间。 |
| | | | max | string | ISO 8601 格式的允许的最大日期/时间。 |
| | | | value | string | ISO 8601 格式的选定日期和/或时间值。如果尚未设置，请用空字符串初始化。 |
| | | | enableDate | boolean | 如果为 true，则允许用户选择日期。 |
| | | | enableTime | boolean | 如果为 true，则允许用户选择时间。 |
| ChoicePicker | 交互组件 | 选择器 | label | string | 选项组的标签。 |
| | | | variant | 字符串枚举<br>"multipleSelection", "mutuallyExclusive" | 选择器应如何显示和行为的提示。默认值："mutuallyExclusive" |
| | | | options | array | 可供选择的选项列表。 |
| | | | value | string | 当前选定值的列表。这应该绑定到数据模型中的字符串数组。 |
| | | | sdisplayStyle | 字符串枚举<br>"checkbox", "chips" | 组件的显示样式。默认值："checkbox" |
| | | | filterable | boolean | 如果为 true，则显示搜索输入以过滤选项。默认值：false |
| Card | 容器组件 | 卡片 | child | string | 要在卡片内渲染的单个子组件的 ID。要显示多个元素，必须将它们包装在布局组件（如 Column 或 Row）中，并将该容器的 ID 传递到这里。不要传递多个 ID 或不存在的 ID。不要内联定义子组件。 |
| Modal | 容器组件 | 模态框 | trigger | string | 交互时打开模态框的组件的 ID（例如按钮）。不要内联定义组件。 |
| | | | content | string | 要在模态框内显示的组件的 ID。不要内联定义组件。 |
| Tabs | 容器组件 | 选项卡 | tabs | array | 对象数组，其中每个对象定义一个带有标题和子组件的标签页。 |
| Video | 高级组件 | 视频播放器 | url | string | 要显示的视频 URL。 |
| AudioPlayer | 高级组件 | 音频播放器 | url | string | 要播放的音频 URL。 |
| | | | description | string | 音频的描述，如标题或摘要。 |

以上所有组件公共属性：

1. id： 必选，surface范围内唯一的组件ID
2. accessibility：无障碍属性
3. weight：自适应布局扩展权重，在Row或者Column布局组件中生效

#### 4.1.2 扩展组件

以下组件如无特殊说明除了协议中定义的id和component字段外，均还包含styles和listeners两个公共属性，styles的详细内容参见：样式；listeners的详细内容参见：交互；

| 名称 | 类型 | 说明 | 属性 | 类型 | 说明 |
|------|------|------|------|------|------|
| Extended.Text | 展示组件 | 用于显示普通文本内容，支持字体、颜色、样式等设置。 | content | string | 要显示的文本内容 |
| Extended.Button | 交互组件 | 按钮组件，响应用户点击操作，常用于触发事件。 | label | string | 按钮中的文本 |
| | | | enabled | boolean | 按钮是否可点击 |
| Extended.TextInput | 交互组件 | 文本输入框，用于接收用户输入的文字内容。 | text | String | 默认文本内容 |
| | | | placeholder | String | 单行文本输入框的默认提示文本内容属性 |
| | | | enabled | boolean | 是否禁用 |
| | | | maxLength | number | 最大输入字符数 |
| | | | type | number | 输入框类型，字符串枚举值；<br>"normal":基本输入模式，无特殊限制。<br>"number":纯数字输入模式，不支持负数、小数<br>"phoneNumber":电话号码输入模式,支持输入数字、空格、+、-、*、#、(、)、长度不限<br>"email":邮箱地址输入模式，支持数字、字母、下划线、小数点、!、#、$、%、&、'、"、*、+、-、/、=、?、^、`、{、|、}、~，以及@字符（只能存在一个@字符）<br>"password":密码输入模式，默认输入文字短暂显示后变成圆点。在已启用密码保险箱的情况下，支持用户名、密码的自动保存和自动填充<br>"numberPassword":纯数字密码输入模式。默认输入文字短暂显示后变成圆点。密码输入模式不支持下划线样式。在已启用密码保险箱的情况下，支持用户名、密码的自动保存和自动填充<br>"userName":用户名输入模式，无特殊限制。在已启用密码保险箱的情况下，支持用户名、密码的自动保存和自动填充<br>"newPassword":新密码输入模式，无特殊限制。默认输入文字短暂显示后变成圆点。在已启用密码保险箱的情况下，支持用户名、密码的自动保存和自动填充<br>"numberDecimal":带小数点的数字输入模式。支持数字，小数点（只能存在一个小数点）。不支持负数小数<br>"url":带URL的输入模式，无特殊限制 |
| Extended.Row | 布局组件 | 水平方向线性布局，将子组件沿水平方向排列。 | children | List[String] 或者 object { componentId: string, path: string } | 子组件ID列表 或者 模板组件ID和循环数据路径 |
| | | | space | number | 横向布局元素水平方向间距。space为负数或者justifyContent设置为"spaceBetween"、"spaceAround"、"spaceEvenly"时，space不生效。默认值：0，非法值：按默认值处理。单位：vp |
| Extended.Column | 布局组件 | 垂直方向线性布局，将子组件沿垂直方向排列。 | children | List[String] 或者 object { componentId: string, path: string } | 子组件ID列表 或者 模板组件ID和循环数据路径 |
| | | | space | number | 纵向布局元素垂直方向间距。space为负数或者justifyContent设置为"spaceBetween"、"spaceAround"、"spaceEvenly"时，space不生效。默认值：0，非法值：按默认值处理。单位：vp |
| Extended.List | 布局组件 | 列表组件，高效展示滚动列表项，支持大量数据。 | children | List[String]或object { componentId: string, path: string } | 子节点的ID列表或者模板组件ID和循环数据路径。 |
| | | | space | Number | 子组件主轴方向的间隔。默认值：0<br><br>参数类型为number时单位为vp。设置为负数或者大于等于List内容区长度时，按默认值显示。space参数值小于List分割线宽度时，子组件主轴方向的间隔取分割线宽度。List子组件的visibility属性设置为None时不显示，但该子组件上下的space还是会生效。 |
| Extended.Stack | 布局组件 | 堆叠布局，子组件按顺序叠放，后添加的在上层。 | children | List[String] | 子组件ID列表 |
| Extended.Grid | 布局组件 | 网格布局，以行列方式排列子组件。 | children | List[String] 或者 object { componentId: string, path: string } | 子组件ID列表 或者 模板组件ID和循环数据路径 |
| Extended.GridRow | 布局组件 | 网格行组件，通常配合Grid使用，定义网格中的一行布局。 | children | List[String] 或者 object { componentId: string, path: string } | 子组件ID列表 或者 模板组件ID和循环数据路径 |
| Extended.Image | 展示组件 | 用于展示图片，支持本地、网络或资源图片。 | src | String | 图片数据源（本地或网络） |
| Extended.Divider | 展示组件 | 分割线组件，用于在视觉上分隔不同内容区域。 |
| Extended.Toggle | 交互组件 | 开关组件，用于表示或切换两种状态（如开/关）。 | isOn | boolean | 开关是否打开 |
| | | | enabled | boolean | 是否可以切换状态 |
| Extended.Progress | 展示组件 | 进度条组件，用于显示任务完成进度或加载状态。 | value | number | 当前进度值 |
| | | | total | number | 进度总长 |
| Extended.Radio | 交互组件 | 单选框，提供相应的用户交互选择项。 | value | string | 当前单选框的值 |
| | | | checked | boolean | 设置单选框的选中状态。 |
| | | | group | string | 当前单选框的所属群组名称，相同group的Radio只能有一个被选中。 |
| | | | indicatorType | 字符串枚举值<br>"tick":系统默认TICK图标<br>"dot":系统默认DOT图标 | 配置单选框的选中样式。未设置时按照RadioIndicatorType.TICK进行显示。 |
| Extended.Checkbox | 交互组件 | 提供多选框组件，通常用于某选项的打开或关闭。 | group | string | 用于指定多选框所属群组的名称（即所属CheckboxGroup的名称）。默认值：undefined，默认状态下配合CheckboxGroupOptions属性group信息为undefined的节点使用。<br>未配合使用CheckboxGroup组件时，此值无用。 |
| | | | select | boolean | 设置多选框选中状态 |
| Extended.CheckboxGroup | 交互组件 | 多选框群组，用于控制多选框全选或者不全选状态。 | group | string | 群组名称。默认值：undefined，默认状态下管理CheckboxOptions属性group信息为undefined的节点。具有相同群组名称的多个CheckboxGroup，仅第一个CheckboxGroup生效。 |
| | | | selectAll | boolean | 设置是否全选。若同组的Checkbox显式设置了select属性，则Checkbox的优先级高。 |
| Extended.If | 条件组件 | 条件语法组件，通过条件判断挂载不同的组件分支。 | condition | boolean | 分支判断条件，为true时挂载if分支，为false时挂载else分支。 |
| | | | childrenIf | List[String] | 条件为true时挂载的分支所包含的子节点ID数组，对应if分支。 |
| | | | childrenElse | List[String] | 条件为false时挂载的分支所包含的子节点ID数组，对应else分支。 |
| Extended.Tabs | 容器组件 | 通过页签进行内容视图切换的容器组件，每个页签对应一个内容视图。 | barPosition | 字符串枚举值 | 设置Tabs的页签位置。默认值：start。<br>• "start": vertical属性方法设置为true时，页签位于容器左侧；vertical属性方法设置为false时，页签位于容器顶部。<br>• "end": vertical属性方法设置为true时，页签位于容器右侧；vertical属性方法设置为false时，页签位于容器底部。 |
| | | | children | List[String] 或者 object { componentId: string, path: string } | 子组件ID列表 或者 模板组件ID和循环数据路径。子组件类型必须是Extended.TabContent |
| | | | vertical | boolean | 是否为纵向Tab。默认值：false，横向Tabs，为true时纵向Tabs。 |
| | | | scrollable | boolean | 是否可以通过滑动页面进行页面切换。true为可以通过，false为不可以。 |
| | | | tabIndex | number | 当前显示页签的索引。默认值：0 |
| Extended.TabContent | 容器组件 | 仅在Extended.Tabs组件中使用，对应一个页签的内容容器 | title | string | Tab页导航条的标题。 |
| | | | icon | string | Tab页导航条的图标 |
| | | | selectedSrc | string | 当前tab选中之后的图标内容 |
| | | | tabType | string | 每个tab的样式，capsule：胶囊状，underline：下划线状 |
| Extended.Select | 交互容器 | 下拉选择菜单，让用户在多个选项间选择。 | options | List\<object>。object格式 { value, icon, symbolIcon }<br>• value: string，下拉选项的内容<br>• icon: string, 下拉选项的图片<br>• symbolIcon: object，下拉选项Symbol图片，优先级高于icon，格式为 {src, fontSize, fontWeight,fontColor,renderingStrategy,effectStrategy}<br>  - src: string，图标<br>  - fontSize：数值，单位fp，字体大小<br>  - fontWeight:数值，字体权重<br>  - fontColor：16进制字符串，字体颜色<br>  - renderingStrategy：字符串枚举值<br>&emsp;    - single：单色模式，默认值。可以设置一个或者多个颜色，默认为黑色。当设置多个颜色时，仅生效第一个颜色。<br>&emsp;    - multipleColor：多色模式。最多可以设置三个颜色。当只设置一个颜色时，修改symbol图标的第一层颜色，其他颜色保持默认颜色。颜色设置顺序与图标分层顺序匹配，当颜色数量大于图标分层时，多余的颜色不生效。仅支持设置颜色，设置透明度设置不生效。<br>&emsp;    - multipleOpacity：分层模式。默认为黑色，可以设置一个或者多个颜色。当设置多个颜色时，仅生效第一个颜色。不透明度与图层相关，symbol图标的第一层透明度为100%、第二层透明度为50%、第三层透明度为20%。<br>  - effectStrategy：动效策略，字符串枚举值<br>&emsp;    - none：无动效，默认值<br>&emsp;    - scale：整体缩放动效<br>&emsp;    - hierarchical：层级动效<br>  | 下拉菜单项的信息。例如：`{ "value": "option-1", "icon": "https://y.qq.com/music/photo_new/T002R300x300M000000KrDC019mc82_3.jpg?max_age=2592000", "symbolIcon": { "value": "sys.symbol.ohos_wifi", "fontSize": 20, "fontColor": "#FF11BF82", "fontWeight": 6, "renderingStrategy": 1, "effectStrategy": 1 } }` |
| | | | selected | number | 设置下拉菜单初始选项的索引 |
| | | | value | string | 设置下拉按钮的文本内容。选中菜单项后，按钮文本将自动更新为选中的菜单项文本。 |
| Extended.Web | 容器组件 | 渲染HTML网页内容 | url | string | web组件的地址 |
| Extended.Navigation | 布局组件 | 导航组件，支持配置多卡片及卡片间跳转 | children | List[String] | 子组件ID列表 |
| | | | currentIndex | number | 当前显示的卡片下标 |
| | | | title | string | 页面标题 |


### 4.2 样式

#### 4.2.1 组件公共样式

| 名称 | 样式说明 | 类型 | 必选 | 使用示例 |
|------|----------|------|------|----------|
| backgroundImageSizeWithStyle | 设置组件背景图片的宽度和高度。 | 字符串枚举值或对象，默认值为"auto"。<br>字符串枚举值：<br>"cover":保持宽高比进行缩小或者放大，使得图片两边都大于或等于显示边界<br>"contain":保持宽高比进行缩小或者放大，使得图片完全显示在显示边界内<br>"auto":保持原图的比例不变<br>"fill":不保持宽高比进行放大缩小，使得图片充满显示边界<br><br>对象：{width， height}，两个属性都是必选，类型为数值或者字符串。<br>数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "backgroundImageSizeWithStyle": "contain" |
| flexShrink | 设置父容器压缩尺寸分配给此属性所在组件的比例。当父容器为Column、Row时，需设置主轴方向的尺寸。 | 数值，范围[0, 1] | 否 | "flexShrink": 1 |
| width | 设置组件宽度 | 数值：[0,inf)<br>默认单位vp<br><br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%"<br><br>枚举值：<br>"matchParent"：当前组件自适应父组件布局时，其大小与父组件内容区相等，不包括padding和border<br>"wrapContent"：当前组件自适应子组件（内容）时，其大小与子组件（内容）相等，并且其大小受父组件内容区大小约束<br>"fixAtIdealSize"：当前组件自适应子组件（内容）时，其大小与子组件（内容）相等，并且其大小不受父组件内容区大小约束 | 否 | "width": 100 |
| height | 设置组件高度 | 数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%"<br>枚举值：<br>"matchParent"：当前组件自适应父组件布局时，其大小与父组件内容区相等，不包括padding和border<br>"wrapContent"：当前组件自适应子组件（内容）时，其大小与子组件（内容）相等，并且其大小受父组件内容区大小约束<br>"fixAtIdealSize"：当前组件自适应子组件（内容）时，其大小与子组件（内容）相等，并且其大小不受父组件内容区大小约束 | 否 | "height": "100vp" |
| constraintSize | 设置约束尺寸，组件布局时，进行尺寸范围限制。 | 对象：{minWidth, maxWidth, minHeight, maxHeight}，四个属性分别是宽度和高度的最大最小值，都是必选，类型为数值或者字符串。<br>数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "constraintSize": { "minWidth": 10, "maxWidth": 100, "minHeight": 10, "maxHeight": 100 } |
| backgroundImage | 设置组件的背景图片路径 | 字符串，图片路径 | 否 | "backgroundImage": "https://example.com/bg.png" |
| margin | 外间距，支持数字（统一边距）或对象{top, right, bottom, left}（分别设置四边） | 数值：[0,inf)<br>默认单位vp<br>对象：四个属性都是可选，类型为数值或者字符串。<br>数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "margin": { "left": 4, "top": "4vp", "right": "4%" } |
| borderRadius | 4边角半径，支持数字（统一半径）或对象{topLeft, topRight, bottomLeft, bottomRight}（分别设置四角） | 数值：[0,inf)<br>默认单位vp<br>对象：四个属性都是可选，类型为数值或者字符串。<br>数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "borderRadius": 8 |
| visibility | 是否可见 | 枚举值字符串，<br>"visible"：可见<br>"hidden"：不可见但占位<br>"none"：不可见也不占位 | 否 | "visibility": "visible" |
| clip | 是否根据父组件边界进行裁切，true/false | 布尔值 | 否 | "clip": true |
| backgroundColor | 颜色值，0xARGB 格式的16进制表示 | 字符串 | 否 | "backgroundColor": "#00FF0000" |
| borderWidth | 边框宽度，支持数值/字符串 | 数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "borderWidth": 1 |
| borderColor | 边框颜色，0xARGB 格式的16进制表示 | 字符串 | 否 | "borderColor": "#00000000" |
| padding | 内边距，支持数字（统一边距）或对象（分别设置四边） | 数值：[0,inf)<br>默认单位vp<br>对象：四个属性都是可选，类型为数值或者字符串。<br>数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "padding": { "left": 8, "top": "8vp", "right": "8%" } |
| layoutWeight | 布局权重，仅当父节点为Row和Column时生效 | 数值，默认值为1 | 否 | "layoutWeight": 2 |
| shadow | 阴影效果，对象或者字符串枚举值 | 对象 { offsetX, offsetY, radius, color, fill, type};<br>offsetX:可选，数值，阴影的X轴偏移量。默认值：0，单位：vp<br><br>offsetY:可选，数值，阴影的Y轴偏移量。默认值：0，单位：vp<br><br>radius:必选，数值，阴影模糊半径。取值范围：[0, +∞)。单位：vp。设置小于0的值时，按值为0处理。<br><br>color:可选，16进制字符串，阴影的颜色。默认为黑色。<br><br>fill:可选，布尔，阴影是否内部填充。true表示阴影在内部填充，false表示阴影在外部填充。默认值：false。<br><br>type:可选,字符串枚举值，阴影类型。默认值："color"。<br>"color":颜色<br>"blur":模糊<br><br>字符串枚举值：<br>"outerDefaultXS":超小阴影<br>"outerDefaultSM":小阴影<br>"outerDefaultMD":中阴影<br>"outerDefaultLG":大阴影<br>"outerFloatingSM":浮动小阴影<br>"outerFloatingMD":浮动中阴影。 | 否 | "shadow": { "offsetX": 2, "offsetY": 2, "radius": 4, "color": "#66000000" } |

#### 4.2.2 组件特有样式

##### Extended.Text

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| textOverflow | 文本超长时的显示方式，需配合maxLines使用 | 字符串枚举值<br>"none"：文本超长时按最大行截断显示<br>"clip"：文本超长时按最大行截断显示<br>"ellipsis"：文本超长时显示不下的文本用省略号代替<br>"marquee"：文本在一行内滚动显示 | 否 | "textOverflow": "ellipsis" |
| decoration | 设置文本装饰线样式及其颜色 | 对象 { type, style, color, thicknessScale }<br>type：装饰线类型，字符串枚举值("none":不使用文本装饰线,"underline":文字下划线修饰,"overline":文字上划线修饰,"lineThrough":穿过文本的修饰线)<br>color:装饰线颜色,字符串类型（16进制）<br>style:装饰线样式,字符串枚举值("solid":单实线,默认值,"doubleE":双实线,"dotted":点线,"dashed":虚线,"wavy":波浪线) | 否 | "decoration": { "type": "underline", "color": "#ff007dff", "style": "solid" } |
| fontSize | 设置字体大小，默认16 fp | 数字，单位为fp | 否 | "fontSize": 18 |
| fontWeight | 文本的字体粗细 | 数字 | 否 | "fontWeight": 500 |
| fontColor | 字体颜色 | 字符串（16进制） | 否 | "fontColor": "#333333" |
| textAlign | 水平对齐方式 | 字符串枚举值 ("start":水平对齐首部,"center":水平居中对齐,"end":水平对齐尾部,"justify": 双端对齐) | 否 | "textAlign": "center" |
| maxLines | 文本最大行数 | 数字 | 否 | "maxLines": 2 |
| wordBreak | 文本断行规则 | 字符串枚举值 "normal"：CJK(中文、日文、韩文)文本可以在任意2个字符间断行，而Non-CJK文本（如英文等）只能在空白符处断行。"breakAll"：对于Non-CJK的文本，可在任意2个字符间断行。对于CJK文本，效果与NORMAL一致。<br>"breakWord"：与breakAll相同，对于Non-CJK的文本可在任意2个字符间断行，一行文本中有断行破发点（如空白符）时，优先按破发点换行，保障单词优先完整显示。若整一行文本均无断行破发点，则在任意2个字符间断行。对于CJK文本，效果与normal一致。"hyphenation"：每行末尾单词尝试通过连字符"-"进行断行，若无法添加连字符"-"，则跟breakWord保持一致。 | 否 | "wordBreak": "breakWord" |
| maxFontSize | 文本最大显示大小 | 数字，单位 fp | 否 | "maxFontSize": 24 |
| fontScaleMode | 字体缩放模式 | 字符串枚举值，"followSystem":跟随系统,"custom":不跟随系统，使用自定义的值。 | 否 | "fontScaleMode": "followSystem" |
| minFontScale | 最小字体缩放比例 | 数字 | 否 | "minFontScale": 0.8 |
| maxFontScale | 最大字体缩放比例 | 数字 | 否 | "maxFontScale": 1.5 |

##### Extended.Button

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| fontSize | 设置字体大小，默认16 fp | 数字，单位为fp | 否 | "fontSize": 16 |
| fontWeight | 文本的字体粗细 | 数字<br>或枚举值"lighter":100字重，字体较细<br>"mormal":400字重，字体粗细正常<br>"regular":400字重，字体粗细正常，与normal效果相同<br>"medium":500字重，字体粗细适中<br>"bold":700字重，字体较粗<br>"bolder":900字重，字体非常粗 | 否 | "fontWeight": 600 |
| maxFontSize | 文本最大显示大小 | 数字，单位 fp | 否 | "maxFontSize": 20 |
| fontScaleMode | 字体缩放模式 | 字符串枚举值，"followSystem":跟随系统,"custom":不跟随系统，使用自定义的值。 | 否 | "fontScaleMode": "followSystem" |
| minFontScale | 最小字体缩放比例 | 数字 | 否 | "minFontScale": 0.8 |
| maxFontScale | 最大字体缩放比例 | 数字 | 否 | "maxFontScale": 1.5 |

##### Extended.TextInput

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| placeholderColor | placeholder文本颜色 | 字符串（16进制） | 否 | "placeholderColor": "#999999" |
| cancelButton | 设置右侧清除按钮样式 | 对象{style,fontColor, fontSize}，三个属性都是可选。<br>"style":字符串枚举值，（constant：清除按钮常显样式；invisible：清除按钮常隐样式；input：清除按钮输入样式）<br>"fontColor"：16进制字符串<br>"fontSize"：数值，默认单位fp | 否 | "cancelButton": { "style": "constant", "fontColor": "#aeaeae", "fontSize": 16 } |
| caretColor | 光标颜色 | 字符串（16进制） | 否 | "caretColor": "#007AFF" |
| selectedBackgroundColor | 文本选中底板颜色（默认20%不透明度） | 字符串（16进制） | 否 | "selectedBackgroundColor": "#33007AFF" |
| showUnderline | 是否开启下划线 | 布尔值，true表示开启，false表示不开启。<br>默认值：false | 否 | "showUnderline": true |
| underlineColor | 设置下划线颜色 | object {typing, normal,error,disable}，四个属性都是可选，类型都是表示颜色的16进制字符串。<br>"typing": 键入时下划线颜色<br>"normal":非特殊状态时下划线颜色<br>"error":错误时下划线颜色<br>"disable":禁用时下划线颜色 | 否 | "underlineColor": {<br>"typing": "#FF4256C1",<br>"normal": "#FF4256C1",<br>"error": "#FF4256C1",<br>"disable": "#FF4256C1"<br>} |
| fontSize | 设置字体大小，默认16 fp | 数字，单位为fp | 否 | "fontSize": 16 |
| fontWeight | 字体粗细 | 数字或字符串枚举值<br>"lighter":100字重，字体较细<br>"normal":400字重，字体粗细正常<br>"regular":400字重，字体粗细正常，与normal效果相同<br>"medium":500字重，字体粗细适中<br>"bold":700字重，字体较粗<br>"bolder":900字重，字体非常粗 | 否 | "fontWeight": 400 |
| fontColor | 字体颜色 | 字符串（16进制） | 否 | "fontColor": "#000000" |
| textAlign | 水平对齐方式 | 字符串枚举值 ("start":水平对齐首部,"center":水平居中对齐,"end":水平对齐尾部,"justify": 双端对齐) | 否 | "textAlign": "start" |
| maxFontSize | 文本最大显示大小 | 数字，单位 fp | 否 | "maxFontSize": 18 |
| wordBreak | 文本断行规则 | 字符串枚举值 "normal"：CJK(中文、日文、韩文)文本可以在任意2个字符间断行，而Non-CJK文本（如英文等）只能在空白符处断行。"breakAll"：对于Non-CJK的文本，可在任意2个字符间断行。对于CJK文本，效果与NORMAL一致。<br>"breakWord"：与breakAll相同，对于Non-CJK的文本可在任意2个字符间断行，一行文本中有断行破发点（如空白符）时，优先按破发点换行，保障单词优先完整显示。若整一行文本均无断行破发点，则在任意2个字符间断行。对于CJK文本，效果与normal一致。"hyphenation"：每行末尾单词尝试通过连字符"-"进行断行，若无法添加连字符"-"，则跟breakWord保持一致。 | 否 | "wordBreak": "normal" |
| maxLines | 文本最大行数 | 数字 | 否 | "maxLines": 3 |
| fontScaleMode | 字体缩放模式 | 字符串枚举值，"followSystem":跟随系统,"custom":不跟随系统，使用自定义的值。 | 否 | "fontScaleMode": "followSystem" |
| minFontScale | 最小字体缩放比例 | 数字 | 否 | "minFontScale": 0.8 |
| maxFontScale | 最大字体缩放比例 | 数字 | 否 | "maxFontScale": 1.5 |

##### Extended.Row

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| justifyContent | 水平方向对齐格式 | 字符串枚举值 "start"：元素在主轴方向首端对齐，第一个元素与行首对齐，后续元素与前一个对齐<br>"center"：元素在主轴方向中心对齐，第一个元素与行首的距离和最后一个元素与行尾的距离相同<br>"end"：元素在主轴方向尾部对齐，最后一个元素与行尾对齐，其余元素与后一个对齐<br>"spaceBetween"：Flex主轴方向均匀分配弹性元素，相邻元素之间距离相同。第一个元素与行首对齐，最后一个元素与行尾对齐<br>"spaceAround"：Flex主轴方向均匀分配弹性元素，相邻元素之间距离相同。第一个元素到行首的距离和最后一个元素到行尾的距离是相邻元素之间距离的一半<br>"spaceEvenly"：Flex主轴方向均匀分配弹性元素，相邻元素之间的距离、第一个元素与行首的间距、最后一个元素到行尾的间距均相同 | 否 | "justifyContent": "spaceBetween" |
| alignItems | 垂直方向对齐格式 | 字符串枚举值<br>"top"：顶部对齐<br>"center"：居中对齐，默认对齐方式<br>"bottom"：底部对齐 | 否 | "alignItems": "center" |

##### Extended.Column

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| justifyContent | 垂直方向对齐格式 | 字符串枚举值 "start"：元素在主轴方向首端对齐，第一个元素与行首对齐，后续元素与前一个对齐<br>"center"：元素在主轴方向中心对齐，第一个元素与行首的距离和最后一个元素与行尾的距离相同<br>"end"：元素在主轴方向尾部对齐，最后一个元素与行尾对齐，其余元素与后一个对齐<br>"spaceBetween"：Flex主轴方向均匀分配弹性元素，相邻元素之间距离相同。第一个元素与行首对齐，最后一个元素与行尾对齐<br>"spaceAround"：Flex主轴方向均匀分配弹性元素，相邻元素之间距离相同。第一个元素到行首的距离和最后一个元素到行尾的距离是相邻元素之间距离的一半<br>"spaceEvenly"：Flex主轴方向均匀分配弹性元素，相邻元素之间的距离、第一个元素与行首的间距、最后一个元素到行尾的间距均相同 | 否 | "justifyContent": "spaceBetween" |
| alignItems | 水平方向对齐格式 | 字符串枚举值<br>"top"：顶部对齐<br>"center"：居中对齐，默认对齐方式<br>"bottom"：底部对齐。 | 否 | "alignItems": "center" |

##### Extended.List

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| listDirection | 列表排列方向 | 字符串枚举值 "vertical":方向为纵向<br>"horizontal":方向为横向 | 否 | "listDirection": "vertical" |
| scrollBar | 滚动条状态 | 字符串枚举值<br>"off"：不显示<br>"auto"：按需显示(触摸时显示，2s后消失)<br>"on"：常驻显示 | 是 | "scrollBar": "auto" |
| nestedScroll | 嵌套滚动模式 | 字符串枚举值 "scrollForward"：滚动组件往末尾端滚动时的嵌套滚动选项<br>"scrollBackward"：滚动组件往起始端滚动时的嵌套滚动选项 | 否 | "nestedScroll": "scrollForward" |

##### Extended.Stack

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| alignContent | 子组件对齐方式 | 字符串枚举值 "topStart"：顶部起始端<br>"top"：顶部横向居中<br>"topEnd"：顶部尾端<br>"start"：起始端纵向居中<br>"center"：横向和纵向居中<br>"end"：尾端纵向居中<br>"bottomStart"：底部起始端<br>"bottom"：底部横向居中<br>"bottomEnd"：底部尾端 | 否 | "alignContent": "center" |

##### Extended.Grid

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| columnsTemplate | 列的数量、固定列宽 | 字符串，仅支持传入"1fr 1fr 2fr"形式的字符串，每个fr代表一列，前面的数值是该列的宽度权重。 | 否 | "columnsTemplate": "1fr 2fr 1fr" |
| rowsTemplate | 行的数量、固定行高 | 字符串，仅支持传入"1fr 1fr 2fr"形式的字符串，每个fr代表一行，前面的数值是该行的高度权重。 | 否 | "rowsTemplate": "1fr 1fr 2fr" |
| columnsGap | 列间距 | 数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "columnsGap": 12 |
| rowsGap | 行间距 | 数值：[0,inf)<br>默认单位vp<br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "rowsGap": 12 |

##### Extended.Image

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| aspectRatio | 宽高比 (width/height) | 数字，指定当前组件的宽高比，aspectRatio=width/height。仅设置width、aspectRatio时，height = width/aspectRatio。<br>仅设置height、aspectRatio时，width = height * aspectRatio。<br>同时设置width、height和aspectRatio时，height不生效，height = width / aspectRatio。<br>设置aspectRatio属性后，组件宽高会受父组件内容区大小限制，constraintSize的优先级高于aspectRatio。 | 否 | "aspectRatio": 1.5 |
| objectFit | 图片填充效果 | 字符串枚举值<br>"fill"：不保持宽高比进行放大缩小，使得图片或视频充满显示边界，对齐方式为水平居中<br>"contain"：保持宽高比进行缩小或者放大，使得图片或视频完全显示在显示边界内，对齐方式为水平居中<br>"cover"：保持宽高比进行缩小或者放大，使得图片或视频两边都大于或等于显示边界，对齐方式为水平居中<br>"auto"：图片或视频会根据其自身尺寸和组件的尺寸进行适当缩放，以在保持比例的同时填充视图，对齐方式为水平居中<br>"none"：保持原有尺寸进行显示，对齐方式为水平居中<br>"scaleDown"：保持宽高比进行显示，图片或视频缩小或者保持不变，对齐方式为水平居中<br>"topStart"：图片或视频显示在组件的顶部起始端，且保持原有尺寸<br>"top"：图片或视频显示在组件的顶部横向居中，且保持原有尺寸<br>"topEnd"：图片或视频显示在组件的顶部尾端，且保持原有尺寸。<br>"start"：图片或视频显示在组件的起始端纵向居中，且保持原有尺寸<br>"center"：图片或视频显示在组件的横向和纵向居中，且保持原有尺寸<br>"end"：图片或视频显示在组件的尾端纵向居中，且保持原有尺寸<br>"bottomStart"：图片或视频显示在组件的底部起始端，且保持原有尺寸<br>"bottom"：图片或视频显示在组件的底部横向居中，且保持原有尺寸<br>"bottomEnd"：图片或视频显示在组件的底部尾端，且保持原有尺寸<br>"matrix"：配合imageMatrix使用，使图像在Image组件自定义位置显示，且保持原有尺寸。不支持svg图源 | 否 | "objectFit": 1 |

##### Extended.Divider

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| strokeWidth | 分割线宽度 | 数值：[0,inf)默认单位vp<br><br>字符串：<br>数值+单位（"100fp"）<br>单位："fp"、"vp"、"%" | 否 | "strokeWidth": 1 |
| vertical | 分割线方向 | 布尔值 (false:水平; true:垂直) | 否 | "vertical": false |
| color | 分割线颜色 | 字符串(16进制) | 否 | "color": "#E0E0E0" |

##### Extended.Toggle

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| selectedColor | 打开状态背景颜色 | 16进制字符串 | 否 | "selectedColor": "#34C759" |
| unSelectedColor | 关闭状态背景颜色 | 16进制字符串 | 否 | "unSelectedColor": "#E5E5EA" |
| switchPointColor | 圆形滑块颜色 | 16进制字符串 | 否 | "switchPointColor": "#FFFFFF" |

##### Extended.Progress

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| color | 进度条前景色 | 16进制字符串 | 否 | "color": "#007AFF" |
| type | 进度条类型 | 字符串枚举值<br>"linear":线性样式<br>"ring":环形无刻度样式，环形圆环逐渐显示直至完全填充<br>"eclipse":圆形样式，显示类似月圆月缺的进度展示效果，从月牙逐渐变化至满月<br>"scaleRing":环形有刻度样式，显示类似时钟刻度形式的进度展示效果<br>"capsule":胶囊样式，头尾两端圆弧处的进度展示效果与Eclipse相同，中段的进度展示效果与Linear相同。当高度大于宽度时，自适应垂直显示。 | 否 | "type": "Ring" |

##### Extended.Radio

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| checkedBackgroundColor | 选中状态底板颜色 | 16进制字符串 | 否 | "checkedBackgroundColor": "#FFAAFF" |
| uncheckedBorderColor | 未选中状态描边颜色 | 16进制字符串 | 否 | "uncheckedBorderColor": "#FFAAFF" |
| indicatorColor | 选中状态内部圆饼颜色 | 16进制字符串 | 否 | "indicatorColor": "#FFAAFF" |

##### Extended.Checkbox

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| selectedColor | 设置多选框选中状态颜色。 | 16进制字符串 | 否 | "selectedColor": "#FFAAFF" |
| unselectedColor | 设置多选框非选中状态颜色。 | 16进制字符串 | 否 | "unselectedColor": "#FFAAFF" |
| mark | 设置多选框内部图标的样式。 | 对象{ strokeColor, size, strokeWidth }<br>三个属性都是可选。<br>strokeColor: 16进制字符串，内部图标颜色<br>size: 数值，内部图标大小，单位vp，默认大小与多选框组件宽度相同。<br>strokeWidth：数值，内部图标粗细，单位vp。 | 否 | "mark": {<br>"strokeColor": "#FFABCD", "size": 20, "strokeWidth": 2 } |
| shape | 设置Checkbox组件形状，包括圆形和圆角方形。 | 字符串枚举值<br>"circle": 圆形，默认值<br>"rounded_square": 圆角方形 | 否 | "shape": "circle" |

##### Extended.CheckboxGroup

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| selectedColor | 设置被选中或部分选中状态的颜色。 | 16进制字符串 | 否 | "selectedColor": "#FFAAFF" |
| unselectedColor | 设置非选中状态颜色。 | 16进制字符串 | 否 | "unselectedColor": "#FFAAFF" |
| mark | 设置多选框内部图标的样式。 | 对象{ strokeColor, size, strokeWidth }<br>三个属性都是可选。<br>strokeColor: 16进制字符串，内部图标颜色<br>size: 数值，内部图标大小，单位vp，默认大小与多选框组件宽度相同。<br>strokeWidth：数值，内部图标粗细，单位vp。 | 否 | "mark": {<br>"strokeColor": "#FFABCD", "size": 20, "strokeWidth": 2 } |
| checkboxShape | 设置CheckboxGroup组件形状，包括圆形和圆角方形。 | 字符串枚举值，<br>"circle": 圆形，默认值<br>"rounded_square": 圆角方形<br><br>CheckboxGroup组件将按照设置的形状显示。CheckboxGroup内所有未单独设置shape类型的Checkbox，其形状将与CheckboxGroup保持一致。CheckboxGroup内已单独设置shape类型的Checkbox，其形状将优先于CheckboxGroup的设置，按照自身设置显示。 | 否 | "checkboxShape": "circle" |

##### Extended.TabContent

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| selectColor | 当前选中tab的标题颜色 | 16进制字符串 | 否 | `"selectColor": "#FFABCD"` |
| unselectedColor | 默认的标题颜色 | 16进制字符串 | 否 | `"unselectedColor": "#FFABCD"` |
| defaultBackgroundColor | 默认的tab背景色 | 16进制字符串 | 否 | `"defaultBackgroundColor": "#FFABCD"` |
| selectBackgroundColor | 当前选中的tab背景色 | 16进制字符串 | 否 | `"selectBackgroundColor": "#FFABCD"` |
| defaultBorderColor | tab边框颜色 | 16进制字符串 | 否 | `"defaultBorderColor": "#FFABCD"` |
| selectBorderColor | 选中的tab边框颜色 | 16进制字符串 | 否 | `"selectBorderColor": "#FFABCD"` |
| fontSize | tab标题文字大小 | number 单位fp | 否 | `"fontSize": 18` |
| fontWeight | tab标字体粗细 | 数字或字符串枚举值<br>• "lighter": 100字重，字体较细<br>• "normal": 400字重，字体粗细正常<br>• "regular": 400字重，字体粗细正常，与normal效果相同<br>• "medium": 500字重，字体粗细适中<br>• "bold": 700字重，字体较粗<br>• "bolder": 900字重，字体非常粗 | 否 | `"fontWeight": 16` |
| iconSize | tab图标的大小 | number 单位vp | 否 | `"iconSize": 18` |
| space | 标题和图标之间的间距 | number 单位vp | 否 | `"space": 5` |

##### Extended.Select

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| divider | 设置的分割线样式 | Object {<br>• strokeWidth：线宽，数值，单位为vp<br>• startMargin：分割线与侧边起始端的距离，数值，单位为vp<br>• endMargin：分割线与侧边结束端的距离，数值，单位为vp<br>• color：颜色，16进制字符串<br>} | 否 | `{ "strokeWidth": 3, "startMargin": 2, "endMargin": 2, "color": "#FFBC7A33" }` |
| font | 设置文本样式 | object：{<br>• size：文本尺寸，数值，单位为fp<br>• weight：文本的字体粗细<br>• family：文本的字体列表，字符串，使用多个字体，使用','进行分割，优先级按顺序生效。例如：'Arial, HarmonyOS Sans'<br>• style：文本的字体样式，字符串枚举值<br>  - "normal": 标准字体样式，默认值<br>  - "italic": 斜体的字体样式<br>} | 否 | `{ "size": 20, "weight": 6, "family": "HarmonyOS Sans", "style": "normal" }` |
| fontColor | 设置下拉按钮本身的文本颜色 | 16进制字符串 | 否 | `{ "fontColor": "#BC7A33" }` |
| selectedOptionBgColor | 下拉菜单选中项的背景色 | 16进制字符串 | 否 | `{ "selectedOptionBgColor": "#BC7A33" }` |
| selectedOptionFont | 设置下拉菜单选中项的文本样式 | object：{<br>• size：文本尺寸，数值，单位为fp<br>• weight：文本的字体粗细<br>• family：文本的字体列表，字符串，使用多个字体，使用','进行分割，优先级按顺序生效。例如：'Arial, HarmonyOS Sans'<br>• style：文本的字体样式，字符串枚举值<br>  - "normal": 标准字体样式，默认值<br>  - "italic": 斜体的字体样式<br>} | 否 | `{ "size": 20, "weight": 6, "family": "HarmonyOS Sans", "style": "normal" }` |
| selectedOptionFontColor | 设置下拉菜单选中项的文本颜色 | 16进制字符串 | 否 | `{ "selectedOptionFontColor": "#BC7A33" }` |
| optionBgColor | 设置下拉菜单项的背景色 | 16进制字符串 | 否 | `{ "optionBgColor": "#BC7A33" }` |
| optionFont | 设置下拉菜单项的文本样式 | object：{<br>• size：文本尺寸，数值，单位为fp<br>• weight：文本的字体粗细<br>• family：文本的字体列表，字符串，使用多个字体，使用','进行分割，优先级按顺序生效。例如：'Arial, HarmonyOS Sans'<br>• style：文本的字体样式，字符串枚举值<br>  - "normal": 标准字体样式，默认值<br>  - "italic": 斜体的字体样式<br>} | 否 | `{ "size": 20, "weight": 6, "family": "HarmonyOS Sans", "style": "normal" }` |
| optionFontColor | 设置下拉菜单项的文本颜色 | 16进制字符串 | 否 | `{ "optionFontColor": "#BC7A33" }` |
| space | 设置下拉菜单项的文本与箭头的间距。设置为非法值或小于等于8的值时，取默认值。默认单位vp | 数值，单位为vp | 否 | `{ "space": 5 }` |
| arrowPosition | 设置下拉菜单项的文本与箭头之间的对齐方式 | 字符串枚举值<br>• "start": 箭头在前，文字在后<br>• "end": 文字在前，箭头在后。默认值 | 否 | `{ "arrowPosition": "start" }` |
| menuAlign | 设置下拉按钮与下拉菜单间的对齐方式 | Object {<br>• alignType：对齐方式类型，字符串枚举<br>  - start：按照语言方向起始端对齐，默认值<br>  - center：居中对齐<br>  - end：按照语言方向末端对齐<br>• offset：按照对齐类型对齐后，下拉菜单相对下拉按钮的偏移量。对象 {dx, dy}，默认值{dx:0, dy:0}<br>两个属性都是数值，单位为vp<br>} | 否 | `{ "alignType": "start", "offset": { "dx": 2, "dy": 2 } }` |
| optionWidth | 下拉菜单项的宽度 | 数值，单位为vp | 否 | `{ "optionWidth": 20 }` |
| optionHeight | 设置下拉菜单显示的最大高度 | 数值，单位为vp | 否 | `{ "optionHeight": 20 }` |
| menuBackgroundColor | 设置下拉菜单的背景色 | 16进制字符串 | 否 | `{ "menuBackgroundColor": "#BC7A33" }` |

##### Extended.Navigation

| 样式名称 | 样式说明 | 样式类型 | 必选 | 使用示例 |
|----------|----------|----------|------|----------|
| backgroundColor | 标题栏背景颜色 | 16进制字符串 | 否 | `{ "backgroundColor": "#BC7A33" }` |

### 4.3 交互

在A2UI扩展组件中，通过新增`listeners`字段定义交互事件：

```json
{
  "id": "edit_btn",
  "component": "Extended.Button",
  "child": "edit_btn_label",
  "variant": "default",
  "enabled": "{{ $user.canEdit }}",
  "listeners": {
    "onClick": {
      "handlerGroups": [{
        "condition": "{{ $user.canEdit }}",
        "handlers": [{
          "id": "validate_form",
          "call": "validate",
          "args": {
            "data": "{{ $__DataModel.formData }}"
          }
        }]
      }, {
        "condition": "{{ $handlerResult['validate_form'] == 0 }}",
        "handlers": [{
          "id": "submit_data",
          "call": "request",
          "args": {
            "url": "/api/update",
            "method": "POST",
            "body": "{{ $__DataModel.formData }}"
          }
        }]
      }]
    }
  }
}
```

**Event对象结构**：`listeners`对象是一个键值对，其中：

* 键: 预定义的交互事件类型（如`onClick`）
* 值: 事件处理器对象，包含`handlerGroups`数组

#### 4.3.1 交互事件

手势事件的关系是竞争互斥，只会响应第一个出现的手势。

**公共事件**

| 事件类型 | 触发条件 |
|----------|----------|
| onClick | 鼠标点击、触摸，属于手势事件 |
| onAppear | 组件显示 |

**组件特有事件**

| 组件 | 事件 | 触发条件 |
|------|------|----------|
| Extended.TextInput | onChange | 值发生变化 |
| Extended.List | onReachStart | 列表到达起始位置时触发。<br>List初始化时如果initialIndex为0会触发一次，List滚动到起始位置时触发一次。List边缘效果为弹簧效果时，划动经过起始位置时触发一次，回弹回起始位置时再触发一次。 |
| Extended.List | onReachEnd | 列表到达末尾位置时触发事件。当最后一个子组件因滚动或内容/布局变化出现在列表视窗中时，触发此回调。<br>当子组件未撑满列表，无须滚动即可直接在列表内完整展示时，首次加载也会触发此事件。List边缘效果为弹簧效果时，划动经过末尾位置时触发一次，回弹回末尾位置时再触发一次。 |
| Extended.GridRow | onBreakpointChange | 断点发生变化时触发回调。 |
| Extended.Radio | onChange | 选中状态发生变化 |
| Extended.Checkbox | onChange | 选中状态发生变化 |
| Extended.CheckboxGroup | onChange | 选中状态发生变化 |
| Extended.Tabs | onChange | 当前显示Tab值发生变化 |
| Extended.TabContent | onChange | 显隐状态发生变化 |
| Extended.Select | onChange | 当前选中选项发生变化 |
| Extended.Navigation | onChange | 显示的卡片下标发生变化 |

**事件上下文**

每个事件触发时，框架提供以下上下文信息：

```
interface EventContext {
  componentId: string;      // 触发事件的组件ID
  eventData?: any;          // 事件相关数据
}
```

**事件数据示例**

| 事件类型 | 事件数据 |
|----------|----------|
| onClick | `{ x: number, y: number }` - 点击坐标 |
| onChange | `{ value: any, oldValue: any }` - 新值和旧值 |
| onAppear | 无 |
| onReachStart | 无 |
| onReachEnd | 无 |
| onBreakpointChange | 字符串枚举值，"xs", "sm", "md", "lg", "xl", "xxl" |

#### 4.3.2 交互行为

| 行为名 | 说明 | 返回值 | 参数类型 | 参数类型说明 |
|--------|------|--------|----------|--------------|
| break | 跳出当前事件的行为链 | void | - | - |
| sendToLLM | 给LLM发送消息 | void | value | string<br>要发送给LLM的文本 |
| | | | textHidden | boolean<br>要发送的消息是否显示在对话框 |
| setDataModel | 设置数据模型值 | void | path | string<br>要设置的变量路径 |
| | | | value | any<br>要设置给目标变量的值 |
| setAttributes | 批量修改目标节点的属性值 | void | id | string<br>目标节点的ID |
| | | | value | object，key为属性名，value为属性值<br>要设置的属性名称和值 |
| scrollTo | List滑动顶部或底部 | void | xOffset | number<br>水平滚动总偏移量，默认单位vp。仅滚动轴为x轴时生效。<br>取值范围：当值小于0时，不带动画的滚动，按0处理。带动画的滚动，默认滚动到起始位置后停止 |
| | | | yOffset | number<br>竖直滚动总偏移量，默认单位vp。仅滚动轴为y轴时生效。<br>取值范围：当值小于0时，不带动画的滚动，按0处理。带动画的滚动，默认滚动到起始位置后停止 |
| navigate | Navigation子页面跳转 | void | componentId | string<br>要操作的目标Navigation组件 |
| | | | index | number<br>要跳转的子页面下标 |

**支持新增自定义行为**，可以在catalog新增交互行为定义，形式如下：

```json
"excutePlugin": {
      "type": "object",
      "description": "excute the target plugin.",
      "properties": {
        "call": {
          "const": "excutePlugin"
        },
        "args": {
          "type": "object",
          "properties": {
            "pluginName": {
              "type": "string",
              "format": "Expression",
              "description": "The name of plugin to open."
            }
          },
          "required": ["pluginName"],
          "additionalProperties": false
        },
        "returnType": {
          "const": "boolean"
        }
      },
      "required": ["call", "args"],
      "unevaluatedProperties": false
    },
```

**每个交互行为组（HandlerGroup）是一个对象**，至少包含以下字段：

```
interface HandlerGroup{
  handlers: Handler[];
  condition?: string;      // 可选：执行条件（表达式）
}
```

**字段说明**

* handlers：交互行为组所包含的行为列表
* condition：可选的执行条件，是一个表达式字符串。当条件为`true`时才执行该行为组。

**条件求值规则**：
- 如果`condition`字段不存在，默认执行
- 如果`condition`求值为`true`，执行该行为组
- 如果`condition`求值为`false`或`undefined`，跳过该行为组

```json
{
  "condition": "{{ $handlerResult['confirm_delete'] == 0 }}",
  "handlers": [{
    "id": "delete_item",
    "call": "setDataModel",
    "params": {
      "path": "{{'/items/' + $index }}",
      "value": null
    }
  }]
}
```

**每个交互行为是一个对象**，至少包含以下字段：

```
interface Handler {
  id: string;              // 行为唯一标识符
  call: string;            // 行为类型
  args: any;    // 行为参数
}
```

**字段说明**

* id：行为的唯一标识符，用于：
  1. 在`$handlerResult`中引用该行为的返回值

* call：行为类型，定义了要执行的操作。支持的行为类型见"预定义行为类型"

```json
{
  "id": "delete_item",
  "call": "setDataModel",
  "params": {
    "path": "{{'/items/' + $index }}",
    "value": null
  }
}
```

* args：行为参数，是一个对象，包含该行为类型所需的所有参数。参数值可以是：
  1. 静态值（字面量）
  2. 表达式字符串（`{{ ... }}`）
  3. 嵌套对象（支持混合使用表达式）

```json
{
  "args": {
    "url": "{{ '/api/users/' + $__DataModel.user.id }}",
    "method": "POST",
    "body": {
      "name": "{{ $formData.name }}",
      "email": "{{ $formData.email }}",
      "timestamp": "{{ $now }}"
    }
  }
}
```

**预定义行为类型**

* **break**：完成跳出当前事件的行为执行。

  示例：
  ```json
  {
    "id": "set_loading",
    "call": "break",
    "condition": "{{ $handlerResult[\"validate\"] == 0 }}"
  }
  ```

* **setDataModel**：设置数据模型中的值。

  示例：
  ```json
  {
    "id": "set_loading",
    "call": "setDataModel",
    "args": {
      "path": "/ui/isLoading",
      "value": true
    }
  }
  ```

  参数说明：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| path | string | 是 | __DataModel的路径（JSON Pointer） |
| value | any | 是 | 是要设置的值（支持表达式） |

* **sendToLLM**：给LLM发送消息。

  示例：
  ```json
  {
    "id": "send_feedback",
    "call": "sendToLLM",
    "args": {
      "value": "用户已提交反馈，请继续处理",
      "textHidden": false
    }
  }
  ```

  参数说明：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| value | string | 是 | 要发送给LLM的文本 |
| textHidden | boolean | 否 | 要发送的消息是否显示在对话框 |

* **setAttributes**：批量修改目标节点的属性值。

  示例：
  ```json
  {
    "id": "update_attr",
    "call": "setAttributes",
    "args": {
      "id": "user_avatar",
      "value": {
        "src": "{{ $__DataModel.user.avatarUrl }}",
        "alt": "用户头像"
      }
    }
  }
  ```

  参数说明：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| id | string | 是 | 目标节点的ID |
| value | object | 是 | 要设置的属性名称和值 |

* **navigate**：Navigation 子页面跳转。

  示例：
  ```json
  {
    "id": "navigate_to_tab",
    "call": "navigate",
    "args": {
      "componentId": "main_navigation",
      "index": 2
    }
  }
  ```

  参数说明：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| componentId | string | 是 | 要操作的目标Navigation组件 |
| index | number | 是 | 要跳转的子页面下标 |

* **scrollTo**：List向顶部或底部滑动。

  示例：
  ```json
  {
    "id": "scroll_top",
    "call": "scrollTo",
    "args": {
      "xOffset": 10
    }
  }
  ```

  参数说明：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| xOffset | number | 是 | 水平滚动总偏移量，默认单位vp。仅滚动轴为x轴时生效。取值范围：当值小于0时，不带动画的滚动，按0处理；带动画的滚动，默认滚动到起始位置后停止 |
| yOffset | number | 是 | 竖直滚动总偏移量，默认单位vp。仅滚动轴为y轴时生效。取值范围：当值小于0时，不带动画的滚动，按0处理；带动画的滚动，默认滚动到起始位置后停止 |

### 4.4 表达式

#### 4.4.1 基本语法

表达式使用双引号和双花括号 "{{ 和 }}" 包裹。

**语法规则：**

* 表达式必须以 "{{ 开始，以 }}" 结束
* 每个 "{{ }}" 对包含且仅包含一个完整的表达式
* 不支持嵌套表达式
* 不支持在一对双引号中使用多个表达式

**正确写法：**

```json
{
  "text": "{{ $firstName + ' ' + $lastName }}"  // 正确：完整的单个表达式
}
```

**错误示例（表达式完整性要求）：**

```json
{
  "text": "{{ '123' }} + {{ $__WindowSize.width }}"  // 错误：多个独立表达式
  "text": "{{ $firstName }} {{ $lastName }}"        // 错误：包含多个表达式
}
```

**限制说明：**

* ❌ "{{ inner {{ nested }} }}" - 不允许嵌套
* ❌ "{{ expr1 }} and {{ expr2 }}" - 不允许包含多个表达式
* ❌ "{{ '123' }} + {{ $__WindowSize.width }}" - 不允许多个表达式拼接
* ✅ "{{ expr1 + ' and ' + expr2 }}" - 使用字符串连接形成单个完整表达式
* ✅ "{{ '123' + $__WindowSize.width }}" - 在一个表达式内完成所有计算

#### 4.4.2 数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| string | 字符串（支持单引号） | 'hello' |
| number | 数字（整数或浮点） | 42，3.14 |
| boolean | 布尔值（必须小写） | true，false |

**基本类型写法规范：**

* 字符串：支持单引号：'string'
  支持模板字符串："{{ `Hello, ${$name}` }}"
* 布尔值：
  必须是小写：true、false
  ❌ 不支持：True、False、TRUE、FALSE

#### 4.4.3 运算符

| 优先级<br>（从高到低） | 运算符 | 说明 | 示例 |
|----------------|---------|------|------|
| 1 | () | 括号 | "{{ ($parentWidth - 20) / 2 }}" |
| 2 | . [] | 成员访问 | "{{ $__DataModel.config['api.endpoint'] }}" |
| 3 | ! | 逻辑非 | "{{ $isLogin && !$isLocked && $hasPermission }}" |
| 4 | * / % | 乘、除、取模 | "{{ $price * $quantity / $count % 100 }}" |
| 5 | + - | 加、减 | "{{ 1 - ($progress + $startValue) / 100 }}" |
| 6 | > >= < <= | 比较 | "{{ $age >= 18 ? '成年人' : '未成年' }}" |
| 7 | == != | 等值比较 | "{{ $password == $answer }}" |
| 8 | && | 逻辑与 | "{{ $isLogin && !$isLocked && $hasPermission }}" |
| 9 | \|\| | 逻辑或 | "{{ $isLogin \|\| !$isLocked && $hasPermission }}" |
| 10 | ?: | 三元条件 | "{{ $age >= 18 ? '成年人' : '未成年' }}" |

**数组索引和字符串属性访问**

支持使用方括号访问数组元素和对象属性，索引可以是常量、变量或字符串字面量。

* **数组索引特点**：
  1. 使用 [index] 语法访问数组元素
  2. 索引可以是数字常量或变量
  3. 支持链式访问：$items[0].user.name
  4. 绝对路径也支持数组：$__DataModel.items[0].name

* **中括号字符串取值**：当属性或变量名包含特殊字符（如 .）时，必须使用中括号内的字符串字面量访问：

```json
{
  "text": "{{ $item['ext.style'].backgroundColor }}",
  "value": "{{ $__DataModel.config['api.endpoint'] }}"
}
```

**中括号访问规则**：
1. 使用字符串字面量作为属性名：$obj['propertyName']
2. 支持特殊字符：$item['ext.style']（属性名包含 .）
3. 支持变量作为属性名：$obj[$propertyName]

```json
{
  "text": "{{ $items[0].name }}",
  "value": "{{ $__DataModel.users[$index].age }}",
  "visible": "{{ $items[$index].isActive }}",
  "style": "{{ $item['ext.style'] }}",
  "config": "{{ $__DataModel.settings['api.config.url'] }}"
}
```

#### 4.4.4 内置变量

**全局变量**：框架提供的系统级响应式变量，可在任何表达式中访问。

| 变量名 | 类型 | 说明 |
|--------|------|------|
| __DataModel | object | 具体类型取决于数据本身的结构 |
| __WindowBreakpoint | string | 当前窗口断点枚举值（如 'sm', 'md', 'lg', 'xl'） |
| __WindowSize | object | 窗口尺寸 { width: number, height: number } |
| __ColorMode | string | 主题深浅色模式（'light' 或 'dark'） |

示例：

```json
{
  "component": "Extended.Column",
  "align": "{{ $__WindowBreakpoint == 'sm' ? 'center' : 'start' }}",
  "children": ["title_text"]
}
```

**路径变量（__DataModel）**：通过路径引用系统访问，支持绝对路径和相对路径。将绝对路径的数据视为一个全局变量$__DataModel，可以通过.或者['key']的方式访问其中的值。

* **和A2UI 协议的 path 属性的区别**：
  * A2UI 协议的 path 属性：使用 / 分隔符（如 "path": "/users"），这是 A2UI 协议规范
  * 表达式内部：使用变量的访问方式，通过.或者['key']的方式访问属性（如 $__DataModel.user.name或$__DataModel['user'].name）

**路径语法规则**

| 路径类型 | 语法 | 示例 | 说明 |
|----------|------|------|------|
| 绝对路径 | $__DataModel['xxx'].yyy | $__DataModel['user'].name | 从数据模型根节点开始 |
| 相对路径 | $xxx.yyy['zzz'] | $firstName['length'] | 从当前作用域开始 |

* **绝对路径**：使用 $__DataModel 前缀标识从数据模型根节点开始的路径。

```json
{
  "component": "Extended.Text",
  "text": "{{ $__DataModel.user.profile.name }}"
}
```

**绝对路径特点**：
1. 必须以 $__DataModel 开头
2. 使用 . 或者[]进行属性访问
3. 不受当前作用域影响
4. 适合访问全局配置、用户信息等

* **相对路径**：使用 $ 前缀标识从当前组件的作用域解析的路径。在列表模板中，相对于当前项数据。

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/users",
    "componentId": "user_item"
  }
},
{
  "id": "user_item",
  "component": "Extended.Text",
  "text": "{{ $firstName + ' ' + $lastName }}"
}
```

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/users",
    "componentId": "user_item"
  }
},
{
  "id": "user_item",
  "component": "Extended.Text",
  "text": "{{ $firstName + ' ' + $lastName }}"
}
```

**相对路径特点**：
1. 使用 $ 前缀标识相对路径
2. 使用 . 分隔各个层级
3. 从当前作用域开始解析
4. 在列表中，相对于当前项（$item）

**使用场景**：

1. 列表模板中的项数据：$name, $price, $category
2. 组件本地状态：$isLoading, $error
3. 嵌套对象：$user.profile.age

* **混合使用示例**：

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/comments",
    "componentId": "comment_item"
  }
},
{
  "id": "comment_item",
  "component": "Extended.Column",
  "children": ["app_name", "comment_text", "author_info"]
},
{
  "id": "app_name",
  "component": "Extended.Text",
  "text": "{{ $__DataModel.app.name }}"
  // 绝对路径：每次迭代都从根获取，显示应用名称
},
{
  "id": "comment_text",
  "component": "Extended.Text",
  "text": "{{ $text }}"
  // 相对路径：从当前评论项获取
  // 第1次迭代：comments[0].text
  // 第2次迭代：comments[1].text
},
{
  "id": "author_info",
  "component": "Extended.Text",
  "text": "{{ $__DataModel.currentUser.name + ' replied to ' + $author }}"
  // 混合使用：
  // $__DataModel.currentUser.name → 绝对路径，获取当前用户
  // $author → 相对路径，从当前评论获取作者
}
```

**局部变量**：

| 变量 | 种类 | 类型 | 说明 |
|------|------|------|------|
| index | 循环变量 | number | 当前项的索引（从0开始） |
| item | 循环变量 | any | 当前项的数据对象 |
| handlerResult[key] | 行为结果变量 | any | 在事件响应执行时，handlerGroups列表中已经执行的行为组中的行为的返回值会被保存为局部变量，所有行为组执行完成时释放。通过行为ID可以访问目标行为的返回值变量。 |
| $context | 事件参数 | EventContext | 事件响应时，根据不同的事件类型会有不同的事件参数。 |

* **循环变量**：在支持使用模板生成子组件的父组件（Extended.Row, Extended.Column, Extended.List, Extended.Grid, Extended.GridRow, Extended.Tabs）中，循环变量自动可用。

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/items",
    "componentId": "item_template"
  }
},
{
  "id": "item_template",
  "component": "Extended.Text",
  "text": "{{ ($index + 1) + '. ' + $item.name }}"
}
```

* **自定义循环变量名**：可以通过 indexVar 和 itemVar 属性自定义循环变量名。

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/items",
    "componentId": "item_template",
    "indexVar": "i",
    "itemVar": "product"
  }
},
{
  "id": "item_template",
  "component": "Extended.Text",
  "text": "{{ $i + ':' + $product.name }}"
}
```

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| indexVar | string | "index" | 自定义索引变量名 |
| itemVar | string | "item" | 自定义项数据变量名 |

```json
{
  "component": "Extended.List",
  "children": {
    "path": "/classes",          // 班级列表
    "componentId": "class_template",
    "indexVar": "classIdx",
    "itemVar": "classInfo"
  }
},
{
  "id": "class_template",
  "component": "Extended.Column",
  "children": [
    {
      "component": "Extended.Text",
      "text": "班级 {{ ($classIdx + 1) + ':' + $classInfo.name }}"
    },
    {
      "component": "Extended.List",
      "children": {
        "path": "/students",     // 当前班级的学生列表
        "componentId": "student_template"
                              // 使用默认 $index 和 $item
      }
    }
  ]
},
{
  "id": "student_template",
  "component": "Extended.Text",
  "text": "班级{{ $classIdx +1 }} - 学生{{ ($index +1) + ':' + $name }}"
  // 同时访问外层 $classIdx 和内层 $index
}
```

* **行为结果变量**：在事件处理的 handlerGroups 列表中，可以通过 $handlerResult["handlerId"] 引用之前已执行的handler的返回值。

* **事件参数变量**：在事件处理的 handlerGroups 列表中，可以通过 $context 获取事件参数。

```json
{
  "component": "Extended.Button",
  "listeners": {
    "onClick": {
      "handlerGroups": [{
        "handlers": [{
            "id": "validate",
            "call": "validateForm",
            "args": {
              "x": "{{ $context.eventData.x }}"
            }
        }]
      }, {
        "condition": "{{ $handlerResult[\"validate\"] == 0 }}",
        "handlers": [{
            "id": "submit",
            "type": "submitData",
            "args": {}
        }]
      }]
    }
  }
}
```

#### 4.4.5 内置扩展函数

**字符串函数**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| format(template, ...args) | string, ...any | string | 格式化字符串（使用槽位占位符） |

**format函数详解**：format 函数使用槽位占位符 {}（类似 C++ std::format 风格）进行字符串格式化：

```json
{
  "text": "{{ format('Hello, {}!', $name) }}",
  "description": "{{ format('User {} has {} messages', $userName, $messageCount) }}",
  "path": "{{ format('/api/users/{}/posts/{}', $userId, $postId) }}"
}
```

除了 format 函数，表达式模块也支持模板字符串（使用反引号）：

```json
{
  "text": "{{ `Hello, $name!` }}",
  "description": "{{ `User $userName has $messageCount messages` }}"
}
```

**数组函数**

| 函数 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| size(arr) | array | number | 数组长度 |

```json
{
  "text": "{{ size($items) + ' 件高价商品'}}",
}
```

#### 4.4.6 类型转换

**自动转换**

| 运算 | 转换规则 |
|------|----------|
| string + number | number转string，拼接 |
| string + boolean | boolean转string，拼接 |
| number + string | 尝试string转number |
| boolean + number | boolean转number（true=1, false=0） |
| !value | 转boolean，取反 |

#### 4.4.7 响应式表达式

当使用的变量发生改变的时候，会重新计算表达式，并更新对应的属性。

会被更新的属性范围：

* 组件属性
* 组件样式属性

"#"作为保留字符，如后续有需要，以此禁用变量的响应能力。

