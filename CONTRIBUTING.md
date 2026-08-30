# 贡献指南

感谢你愿意为 vCal-ACGbday 贡献数据！  
本项目记录二次元角色的生日，贡献者通过维护 `data/` 目录下的数据文件来添加或修正角色。

## 环境准备

需要 `python >= 3.10`。  
推荐使用虚拟环境。

```python
pip install -e ".[dev]"
```

## 数据

数据结构，详见 [data-format](doc/data-format.md)。

使用 `vcal check lint` 来执行格式验证，提交前，需确保 Lint 通过。  
此外，还有一些方便的校验工具，参考 [check](doc/check.md) 和 [check-online](doc/check-online.md)。

### 改动数据

要改动数据，只需要修改 `data/` 的数据即可。

**改动角色数据，必须修改 uuid。**（改动 `refs` 无须修改）  
因为 uuid 同时是角色的版本标识。构建脚本会判断 uuid 是否变化，来自动处理 ics 文件中条目的改动日期。

### 添加数据

要手动添加数据，在 `data/` 直接添加即可。  
不过，有一些方便的补全和添加工具，详见 [import](doc/import.md)。

### 番组计划 API

使用番组计划 API 的调用，均支持使用 `--auth` 传入你的令牌。  
部分受限条目，对于匿名请求会返回 404。令牌可以在[这里](https://next.bgm.tv/demo/access-token)创建。

## 提交 Pull Request

修改数据之后，在 [CHANGELOG.md](CHANGELOG.md) 的“未发版变更”小节中，记录本次的变化。  
按 [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) 填写并提交 PR。

`dist/` 构建产物，以及 [CHANGELOG.md](CHANGELOG.md) 的历史版本记录，由维护者构建，无需在 PR 中提交。  
维护者会定期处理，并发布新版本。

若要新增构建项，请提交 Issue。  
不需要在 [config.yml](config.yml) 里添加新的 `contributors` 记录。PR 合并时会手动加入。
