# Git 协作与开发规范
# Git Workflow & Development Standards v1.0

> **目标读者**: 全体开发者（特别是 Git 初学者）  
> **作用**: 统一代码管理和协作流程  
> **语言**: **推荐使用中文编写 Commit 消息**，降低团队协作难度

---

## ⚠️ 重要说明

考虑到小组成员协作的实际情况，本项目 **推荐使用中文编写 Commit 消息**。

**理由**：
- ✅ 降低理解难度，提高协作效率
- ✅ 减少英文表达错误，避免歧义
- ✅ 更贴近中文思维习惯
- ✅ 加快 Code Review 速度

**原则**：
- 中文为主，英文可选
- Type 和 Scope 保持英文（如 `feat`, `fix`, `api`, `map`）
- 主题和详细描述使用中文
- 如果团队成员更习惯英文，也可以使用英文

---

## 目录
- [Git 基础概念](#git-基础概念)
- [分支策略](#分支策略)
- [Commit 规范](#commit-规范)
- [代码审查流程](#代码审查流程)
- [单元测试规范](#单元测试规范)
- [常见问题](#常见问题)

---

## Git 基础概念

### 什么是 Git？
Git 是一个分布式版本控制系统，可以：
- 记录代码的每次修改
- 多人协作开发
- 回滚到任意历史版本
- 创建分支独立开发功能

### 核心概念速查

```
工作区 (Working Directory)
   ↓ git add
暂存区 (Staging Area)
   ↓ git commit
本地仓库 (Local Repository)
   ↓ git push
远程仓库 (Remote Repository)
```

### 必备命令

```bash
# 克隆项目
git clone <repository-url>

# 查看状态
git status

# 查看当前分支
git branch

# 查看提交历史
git log --oneline --graph

# 拉取最新代码
git pull origin main
```

---

## 分支策略

本项目采用 **Git Flow** 简化版，包含以下分支：

### 分支类型

```
main (主分支)
├── develop (开发分支)
│   ├── feature/xxx (功能分支)
│   ├── bugfix/xxx (修复分支)
│   └── hotfix/xxx (紧急修复)
```

### 1. main 分支
- **用途**: 生产环境代码，随时可部署
- **保护**: 受保护，不能直接 push
- **更新**: 仅通过 Pull Request 合并
- **命名**: 固定为 `main`

### 2. develop 分支
- **用途**: 开发主分支，集成所有功能
- **保护**: 受保护，不能直接 push
- **更新**: 通过 Pull Request 合并 feature 分支
- **命名**: 固定为 `develop`

### 3. feature 分支（功能开发）
- **用途**: 开发新功能
- **从哪里创建**: 从 `develop` 分支创建
- **合并到哪里**: 合并回 `develop`
- **命名规范**: `feature/<功能描述>`
- **生命周期**: 功能完成后删除

**示例**:
```
feature/api-metadata      # 实现元数据 API
feature/map-rendering     # 实现地图渲染
feature/timeline-control  # 实现时间轴控制
```

### 4. bugfix 分支（Bug 修复）
- **用途**: 修复 develop 分支的 Bug
- **从哪里创建**: 从 `develop` 分支创建
- **合并到哪里**: 合并回 `develop`
- **命名规范**: `bugfix/<Bug描述>`
- **生命周期**: 修复完成后删除

**示例**:
```
bugfix/cors-error         # 修复 CORS 错误
bugfix/map-not-loading    # 修复地图不加载
bugfix/timeline-freeze    # 修复时间轴卡顿
```

### 5. hotfix 分支（紧急修复）
- **用途**: 修复生产环境紧急 Bug
- **从哪里创建**: 从 `main` 分支创建
- **合并到哪里**: 同时合并到 `main` 和 `develop`
- **命名规范**: `hotfix/<紧急Bug描述>`
- **生命周期**: 修复完成后删除

**示例**:
```
hotfix/api-crash          # 修复 API 崩溃
hotfix/data-leak          # 修复数据泄漏
```

---

## 分支操作实战

### 场景 1: 开发新功能（后端 API）

```bash
# 1. 确保在 develop 分支且是最新的
git checkout develop
git pull origin develop

# 2. 创建 feature 分支
git checkout -b feature/api-passenger-flow

# 3. 开发功能...
# 编辑 app.py，添加 /passenger-flow 端点

# 4. 查看修改了哪些文件
git status

# 5. 添加修改到暂存区
git add app.py

# 或者添加所有修改
git add .

# 6. 提交（遵循 Commit 规范）
git commit -m "feat(api): 实现客流数据接口

- 添加 GET /api/v1/passenger-flow 端点
- 支持 datetime 和 types 查询参数
- 添加缺少参数的错误处理
- 完成单元测试

关闭 #12"

# 7. 推送到远程仓库
git push origin feature/api-passenger-flow

# 8. 在 GitHub/GitLab 创建 Pull Request
# 从 feature/api-passenger-flow → develop

# 9. 代码审查通过后，在线上合并

# 10. 合并后删除本地分支
git checkout develop
git pull origin develop
git branch -d feature/api-passenger-flow
```

### 场景 2: 修复 Bug

```bash
# 1. 从 develop 创建 bugfix 分支
git checkout develop
git pull origin develop
git checkout -b bugfix/cors-error

# 2. 修复 Bug...
# 编辑 app.py，配置 CORS

# 3. 提交
git add app.py
git commit -m "fix(api): 解决 CORS 错误

- 添加 Flask-CORS 配置
- 允许来自 localhost:8000 的请求
- 使用 curl 和浏览器测试

修复 #23"

# 4. 推送并创建 Pull Request
git push origin bugfix/cors-error

# 5. 合并后删除分支
git checkout develop
git pull origin develop
git branch -d bugfix/cors-error
```

### 场景 3: 同步远程更新

```bash
# 在自己的 feature 分支上
git checkout feature/my-feature

# 拉取 develop 最新代码
git pull origin develop

# 如果有冲突，解决冲突后
git add .
git commit -m "merge: 同步 develop 分支"
git push origin feature/my-feature
```

---

## Commit 规范

本项目采用 **Conventional Commits** 规范，但考虑到团队协作的实际情况，**推荐使用中文编写 Commit 消息**，降低理解和编写难度。

### Commit 消息格式

```
<type>(<scope>): <主题>

<详细描述>

<脚注>
```

**中文示例（推荐）**:
```
feat(api): 添加客流数据接口

- 实现 GET /api/v1/passenger-flow 接口
- 支持 datetime 和 types 查询参数
- 添加参数校验和错误处理
- 完成单元测试，覆盖率 95%

关闭 #12
```

**英文示例（可选）**:
```
feat(api): add passenger-flow endpoint

- Implement GET /api/v1/passenger-flow
- Support datetime and types parameters
- Add error handling for invalid inputs
- Add unit tests for all edge cases

Closes #12
```

### Type（类型）

| Type | 说明 | 中文示例 | 英文示例（可选） |
|------|------|----------|------------------|
| `feat` | 新功能 | `feat(api): 添加线路接口` | `feat(api): add routes endpoint` |
| `fix` | Bug 修复 | `fix(map): 修复坐标转换问题` | `fix(map): resolve coordinate conversion` |
| `docs` | 文档变更 | `docs(readme): 更新安装说明` | `docs(readme): update installation guide` |
| `style` | 代码格式 | `style(api): 使用 black 格式化代码` | `style(api): format with black` |
| `refactor` | 重构 | `refactor(map): 提取颜色映射逻辑` | `refactor(map): extract color scale logic` |
| `perf` | 性能优化 | `perf(api): 添加数据缓存` | `perf(api): add data caching` |
| `test` | 添加测试 | `test(api): 添加客流接口测试` | `test(api): add passenger-flow tests` |
| `chore` | 构建/工具 | `chore(deps): 更新 flask 到 3.0.1` | `chore(deps): update flask to 3.0.1` |
| `ci` | CI/CD | `ci: 添加 GitHub Actions 工作流` | `ci: add github actions workflow` |
| `revert` | 回滚 | `revert: 回滚"添加功能X"` | `revert: revert "feat: add feature X"` |

### Scope（范围）

指明修改影响的模块或文件：

**后端 Scope**:
```
api         # API 端点
data        # 数据处理
config      # 配置文件
tests       # 测试
scripts     # 脚本
```

**前端 Scope**:
```
map         # 地图模块
timeline    # 时间轴模块
controls    # 控制器模块
legend      # 图例模块
api         # API 封装
ui          # UI 组件
styles      # 样式
```

**通用 Scope**:
```
docs        # 文档
deps        # 依赖
build       # 构建
deploy      # 部署
```

### Subject（主题/简短描述）

**中文写法**:
- 使用动宾结构（"添加XX"、"修复XX"、"优化XX"）
- 不要句号或感叹号
- 限制在 50 字符内

**英文写法（如果使用）**:
- 使用祈使句（"add" 而不是 "added"）
- 不要大写首字母
- 不要以句号结尾

**好的中文示例**:
```
feat(api): 添加健康检查接口
fix(map): 修复图层切换问题
docs(api): 更新客流接口示例
```

**好的英文示例**:
```
feat(api): add health check endpoint
fix(map): resolve layer toggle issue
docs(api): update passenger-flow examples
```

**不好的示例**:
```
feat(api): 添加了健康检查接口。        ❌ (过去式 + 句号)
fix(map): 修复 bug                    ❌ (不清晰)
更新 README                          ❌ (没有 type 和 scope)
feat(api): Added health endpoint.    ❌ (过去式 + 大写 + 句号)
```

### Body（详细描述）

- 与主题空一行
- 解释 "是什么" 和 "为什么"，而不是 "怎么做"
- 使用列表格式（中文或英文都可以）
- 限制每行 72 字符

**中文示例（推荐）**:
```
feat(api): 添加客流数据接口

该接口提供所有交通线路的实时客流数据。

- 支持 ISO 8601 格式的 datetime 查询参数
- 支持 types 过滤器（mrt、lrt、bus）
- 返回包含利用率的聚合客流数据
- 添加完善的错误处理
- 完成单元测试，覆盖率 95%

性能：典型查询响应时间 < 300ms
```

**英文示例（可选）**:
```
feat(api): add passenger-flow endpoint

This endpoint provides real-time passenger flow data for all transit routes.

- Support datetime query parameter in ISO 8601 format
- Support types filter (mrt, lrt, bus)
- Return aggregated flow data with utilization
- Add comprehensive error handling
- Add unit tests with 95% coverage

Performance: Response time < 300ms for typical queries
```

### Footer（脚注）

用于：
- 关联 Issue：`关闭 #123`、`修复 #456`、`参考 #789`
  - 或英文：`Closes #123`, `Fixes #456`, `Refs #789`
- Breaking Changes：`破坏性变更: ...` 或 `BREAKING CHANGE: ...`

**中文示例（推荐）**:
```
feat(api): 重新设计客流数据响应格式

破坏性变更：响应格式已修改

修改前：
{
  "data": [{"id": "NS1", "passengers": 1000}]
}

修改后：
{
  "data": [{"route_id": "NS1", "flow": 1000, "capacity": 12000}]
}

迁移指南：https://...

关闭 #45
```

**英文示例（可选）**:
```
feat(api): redesign passenger-flow response format

BREAKING CHANGE: The response format has changed.

Before:
{
  "data": [{"id": "NS1", "passengers": 1000}]
}

After:
{
  "data": [{"route_id": "NS1", "flow": 1000, "capacity": 12000}]
}

Migration guide: https://...

Closes #45
```

---

## Commit 示例集合

以下是各种场景的 Commit 示例，**中文和英文都可以**，团队内部推荐使用中文。

### 1. 添加新功能

**中文版（推荐）**:
```bash
git commit -m "feat(api): 实现元数据接口

- 添加 GET /api/v1/metadata 接口
- 返回系统配置和时间范围
- 启动时从 JSON 文件加载元数据
- 添加响应格式验证

关闭 #5"
```

**英文版（可选）**:
```bash
git commit -m "feat(api): implement metadata endpoint

- Add GET /api/v1/metadata
- Return system configuration and temporal range
- Load metadata from JSON file on startup
- Add response validation

Closes #5"
```

### 2. 修复 Bug

**中文版（推荐）**:
```bash
git commit -m "fix(map): 修正 GeoJSON 坐标顺序

坐标原本是 [lat, lng] 格式，但 GeoJSON 要求 [lng, lat]，
导致所有线路在地图上位置错误。

- 在 loadRoutes 方法中转换坐标
- 添加坐标验证
- 更新单元测试

修复 #18"
```

**英文版（可选）**:
```bash
git commit -m "fix(map): correct GeoJSON coordinate order

The coordinates were in [lat, lng] format but GeoJSON
requires [lng, lat]. This caused all routes to be
misplaced on the map.

- Convert coordinates in loadRoutes method
- Add coordinate validation
- Update unit tests

Fixes #18"
```

### 3. 文档更新

**中文版（推荐）**:
```bash
git commit -m "docs(api): 添加客流接口使用示例

- 添加 curl 示例
- 添加响应格式说明
- 说明错误代码
- 添加性能说明"
```

**英文版（可选）**:
```bash
git commit -m "docs(api): add examples for passenger-flow endpoint

- Add curl examples
- Add response format explanation
- Document error codes
- Add performance notes"
```

### 4. 重构代码

**中文版（推荐）**:
```bash
git commit -m "refactor(map): 提取颜色映射管理器

- 创建 ColorScaleManager 类
- 将 D3 色标逻辑移到独立文件
- 提高代码可测试性
- 无功能变更"
```

**英文版（可选）**:
```bash
git commit -m "refactor(map): extract color scale manager

- Create ColorScaleManager class
- Move D3 scale logic to separate file
- Improve code testability
- No functional changes"
```

### 5. 性能优化

**中文版（推荐）**:
```bash
git commit -m "perf(api): 添加响应缓存

- 实现 LRU 缓存用于客流查询
- 缓存大小：100 条记录
- 响应时间从 450ms 降到 80ms

关闭 #34"
```

**英文版（可选）**:
```bash
git commit -m "perf(api): add response caching

- Implement LRU cache for passenger-flow queries
- Cache size: 100 entries
- Reduce response time from 450ms to 80ms

Closes #34"
```

### 6. 添加测试

**中文版（推荐）**:
```bash
git commit -m "test(api): 添加客流接口测试

- 测试有效请求
- 测试缺少参数
- 测试无效时间格式
- 测试无效交通类型
- 覆盖率：98%"
```

**英文版（可选）**:
```bash
git commit -m "test(api): add passenger-flow endpoint tests

- Test valid requests
- Test missing parameters
- Test invalid datetime format
- Test invalid transit types
- Coverage: 98%"
```

### 7. 依赖更新

**中文版（推荐）**:
```bash
git commit -m "chore(deps): 更新 pandas 到 2.1.4

- 修复安全漏洞 CVE-2024-xxxxx
- 更新 requirements.txt
- 验证所有测试通过"
```

**英文版（可选）**:
```bash
git commit -m "chore(deps): update pandas to 2.1.4

- Fix security vulnerability CVE-2024-xxxxx
- Update requirements.txt
- Verify all tests pass"
```

### 8. 样式调整

**中文版（推荐）**:
```bash
git commit -m "style(frontend): 改进时间轴按钮布局

- 增加按钮间距
- 添加悬停效果
- 改进移动端响应式
- 无功能变更"
```

**英文版（可选）**:
```bash
git commit -m "style(frontend): improve timeline button layout

- Increase button spacing
- Add hover effects
- Improve mobile responsiveness
- No functional changes"
```

---

## 代码审查流程

### Pull Request（PR）创建清单

在创建 PR 前，请确认：

- [ ] 代码已在本地测试通过
- [ ] 遵循 Commit 规范
- [ ] 添加了必要的注释
- [ ] 更新了相关文档
- [ ] 添加或更新了单元测试
- [ ] 所有测试通过
- [ ] 没有遗留的 `console.log` 或调试代码
- [ ] 代码风格一致

### PR 标题格式

与 Commit 消息格式相同，推荐使用中文：

**中文示例（推荐）**:
```
feat(api): 添加客流数据接口
fix(map): 修复坐标转换问题
docs(readme): 更新安装说明
```

**英文示例（可选）**:
```
feat(api): add passenger-flow endpoint
fix(map): resolve coordinate conversion issue
docs(readme): update installation guide
```

### PR 描述模板

```markdown
## 变更类型
- [ ] 新功能 (feature)
- [ ] Bug 修复 (bugfix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 其他

## 变更内容
简要描述这个 PR 做了什么。

## 相关 Issue
Closes #123

## 测试
- [ ] 本地测试通过
- [ ] 添加了单元测试
- [ ] 更新了集成测试

## 截图（如果适用）
（添加前后对比截图）

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 文档已更新
- [ ] 测试已添加/更新
- [ ] CI 通过
```

### 代码审查标准

**审查者需要检查**:

1. **功能正确性**
   - 代码是否实现了预期功能？
   - 是否有边界情况未处理？

2. **代码质量**
   - 是否遵循项目规范？
   - 是否有重复代码？
   - 命名是否清晰？

3. **测试覆盖**
   - 是否有足够的测试？
   - 测试是否覆盖边界情况？

4. **性能影响**
   - 是否有性能问题？
   - 是否需要优化？

5. **文档完整性**
   - API 变更是否更新了文档？
   - 是否需要更新 README？

### 审查反馈示例

**好的反馈**:
```
建议: 在 line 45, 可以使用 list comprehension 简化代码:

当前:
result = []
for item in data:
    result.append(item.value)

建议改为:
result = [item.value for item in data]
```

**不好的反馈**:
```
这段代码写得不好。❌（不具体）
```

---

## 单元测试规范

### 后端单元测试（必须）

后端使用 **pytest** 进行单元测试。

#### 测试文件结构

```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_api.py          # API 端点测试
│   ├── test_data.py         # 数据处理测试
│   └── test_utils.py        # 工具函数测试
```

#### 测试命名规范

```python
# 测试文件: test_<模块名>.py
# 测试类: Test<功能名>
# 测试方法: test_<场景>_<预期结果>

# 好的例子
def test_passenger_flow_valid_request_returns_200():
    """测试有效请求返回 200"""
    pass

def test_passenger_flow_missing_datetime_returns_400():
    """测试缺少 datetime 参数返回 400"""
    pass

def test_passenger_flow_invalid_datetime_returns_400():
    """测试无效 datetime 格式返回 400"""
    pass
```

#### 测试示例

```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_returns_200(self, client):
        """测试健康检查返回 200"""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
    
    def test_health_returns_valid_json(self, client):
        """测试健康检查返回有效 JSON"""
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        assert 'status' in data
        assert 'version' in data
        assert data['status'] == 'healthy'

class TestPassengerFlowEndpoint:
    """客流数据端点测试"""
    
    def test_valid_request_returns_200(self, client):
        """测试有效请求"""
        response = client.get(
            '/api/v1/passenger-flow',
            query_string={'datetime': '2024-01-01T08:00:00', 'types': 'mrt'}
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'data' in data
        assert 'timestamp' in data
    
    def test_missing_datetime_returns_400(self, client):
        """测试缺少 datetime 参数"""
        response = client.get('/api/v1/passenger-flow')
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_PARAM'
    
    def test_invalid_datetime_returns_400(self, client):
        """测试无效 datetime 格式"""
        response = client.get(
            '/api/v1/passenger-flow',
            query_string={'datetime': 'invalid-date'}
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_DATETIME'
    
    def test_invalid_types_returns_400(self, client):
        """测试无效交通类型"""
        response = client.get(
            '/api/v1/passenger-flow',
            query_string={'datetime': '2024-01-01T08:00:00', 'types': 'invalid'}
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_TYPE'
```

#### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_api.py

# 运行特定测试
pytest tests/test_api.py::TestHealthEndpoint::test_health_returns_200

# 显示详细输出
pytest -v

# 显示测试覆盖率
pytest --cov=app --cov-report=html

# 只运行失败的测试
pytest --lf
```

#### 测试覆盖率要求

- **核心 API 端点**: 90% 以上
- **数据处理逻辑**: 80% 以上
- **工具函数**: 95% 以上

---

### 前端单元测试（推荐但非必须）

前端可以使用 **Jest** 进行单元测试，但考虑到时间限制，**前端测试为可选项**。

#### 如果要写前端测试

```javascript
// tests/colorScale.test.js
import { ColorScaleManager } from '../js/colorScale.js';

describe('ColorScaleManager', () => {
  let manager;
  
  beforeEach(() => {
    manager = new ColorScaleManager({
      mrt: { scheme: 'Blues', domain: [0, 12000] }
    });
  });
  
  test('should return color for valid type and value', () => {
    const color = manager.getColor('mrt', 6000);
    expect(color).toBeTruthy();
    expect(typeof color).toBe('string');
  });
  
  test('should return domain for valid type', () => {
    const domain = manager.getDomain('mrt');
    expect(domain).toEqual([0, 12000]);
  });
});
```

#### 运行前端测试

```bash
# 安装 Jest
npm install --save-dev jest

# 运行测试
npm test

# 查看覆盖率
npm test -- --coverage
```

---

## 常见问题

### Q1: 如何撤销最后一次 commit？

```bash
# 保留修改，撤销 commit
git reset --soft HEAD~1

# 丢弃修改，撤销 commit
git reset --hard HEAD~1

# 如果已经 push，需要强制推送（谨慎！）
git push origin feature/my-feature --force
```

### Q2: 如何修改最后一次 commit 消息？

```bash
# 修改最后一次 commit 消息
git commit --amend -m "fix(api): correct commit message"

# 如果已经 push，需要强制推送
git push origin feature/my-feature --force
```

### Q3: 如何解决冲突？

```bash
# 1. 拉取最新代码时发生冲突
git pull origin develop
# 出现冲突提示

# 2. 查看冲突文件
git status

# 3. 打开文件，手动解决冲突
# 文件中会有类似标记：
# <<<<<<< HEAD
# 你的修改
# =======
# 别人的修改
# >>>>>>> branch-name

# 4. 解决冲突后，标记为已解决
git add <冲突文件>

# 5. 提交
git commit -m "merge: resolve conflicts with develop"
```

### Q4: 如何删除远程分支？

```bash
# 删除远程分支
git push origin --delete feature/my-feature

# 删除本地分支
git branch -d feature/my-feature

# 强制删除本地分支（如果有未合并的修改）
git branch -D feature/my-feature
```

### Q5: 如何查看某个文件的修改历史？

```bash
# 查看文件修改历史
git log --follow app.py

# 查看每次修改的详细内容
git log -p app.py

# 查看谁修改了哪一行
git blame app.py
```

### Q6: 如何暂存当前修改？

```bash
# 暂存当前修改（切换分支时很有用）
git stash

# 查看暂存列表
git stash list

# 恢复最近的暂存
git stash pop

# 恢复指定的暂存
git stash apply stash@{0}
```

---

## Git 工作流总结图

```
┌─────────────────────────────────────────────────────────┐
│                         main                            │
│                    (生产环境)                            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ hotfix (紧急修复)
                       │
┌──────────────────────┴──────────────────────────────────┐
│                       develop                            │
│                    (开发主分支)                          │
└──────┬───────────────┬───────────────┬──────────────────┘
       │               │               │
       │ feature       │ feature       │ bugfix
       │ (功能1)       │ (功能2)       │ (修复)
       │               │               │
       ↓               ↓               ↓
   [完成]          [开发中]         [完成]
       │               │               │
       └───────────────┴───────────────┘
                       │
                   合并到 develop
```

---

## 最佳实践

1. **频繁提交，小步迭代**
   - 每完成一个小功能就 commit
   - 避免一次 commit 包含太多修改

2. **提交前先拉取**
   ```bash
   git pull origin develop
   git push origin feature/my-feature
   ```

3. **遵循 Commit 规范**
   - 使用工具检查：`commitlint`
   - 使用 Git hooks 自动验证

4. **代码审查认真对待**
   - 审查别人的代码是学习的好机会
   - 接受别人的建议虚心改进

5. **测试先行**
   - 写代码前先写测试（TDD）
   - 确保所有测试通过再提交

6. **及时删除已合并的分支**
   - 保持仓库整洁
   - 避免混淆

---

## 推荐工具

### Git 图形化客户端
- **GitHub Desktop**: 适合初学者
- **GitKraken**: 功能强大
- **SourceTree**: 免费且功能全面

### Commit 消息检查
```bash
# 安装 commitlint
npm install --save-dev @commitlint/cli @commitlint/config-conventional

# 配置 Git hook
npm install --save-dev husky
npx husky install
npx husky add .husky/commit-msg 'npx --no-install commitlint --edit "$1"'
```

### 代码格式化
```bash
# Python (Black)
pip install black
black app.py

# JavaScript (Prettier)
npm install --save-dev prettier
npx prettier --write "**/*.js"
```

---

## 快速参考卡片

### 常用命令

```bash
# 查看状态
git status

# 创建分支
git checkout -b feature/new-feature

# 切换分支
git checkout develop

# 提交代码
git add .
git commit -m "feat(api): 添加新接口"
git push origin feature/new-feature

# 拉取更新
git pull origin develop

# 查看日志
git log --oneline --graph

# 删除分支
git branch -d feature/old-feature
```

### Commit 类型速查

```
feat     - 新功能
fix      - Bug 修复
docs     - 文档
style    - 格式
refactor - 重构
perf     - 性能优化
test     - 测试
chore    - 构建/工具
```

---

**完成学习后**: 请阅读 `DEVELOPMENT_WORKFLOW.md` 开始开发。

**需要帮助？**: 查看 `AI_COLLABORATION.md` 中的协作指南。
