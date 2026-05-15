# Lolicon API v2 使用完整文档

本文档根据 Lolicon API v2 的公开说明整理，用于在本插件或其它客户端中调用随机图片接口。

## 基本信息

随机色图 API 最初作为 `cq-picsearcher-bot` 的娱乐功能开发，后续正式开放使用。当前 API 已迁移至第三方服务，不再需要 `apikey`，但仍存在调用限制，请合理使用。

所有图片均来自 Pixiv，版权归原作者所有。API 仅保存作品基本信息，不代理或储存图片文件。

## 接口地址

```text
GET https://api.lolicon.app/setu/v2
POST https://api.lolicon.app/setu/v2
```

POST 请求需要使用 JSON：

```http
Content-Type: application/json
```

## 快速示例

### GET 获取一张全年龄随机图片

```text
https://api.lolicon.app/setu/v2
```

### GET 获取指定标签图片

```text
https://api.lolicon.app/setu/v2?tag=萝莉|少女&tag=白丝|黑丝
```

含义为：

```text
(萝莉 OR 少女) AND (白丝 OR 黑丝)
```

### GET 同时请求多种图片规格

```text
https://api.lolicon.app/setu/v2?size=original&size=regular
```

### POST 示例

```json
{
  "r18": 0,
  "num": 1,
  "tag": [
    ["萝莉", "少女"],
    ["白丝", "黑丝"]
  ],
  "size": ["regular"],
  "excludeAI": true
}
```

## 请求参数

| 参数名 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `r18` | `int` | `0` | `0` 为非 R18，`1` 为 R18，`2` 为混合。该分类为图库内分类，不等同于 Pixiv 作品本身的 R18 标识。 |
| `num` | `int` | `1` | 一次返回的结果数量，范围 `1` 到 `20`。指定关键字或标签时，实际返回数量可能少于指定数量。 |
| `uid` | `int[]` | 无 | 返回指定 Pixiv 作者 uid 的作品，最多 20 个。 |
| `keyword` | `string` | 无 | 从标题、作者、标签中按关键字模糊匹配，大小写不敏感。性能和准确度较差，建议使用 `tag`。 |
| `tag` | `string[]` 或二维数组 | 无 | 按标签、作者名、标题进行 AND / OR 匹配。详见 `tag` 说明。 |
| `size` | `string[]` | `["original"]` | 返回指定图片规格的地址。详见 `size` 说明。 |
| `proxy` | `string` | `i.pixiv.re` | 设置图片地址使用的在线反代服务。详见 `proxy` 说明。 |
| `dateAfter` | `int` | 无 | 返回在该时间及以后上传的作品，单位为毫秒时间戳。 |
| `dateBefore` | `int` | 无 | 返回在该时间及以前上传的作品，单位为毫秒时间戳。 |
| `dsc` | `boolean` | `false` | 禁用部分缩写 `keyword` 和 `tag` 的自动转换。 |
| `excludeAI` | `boolean` | `false` | 排除 AI 作品。 |
| `aspectRatio` | `string` | 无 | 按图片长宽比筛选。详见 `aspectRatio` 说明。 |

## 数组参数

GET 请求可以通过追加同名参数发送数组：

```text
https://api.lolicon.app/setu/v2?size=original&size=regular
```

POST 请求中，如果数组只有一个元素，可以省略数组写法：

```json
{
  "size": "regular"
}
```

等价于：

```json
{
  "size": ["regular"]
}
```

## 布尔值参数

以下值会被视为假值：

```text
0、false、null、"0"、"false"、"null"、空字符串
```

其它值均会被视为真值。

## tag 参数

`tag` 可以按照 AND 和 OR 规则匹配标签、作者名、标题，所有匹配均大小写不敏感。

匹配规则：

