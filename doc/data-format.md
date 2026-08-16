# 数据格式

角色数据存放在 `data/` 目录，每部作品一个文件夹，作品信息和角色信息分别存放。  
格式由 `schema/` 下的 JSON Schema 定义，`vcal check lint` 按 schema 校验。

## 目录结构

```text
data/
  <作品名>/          # 文件夹名
    _info.yaml      # 作品信息
    <角色名>.yml     # 角色信息，一个角色一个文件
```

角色数据的 yml 文件名，以及作品目录的文件夹名，均使用中文名（不要空格）。

## 作品 `_info.yaml`

```yaml
name:
  orig: 魔法少女まどか☆マギカ # 原名（必填）
  zh: 魔法少女小圆           # 中文名（必填）
  ja: 0                    # 可选，为 0 则表示引用 orig
id:
  bangumi:                 # bangumi subject id 数组
    - 9717
    - 25833
  # custom: 123            # 可选，自定义 id，仅在另外两个没有的时候使用
  # moegirl: [...]         # 可选，萌百页面名数组
```

### name

`name` 支持任意语言变体，键为 `^[a-z]{2}(-[a-z]+)?$`（如 `zh`、`ja`、`en`、`zh-pinyin`、`ja-kana`）：

| 值 | 含义 |
| --- | --- |
| `0` | 等于 `orig` |
| 非空字符串 | 该语言的名称 |
| 缺省 | 该语言无名称 |

### id

`bangumi` / `custom` / `moegirl` 至少一个：

- `bangumi`：整数数组，排序以首个为键
- `custom`：正整数
- `moegirl`：字符串数组

对于 `bangumi`，作品有多个季或条目，应该都记录。

## 角色 `<角色名>.yml`

```yaml
name:
  orig: 鹿目 まどか           # 日文原名（必填）
  zh: 鹿目圆                 # 中文名（必填）
  ja-kana: かなめ まどか      # 假名读法
  ja: 0
desc:
  extra:                    # 可选，附加行列表（代号/小名/名台词）
    - 救济的魔女／救済の魔女
    - Kriemhild Gretchen
  main: |-                  # 可选，简介（块标量）
    小圆...熟悉的名字...是谁？
bday:
  y: 9999                   # 可选，年份
  m: 10                     # 必填，月（1-12）
  d: 3                      # 必填，日（1-31）
  verified: true            # 可选，已确认数据，跳过 bday 联网检查
uuid: a448204a-9ca0-47b8-8f19-ae6bcf7b1f33   # 必填，唯一标识
refs:
  bangumi: 10439            # 数据源
  moegirl: 鹿目圆
```

### 必填字段

- `name.orig`、`name.zh`：名字
- `bday.m`、`bday.d`：生日月日（年份可选）
- `uuid`：唯一标识
- `refs`：至少一个数据源引用

### refs 字段

至少一个数据源，用于生日数据校验：

| 键 | 值 | 说明 |
| --- | --- | --- |
| `bangumi` | 整数或数字字符串 | bgm 角色 id |
| `moegirl` | 字符串 | 萌娘百科页面名 |
| `wikipedia-<lang>` | 字符串 | 维基页面名，`-` 后为语言前缀 |

### bday.verified

`bday.verified: true` 时，`vcal check bday` 跳过该角色的联网检查。  
用于在别处已确认权威数据的角色。  
设置此项时，需要添加注释，列出从何处确认。

## 约定

**改动角色数据，必须修改 uuid。**  
因为 uuid 同时是角色的版本标识。构建脚本会判断 uuid 是否变化，来自动处理 ics 文件中条目的改动日期。

角色数据允许不完整（如缺少年份、缺少某个名字），不要写空值占位（空字符串、空列表、null 都不应存在）。
