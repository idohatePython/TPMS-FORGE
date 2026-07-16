# TPMS-FORGE 开发计划与任务清单

版本：v0.1  
基线分支：`backend`  
最后更新：2026-07-16

## 1. 项目目标

TPMS-FORGE 是一个面向增材制造的 Web 平台。V1.0 必须跑通以下真实闭环：

```text
上传 STL/OBJ
-> 生成或导入 TPMS 模型
-> 导出 STL
-> OrcaSlicer 切片
-> 查看逐层、逐行 G-code 路径
-> 下载 G-code
```

V1.0 的重点是可靠地完成单用户/少量用户的端到端工作流，不在此阶段引入微服务、Kubernetes、Kafka 或多云存储。

## 2. 当前基线

已完成：

- Vue 3 + TypeScript + Vite + Naive UI 的工作台与主要页面骨架。
- FastAPI 的认证、项目、文件、任务和管理员 API 骨架；部分业务数据仍为 mock。
- STL/OBJ 上传、Three.js 模型查看、OrcaSlicer CLI 调用和 G-code 下载。
- Web Worker 中的 Orca G-code 解析，支持 `;LAYER_CHANGE`、`M82/M83`、`G90/G91`、`G2/G3`。
- Cura 风格层范围与逐行路径预览；真实打印路径不透明，空驶路径默认隐藏且可单独开启。
- 外部数据目录：`../TPMS-FORGE-data`。STL/OBJ/G-code 不在 Git 仓库中。
- 项目文件页面：模型和 G-code 的列表、下载、删除。
- 基础静态检查、Python 测试、真实 `Phone Holder` G-code 解析测试、前端生产构建。

当前限制：

- 项目、用户、任务仍主要来自内存 mock 数据，服务重启后业务元数据不会持久化。
- 切片接口当前同步调用 OrcaSlicer，长任务会占用 HTTP 请求。
- Celery、Redis、PostgreSQL 的工程配置已存在，但业务链路尚未真正接入。
- TPMS 生成、网格处理、预览和任务状态轮询仍是待实现能力。
- G-code 预览已经能够正确解析当前 Orca 输出，但还不是完整的专业切片器渲染器。

## 3. 不可变约定

- Git 仓库只保存代码、配置示例、测试和小型 fixture；不保存用户 STL、OBJ、G-code、`.env` 或 Orca 本机配置。
- 文件本体通过 `StorageService` 访问。业务模块不得手工拼接 `storage/users/...` 路径。
- V1.0 使用本地外部数据目录；将来迁移 MinIO/S3 时只替换存储实现。
- 前端只调用后端 API；不直接访问本地文件系统、OrcaSlicer 或数据库。
- worker 只调用 `algorithms.pipeline`。算法底层模块不得反向依赖 FastAPI、Vue 或 Celery。
- 新功能从 `backend` 创建 `feature/<topic>` 分支，通过 PR 合并回 `backend`。

## 4. 里程碑

### M0：交接与环境可复现

目标：新开发者在干净机器上能启动完整开发环境，并能使用自己的 OrcaSlicer 配置切片一个模型。

任务：

- [ ] 补充 `.env.example` 注释，说明 Windows、WSL、Linux 下 `ORCA_SLICER_PATH` 和配置文件路径的写法。
- [ ] 在 README 中补充“外部数据目录初始化、迁移、备份、清理”说明。
- [ ] 为 `scripts/check-env.sh` 增加 `STORAGE_ROOT` 可写性检查和 Orca 可执行文件检查。
- [ ] 统一开发启动方式：本地 `uv + pnpm` 与 Docker Compose 均可运行。
- [ ] 建立最小演示数据生成脚本，不依赖个人目录中的模型文件。

验收：在另一台机器执行安装、配置 `.env`、启动前后端后，可以上传一个 STL 并获得 G-code。

建议分支：`feature/dev-environment-handoff`

### M1：真实业务数据与权限

目标：移除项目、用户、任务的内存 mock 数据，业务状态可在服务重启后恢复。

任务：

- [ ] 设计并实现 SQLAlchemy 模型：`users`、`projects`、`project_files`、`tasks`、`task_artifacts`。
- [ ] 添加 Alembic 初始迁移和本地初始化命令。
- [ ] 将认证从开发期固定凭据升级为密码哈希、JWT 刷新策略和角色权限校验。
- [ ] 文件表保存对象 key、原始文件名、大小、MIME 类型、校验和、创建时间、删除时间和关联任务。
- [ ] 项目文件页面改为读取数据库元数据，不通过目录扫描承担业务事实来源。
- [ ] 增加“软删除 + 定期物理清理”的文件生命周期策略。
- [ ] 为项目、文件、任务增加用户归属校验，杜绝通过猜测 `project_id` 越权访问。

