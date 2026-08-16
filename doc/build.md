# build

根据 `config.yml` 和 `data/` 构建到 `dist/`。

## 用法

```text
vcal build [--config config.yml] [--data data] [--output dist]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--config` | `config.yml` | 构建配置 |
| `--data` | `data` | 数据目录 |
| `--output` | `dist` | 输出目录 |

执行 `vcal build` 时，会自动执行 `vcal check lint`，若不通过，将终止构建。

## 产物

| 文件 | 说明 |
| --- | --- |
| `vCal_ACGbday.ics` | 完整版日历（含简介/附加行） |
| `vCal_ACGbday_safe.ics` | 精简版日历（只含名字与作品名） |
| `vCal_ACGbday_original.ics` | 原名版日历 |
| `vCal_ACGbday.js` | 中文版今日生日脚本 |
| `vCal_ACGbday_original.js` | 原名版今日生日脚本 |
| `list.md` | 角色列表（按作品分组） |

## 配置

`config.yml` 的 `ics:` 段定义每个 ics 版本，`js:` 段定义 js 版本。  
各字段决定 `SUMMARY / LOCATION / DESCRIPTION` 的数据来源与组织方式。  
详见 [config.yml](../config.yml)。

## 其他

### 角色 DTSTAMP

这个条目记录 ics 数据中，一个日程的修改时间。

一个角色首次被构建，会自动以当前时间作为 DTSTAMP。  
对于已有角色，会读取旧 dist 中已存在的 UID 与 DTSTAMP 映射。角色未改动时沿用它，有改动则以当前时间作为 DTSTAMP。

因此，当修改了角色数据时，需要一并修改一下记录的 uuid，以确保 DTSTAMP 自动刷新。

### ics update

构建时，会在构建日期的上一年 1 月 1 日，创建 update 日程。  
里面记录了版本号、项目地址、所有贡献者。

这些都是程序自动创建的，无须手动添加文件。