- 参数数组内的每个字符串之间使用 AND 规则，最多 3 个。
- 每个字符串可以包含多个用 `|` 分隔的标签，标签之间使用 OR 规则，最多 20 个。
- 标签和作者名使用 n-gram 分词匹配，`2 <= n <= 3`。
- 标题为完全匹配。

例如需要查找：

```text
(萝莉 OR 少女) AND (白丝 OR 黑丝)
```

GET 写法：

```text
https://api.lolicon.app/setu/v2?tag=萝莉|少女&tag=白丝|黑丝
```

POST 写法：

```json
{
  "tag": [
    "萝莉|少女",
    "白丝|黑丝"
  ]
}
```

POST 也可以直接使用二维数组：

```json
{
  "tag": [
    ["萝莉", "少女"],
    ["白丝", "黑丝"]
  ]
}
```

## size 参数

`size` 用于指定返回的图片规格地址。支持以下值：

| 规格 | 示例地址 |
| --- | --- |
| `original` | `https://i.pixiv.re/img-original/img/2021/06/14/17/25/59/90551655_p0.jpg` |
| `regular` | `https://i.pixiv.re/img-master/img/2021/06/14/17/25/59/90551655_p0_master1200.jpg` |
| `small` | `https://i.pixiv.re/c/540x540_70/img-master/img/2021/06/14/17/25/59/90551655_p0_master1200.jpg` |
| `thumb` | `https://i.pixiv.re/c/250x250_80_a2/img-master/img/2021/06/14/17/25/59/90551655_p0_square1200.jpg` |
| `mini` | `https://i.pixiv.re/c/48x48/img-master/img/2021/06/14/17/25/59/90551655_p0_square1200.jpg` |

如果 `size` 参数不符合上述任一规格，响应中的 `urls` 会是空对象：

```json
{}
```

## proxy 参数

Pixiv 图片域名 `i.pximg.net` 有防盗链机制，不包含 `www.pixiv.net` referrer 的请求会返回 `403`。如果需要在网页或客户端中直接展示、下载图片，通常需要使用反代服务。

默认反代为：

```text
i.pixiv.re
```

当 `proxy` 不指定协议时，API 会自动补充 `https://`。

你也可以将 `proxy` 设置为任意假值，以获取原始 `i.pximg.net` 图片地址。

### proxy 占位符

| 占位符 | 说明 | 示例值 |
| --- | --- | --- |
| `{{pid}}` | 作品 pid | `90551655` |
| `{{p}}` | 作品所在页 | `0` |
| `{{uid}}` | 作者 uid | `43454954` |
| `{{ext}}` | 原图扩展名 | `jpg` |
| `{{path}}` | 图片地址的相对路径 | 根据规格不同而不同 |
| `{{datePath}}` | 相对路径中的日期部分 | `2021/06/14/17/25/59` |

以下写法等价：

```text
i.pixiv.re
https://i.pixiv.re
i.pixiv.re/{{path}}
https://i.pixiv.re/{{path}}
```

如果使用了占位符，但没有使用 `{{path}}`，则 `size` 参数无意义，不同规格返回的地址会相同。

### 自定义缩略图规格

可以通过 `proxy` 占位符构造特定大小的缩略图：

```text
https://i.pixiv.re/c/<size>x<size>/img-master/img/{{datePath}}/{{pid}}_p{{p}}_<master|square>1200.jpg
```

说明：

- `<size>x<size>` 的长宽必须相同。
- 最大尺寸为 `600x600`。
- 某些特定大小需要附加固定图片质量参数，例如 `small` 和 `thumb`。
- `master` 表示等比例缩放，不裁切，使长度或宽度最大为指定尺寸。
- `square` 表示居中裁切。

## dsc 参数

API 内部包含少量自动转换规则，会把一些不适合直接搜索的缩写或简称转换为更合适的搜索词。

示例：

