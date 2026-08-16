# Check

## check lint

校验 `data/` 下所有数据文件是否符合 schema。

```text
vcal check lint [--data DIR] [--report PATH]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--data` | `data` | 数据目录 |
| `--report` | `report/lint_report.yml` | 报告输出路径 |

检查内容：

1. **单文件结构**：按 `schema/` 校验（必填字段、类型、取值范围、uuid 格式、refs/id 规则）
2. **危险字符**：控制字符等可能导致崩溃的内容
3. **uuid**：重复和不规范的 uuid
4. **命名冲突**：同名角色，uuid 相同则报错，uuid 不同则警告

## check uuid

将版本位非 1-5 的 uuid 重写为标准 v4（小写）。

```text
vcal check uuid [--data DIR]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--data` | `data` | 数据目录 |

行为：扫描所有角色文件，找出不合规 uuid，直接改写为标准 v4，重写后检查是否重复。  
此工具会修改数据文件。

## check dist

用 icalendar 解析验证 `dist/` 下的 ics 文件结构合法性。

```text
vcal check dist [--dist DIR]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--dist` | `dist` | 产物目录 |

检查内容：ics 能否被 icalendar 解析；每个 VEVENT 是否包含 UID / SUMMARY / DTSTART / DTSTAMP。