验收：重启 backend、worker、PostgreSQL 后，用户、项目、文件选择和任务历史均可恢复；不同用户不能下载或删除彼此文件。

建议分支：`feature/persistent-project-data`

### M2：异步任务与真实 TPMS 管线

目标：将耗时操作从 HTTP 请求移入 Celery，并实现第一个可用 TPMS 生成闭环。

任务：

- [ ] 定义统一任务状态：`queued`、`running`、`completed`、`failed`、`cancelled`。
- [ ] 实现 Celery 任务注册、结构化日志、重试边界和错误码。
- [ ] 增加 `model_generation` pipeline：输入模型、TPMS 类型、cell size、n、d、quality；输出 STL 与预览元数据。
- [ ] 在 `algorithms/tpms` 实现 Schwarz-P、Gyroid、Diamond 的统一参数接口。
- [ ] 在 `algorithms/mesh` 实现边界裁剪、网格修复、法向检查、非流形检测和 STL 导出。
- [ ] 后端提供任务创建、查询、取消和结果下载 API。
- [ ] 前端 TPMS 页面接入真实任务提交、进度轮询、失败提示和结果预览。

验收：用户从页面生成三种 TPMS 中任意一种，任务在 worker 中执行，生成的 STL 可被下载并再次导入 OrcaSlicer。

建议分支：`feature/async-tpms-generation`

### M3：切片任务工程化

目标：OrcaSlicer 切片成为可追踪、可取消、可复现的后台任务。

任务：

- [ ] 将同步 `run_slicing_gcode` 调用移入 Celery。
- [ ] 持久化切片请求参数、Orca 版本、打印机/工艺/材料 profile 标识和输出文件信息。
- [ ] 为每次切片生成独立输出名称，避免固定 `plate_1.gcode` 被覆盖。
- [ ] 捕获 Orca CLI 标准输出、标准错误、超时和异常退出码，并在任务详情页展示可读错误。
- [ ] 支持任务取消：停止子进程、标记任务状态、清理临时文件。
- [ ] 提取切片结果摘要：层数、预计时间、耗材、模型尺寸和文件大小。
- [ ] 对输入模型、profile 路径、命令参数实施白名单和安全校验。

验收：连续提交多个切片任务不会阻塞 API；每个任务可查看状态、参数、日志摘要和对应 G-code；失败时用户能知道是 profile、模型还是 Orca 执行问题。

建议分支：`feature/async-orca-slicing`

### M4：G-code 预览完善与性能验收

目标：在常见 Orca G-code 文件上提供稳定、准确、流畅的路径预览。

任务：

- [ ] 为不同 Orca profile 建立脱敏 G-code fixture：相对/绝对挤出、空驶、桥接、支撑、圆弧、多对象。
- [ ] 抽离 G-code 解析共享模块，消除 Worker 与主线程兜底解析的重复逻辑。
- [ ] 支持更多 `;TYPE:` 分类，并为未知类型保留可见的 `其他` 分类，禁止静默丢线。
- [ ] 增加解析统计：总行数、运动段数、各类型长度、未识别指令数、解析耗时。
- [ ] 增加路径显示选项：路径类型筛选、空驶显示、当前层/层范围、当前执行行高亮。
- [ ] 增加相机复位、俯视、正视、缩放至模型等视口操作。
- [ ] 对超过目标规模的 G-code 做性能基准；解析必须在 Worker 中完成，主线程不得构造逐段 Vue 节点。

验收：`Phone Holder` 和至少两份其他 fixture 均能准确显示；第 83–138 类 `E.0387` 简写路径不丢失；拖动层范围和行进度不卡死。

建议分支：`feature/gcode-preview-quality`

### M5：文件存储、配额与可运维性

目标：外部数据目录可安全管理，未来可平滑迁移对象存储。

任务：

- [ ] 为文件记录增加配额统计、使用量展示和文件类型限制。
- [ ] 增加临时文件清理任务：切片中间文件、失败任务输出、过期预览缓存。
- [ ] 实现项目删除时的异步数据清理和二次确认。
- [ ] 将 `LocalStorageService` 与未来 `S3StorageService` 的接口契约写成测试。
- [ ] 增加 MinIO 本地可选配置，但不作为 V1.0 默认依赖。
- [ ] 编写备份与恢复说明：数据库备份 + `TPMS-FORGE-data` 目录备份必须成对执行。

验收：用户可查看存储占用并删除自己的文件；临时目录不会无限增长；替换存储实现不需要修改业务路由。