| 输入 | 自动转换为 |
| --- | --- |
| `vtb` | `虚拟YouTuber|VTuber` |
| `fgo` | `Fate/GrandOrder|Fate/Grand Order|FateGrandOrder` |
| `pcr` | `公主连结|公主连结Re:Dive|プリンセスコネクト` |
| `gbf` | `碧蓝幻想` |
| `舰b` | `碧蓝航线|AzurLane` |
| `舰c` | `舰队collection` |
| `少前` | `少女前线|girlsfrontline` |

将 `dsc` 设置为任意真值可以禁用这些转换。

## aspectRatio 参数

`aspectRatio` 用于按图片长宽比筛选，格式需要符合：

```regex
((gt|gte|lt|lte|eq)[\d.]+){1,2}
```

顺序不影响。所有长宽比数据都会四舍五入到小数点后 3 位。

常见写法：

| 需求 | 写法 |
| --- | --- |
| 竖图，长宽比小于 1 | `lt1` |
| 横图，长宽比大于 1 | `gt1` |
| 正方形，长宽比等于 1 | `eq1` |
| 约为 16:9，大于 1.7 且小于 1.8 | `gt1.7lt1.8` |
| 基本为 16:9，大于等于 1.777 且小于等于 1.778 | `gte1.777lte1.778` |

## 响应结构

接口响应为 JSON：

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `error` | `string` | 错误信息。成功时通常为空字符串。 |
| `data` | `setu[]` | 图片信息数组。 |

### setu 对象

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `pid` | `int` | Pixiv 作品 pid。 |
| `p` | `int` | 作品所在页。 |
| `uid` | `int` | 作者 uid。 |
| `title` | `string` | 作品标题。 |
| `author` | `string` | 作者名，入库时会过滤掉 `@` 及其后内容。 |
| `r18` | `boolean` | 是否为 R18。该分类为图库内分类，不等同于 Pixiv 作品本身的 R18 标识。 |
| `width` | `int` | 原图宽度，单位 px。 |
| `height` | `int` | 原图高度，单位 px。 |
| `tags` | `string[]` | 作品标签，包含标签的中文翻译，如果存在。 |
| `ext` | `string` | 图片扩展名。 |
| `aiType` | `number` | 是否为 AI 作品。`0` 表示未知，`1` 表示不是，`2` 表示是。 |
| `uploadDate` | `int` | 作品上传日期，单位为毫秒时间戳。 |
| `urls` | `object` | 包含所有指定 `size` 的图片地址。 |

### 响应示例

```json
{
  "error": "",
  "data": [
    {
      "pid": 90551655,
      "p": 0,
      "uid": 43454954,
      "title": "example title",
      "author": "example author",
      "r18": false,
      "width": 1000,
      "height": 1400,
      "tags": ["tag1", "tag2"],
      "ext": "jpg",
      "aiType": 1,
      "uploadDate": 1623662759000,
      "urls": {
        "original": "https://i.pixiv.re/img-original/img/2021/06/14/17/25/59/90551655_p0.jpg"
      }
    }
  ]
}
```

## 自动更新作品信息

被获取的作品如果满足以下条件，会被加入后台更新队列：

- 作品上传时间在两年内。
- 距离上次更新信息超过 90 天。

这用于减少作品修改或删除导致原图地址失效的问题。

注意：当次调用以及后台更新完成前，API 返回的仍然可能是旧信息。

## 调用建议

- 默认使用 `r18: 0`，避免在不合适的场景返回 R18 内容。
- 优先使用 `tag`，少用 `keyword`。
- 展示图片时建议使用 `regular` 或 `small`，需要原图时再请求 `original`。
- 面向聊天机器人时建议限制 `num`，避免一次返回过多结果。
- 如果不希望返回 AI 作品，可设置 `excludeAI: true`。
- 直接展示 Pixiv 图片时建议保留默认 `proxy`，否则原始地址可能因防盗链返回 `403`。

## 相关入口

- API v2：`https://api.lolicon.app/setu/v2`
- Telegram Bot：`@setu_robot`，仅支持 inline 方式调用。

