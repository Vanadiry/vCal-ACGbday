# Import

## import fill

用于批量补全已有作品的数据。  
扫描 `data/` 下每部作品，从 bangumi 拉取该作品的全部角色，找出 `data/` 中缺失的角色并补全到 `import/`。

## 用法

```text
vcal import fill [--data DIR] [--import-dir DIR] [--report PATH]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--data` | `data` | 数据目录 |
| `--import-dir` | `import` | 输出目录（生成的角色放这里） |
| `--report` | `import/report.yml` | 无生日/失败角色的报告 |

## 流程

1. 遍历 `data/` 每部作品，读取 `_info.yml` 的 `id.bangumi`，拉取该 subject 的全部角色列表。
2. 对每个角色拉取详情，与 `data/` 中已有的 `refs.bangumi` 比对，处理缺失角色。

最后，会生成包含 `name`、`bday`、`desc.main`、`refs.bangumi` 的数据。  
虽然这是个自动化工具，但还是需要手工审核数据的。

目前设置为 12 并发，通常是不会触发限速的。  
真被 403 了，fill 会自动降低并发，并等待一会后重试。