建议分支：`feature/storage-lifecycle`

### M6：发布前质量与部署

目标：形成可演示、可部署、可回归验证的 V1.0 候选版本。

任务：

- [ ] 增加 API 集成测试：登录、上传、生成任务、切片、文件下载、文件删除、权限隔离。
- [ ] 增加前端端到端测试：关键路由、上传、任务状态、G-code 预览控制。
- [ ] 增加算法单元测试和小型网格 fixture。
- [ ] 配置 GitHub Actions：Ruff、mypy、pytest、frontend lint/typecheck/test/build。
- [ ] 配置 pre-commit：格式化、静态检查、禁止提交大文件和 `.env`。
- [ ] 补充 Docker 生产镜像、环境变量说明、日志收集和健康检查。
- [ ] 完成演示脚本：从上传模型到下载 G-code 的完整流程。

验收：干净环境可一键部署；主干每次提交自动通过检查；演示闭环不依赖本地 mock 数据。

建议分支：`feature/v1-release-readiness`

## 5. 推荐执行顺序

```text
M0 环境交接
-> M1 真实数据与权限
-> M2 异步 TPMS
-> M3 异步切片
-> M4 预览完善
-> M5 存储治理
-> M6 发布准备
```

M1 是后续工作的基础。M2 和 M3 可以在 M1 的数据库模型、任务表和文件表稳定后并行推进。M4 可以在 M3 提供稳定 G-code artifact 后持续迭代。

## 6. 分支与提交规范

开始新任务：

```bash
git checkout backend
git pull origin backend
git checkout -b feature/<topic>
```

提交格式：

```text
feat: add async Orca slicing task
fix: parse leading-decimal extrusion values
test: cover project file deletion
docs: document external storage backup
chore: update local development scripts
```

合并前必须执行：

```bash
bash scripts/dev.sh typecheck
bash scripts/dev.sh lint
bash scripts/dev.sh test
bash scripts/dev.sh build-frontend
```

不得提交：

- `.env`、token、密码、个人 Orca profile 路径。
- `TPMS-FORGE-data/` 中的用户模型、G-code、日志和临时文件。
- `node_modules/`、`.venv/`、构建产物、缓存和本地 IDE 配置。

## 7. 开发环境交接清单

```bash
git clone <repository-url>
cd TPMS-FORGE
git checkout backend
cp .env.example .env
mkdir -p ../TPMS-FORGE-data
bash scripts/dev.sh install
bash scripts/check-env.sh
```

必须由开发者自行配置：

- `ORCA_SLICER_PATH`
- `ORCA_MACHINE_PROFILE`
- `ORCA_PROCESS_PROFILE`
- 可选的 `ORCA_FILAMENT_PROFILE`
- Docker 场景下的 `TPMS_STORAGE_HOST_PATH`

启动：

```bash
docker compose up postgres redis
bash scripts/dev.sh backend
bash scripts/dev.sh worker
bash scripts/dev.sh frontend
```

访问地址：

- 前端：`http://localhost:5173`
- API 健康检查：`http://localhost:8000/api/v1/health`
- API 文档：`http://localhost:8000/docs`

## 8. 风险清单

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Orca CLI 与 profile 路径因机器不同失效 | 无法切片 | 在 M0 增加环境检查和清晰报错；不提交个人路径 |
| 大 G-code 造成浏览器卡顿 | 预览不可用 | Worker 解析、TypedArray、BufferGeometry、性能基准测试 |
| 用户文件进入 Git 或仓库目录膨胀 | 仓库难以协作 | 强制外部 `STORAGE_ROOT`，pre-commit 检查大文件 |
| 内存 mock 与真实数据库行为不一致 | 上线前返工 | 优先完成 M1，再扩展算法与任务 |
| 长任务占用 HTTP 请求 | 超时、服务不可用 | M2/M3 统一迁移 Celery |
| 文件删除导致任务结果失效 | 下载/预览报错 | artifact 状态、软删除、任务详情提示和异步清理 |

## 9. V1.0 完成定义

以下条件同时满足时，V1.0 可以进入演示或试用：

- 用户可注册/登录并只能访问自己的项目和文件。
- 用户可上传、选择、预览、下载和删除 STL/OBJ。
- 用户可创建 TPMS 任务，获得有效 STL 输出。
- 用户可对原始模型或 TPMS 模型提交 Orca 切片任务。
- 用户可查看任务状态、错误和输出 G-code。
- 用户可在网页中逐层、逐行查看真实 G-code 路径，并下载结果。
- 大文件不进入 Git，文件与元数据都可备份和恢复。
- 自动检查和核心测试在干净环境中通过。
