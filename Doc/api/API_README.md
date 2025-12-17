# API 接口规范
# API Specification v1.0

> **状态**: 🚧 设计中（开发过程中调整）  
> **最后更新**: 2024-12-17

---

## 📋 文档说明

本文档为 **API 设计指南和示例**，不是最终确定的规范。

**开发原则**：
- 在开发过程中根据实际需求调整 API
- 前后端协商确定最终的接口格式
- 以下示例仅作为参考，不强制遵守

**文档结构**：
```
docs/api/
├── README.md          # 本文件 - API 概览
├── health.md          # 健康检查接口（示例）
├── metadata.md        # 系统元数据接口（待开发）
├── routes.md          # 线路数据接口（待开发）
└── passenger-flow.md  # 客流数据接口（待开发）
```

---

## 基础约定

### API Base URL
```
http://localhost:5000/api/v1
```

### 通用规范
- **请求方法**: 主要使用 GET（查询数据）
- **响应格式**: JSON
- **字符编码**: UTF-8
- **时间格式**: ISO 8601 (`YYYY-MM-DDTHH:mm:ss`)
- **坐标格式**: GeoJSON 标准 ([经度, 纬度])

### 错误响应格式（建议）
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "可读的错误信息",
    "details": {}
  }
}
```

---

## 核心接口列表

| 端点 | 方法 | 用途 | 状态 | 文档 |
|------|------|------|------|------|
| `/health` | GET | 健康检查 | ✅ 示例已完成 | [health.md](./health.md) |
| `/metadata` | GET | 系统元数据 | 📝 待设计 | [metadata.md](./metadata.md) |
| `/routes` | GET | 线路信息 | 📝 待设计 | [routes.md](./routes.md) |
| `/passenger-flow` | GET | 客流数据 | 📝 待设计 | [passenger-flow.md](./passenger-flow.md) |

---

## 开发流程

### 1. 设计阶段（当前）
- [ ] 后端开发者设计 API 草案
- [ ] 在对应的 `.md` 文件中编写接口文档
- [ ] 包含：请求参数、响应格式、错误处理

### 2. 协商阶段
- [ ] 前端开发者审查 API 设计
- [ ] 提出修改建议（在文档中标注）
- [ ] 前后端达成一致

### 3. 实现阶段
- [ ] 后端实现接口
- [ ] 前端对接测试
- [ ] 根据实际情况调整

### 4. 确定阶段
- [ ] 测试通过后，标记为 ✅ 已确定
- [ ] 锁定接口，后续不再大改

---

## API 设计建议

### 命名规范
- 使用小写字母和连字符：`/passenger-flow` ✅
- 避免驼峰命名：`/passengerFlow` ❌
- 使用复数表示集合：`/routes` ✅

### 参数设计
- 必填参数尽量少（降低使用难度）
- 提供合理的默认值
- 参数名清晰明确

### 响应设计
- 保持响应结构简单
- 避免过度嵌套
- 关键字段放在顶层

### 错误处理
- 使用合适的 HTTP 状态码
- 提供清晰的错误信息
- 包含足够的调试信息

---

## 示例：健康检查接口

详细文档见 [health.md](./health.md)

**快速预览**：
```bash
# 请求
GET /api/v1/health

# 响应
{
  "status": "healthy",
  "timestamp": "2024-12-17T10:30:45",
  "version": "1.0.0"
}
```

---

## 前后端协作

### 后端开发者
1. 在 `docs/api/` 下创建对应的 `.md` 文件
2. 编写 API 设计文档（参考 `health.md` 格式）
3. 通知前端开发者审查
4. 实现接口并提供测试 URL

### 前端开发者
1. 审查 API 文档，提出修改建议
2. 可以先使用 Mock 数据开发
3. 后端接口就绪后对接测试
4. 发现问题及时反馈

### 变更管理
- 小改动：直接修改文档并通知
- 大改动：讨论后再修改
- 记录变更历史在文档末尾

---

## 快速开始

### 后端开发者
```bash
# 1. 设计新接口
cp docs/api/health.md docs/api/new-endpoint.md
# 编辑 new-endpoint.md

# 2. 实现接口
# 在 backend/api/ 下创建对应文件

# 3. 测试接口
curl http://localhost:5000/api/v1/new-endpoint
```

### 前端开发者
```bash
# 1. 查看 API 文档
cat docs/api/new-endpoint.md

# 2. 创建 Mock 数据
# 在 frontend/data/mockData.js 中添加

# 3. 对接真实 API
# 修改 config.js: USE_MOCK_DATA = false
```

---

## 变更日志

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2024-12-17 | 1.0 | 创建 API 文档结构，完成健康检查示例 | Jingren |

---

**下一步**: 
- 后端：参考 `health.md` 设计其他接口
- 前端：审查设计，准备 Mock 数据
