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

执行 `vcal build` 时，会自动执行 `vcal check lint`（含 `config.yml` 检查），若不通过，将终止构建。

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
日历客户端据此判断是否需要更新本地条目。

构建时，会将本次构建的产物，与 `dist` 中上次的产物比对。  
若内容一致，则不更新 DTSTAMP。  
若内容不同，或者首次竖线，则将当前时间作为 DTSTAMP，客户端覆盖更新/添加此条目数据。

### ics update

构建时，会在构建日期的上一年 1 月 1 日，创建 update 日程。  
里面记录了版本号、项目地址、所有贡献者。  
update 日程的 uuid 由基础文件名派生，固定不变。  
