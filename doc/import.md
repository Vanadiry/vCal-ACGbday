# Import

## import fill

用于批量补全已有作品的数据。  
扫描 `data/` 下每部作品，从 bangumi 拉取该作品的全部角色，找出 `data/` 中缺失的角色并补全到 `import/`。

### 用法

```text
vcal import fill [--data DIR] [--import-dir DIR] [--report PATH]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--data` | `data` | 数据目录 |
| `--import-dir` | `import` | 输出目录（生成的角色放这里） |
| `--report` | `import/report.yml` | 无生日/失败角色的报告 |

### 流程

1. 遍历 `data/` 每部作品，读取 `_info.yml` 的 `id.bangumi`，拉取该 subject 的全部角色列表。
2. 对每个角色拉取详情，与 `data/` 中已有的 `refs.bangumi` 比对，处理缺失角色。

最后，会生成包含 `name`、`bday`、`desc.main`、`refs.bangumi` 的数据。  
虽然这是个自动化工具，但还是需要手工审核数据的。

目前设置为 12 并发，通常是不会触发限速的。  
真被 403 了，fill 会自动降低并发，并等待一会后重试。

## import tracker

用于拉取整部作品的数据。  
读取 `import/tracker.yml`，为其中记录的每部作品拉取全部角色，生成 `import/<folder>/` 下的 `_info.yml` 与角色 yml。

### tracker.yml 格式

```yaml
- name: "作品文件夹名"
  subject: # bangumi subject id 数组，多季作品应当全部记录
    - 111
    - 333
```

### 用法

```text
vcal import tracker [--tracker PATH] [--import-dir DIR]
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--tracker` | `import/tracker.yml` | tracker 文件路径 |
| `--import-dir` | `import` | 输出目录 |

### 流程

1. 拉取每个 subject 主数据（名称），合并生成各作品的 `_info.yml`。
2. 拉取角色列表（过滤客串）。
3. 对每个角色拉取详情，生成角色 yml。

解析不到的内容，会用 `null` 占位。
