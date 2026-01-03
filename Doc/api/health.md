# 健康检查接口
# Health Check API

> **端点**: `GET /api/v1/health`  
> **状态**: ✅ 已确定（示例接口）  
> **最后更新**: 2024-12-17

---

## 接口概述

健康检查接口用于验证后端服务是否正常运行。这是最简单的接口，可作为其他接口的设计参考。

**用途**：
- 前端检测后端是否可用
- 运维监控服务状态
- 调试时快速测试连接

---

## 请求

### 基本信息
```
GET /api/v1/health
```

### 请求参数
无

### 请求示例
```bash
# 使用 curl
curl http://localhost:5000/api/v1/health

# 使用 JavaScript
fetch('http://localhost:5000/api/v1/health')
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 响应

### 成功响应（200 OK）

```json
{
  "status": "healthy",
  "timestamp": "2024-12-17T10:30:45",
  "version": "1.0.0",
  "data_loaded": true,
  "total_routes": 359
}
```

### 响应字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | ✅ | 服务状态：`healthy`, `degraded`, `unhealthy` |
| `timestamp` | string | ✅ | 当前服务器时间（ISO 8601） |
| `version` | string | ✅ | API 版本号 |
| `data_loaded` | boolean | ⭕ | 数据是否已加载 |
| `total_routes` | number | ⭕ | 已加载的线路数量 |

---

## 错误响应

健康检查接口通常不会返回错误，除非服务完全宕机。

### 服务不可用（503 Service Unavailable）

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "服务暂时不可用"
  }
}
```

---

## 实现示例

### 后端实现（Python/Flask）

```python
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/api/v1/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'data_loaded': True,
        'total_routes': 359
    })

if __name__ == '__main__':
    app.run(port=5000)
```

### 前端调用（JavaScript）

```javascript
// api.js
class TransitAPI {
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      if (!response.ok) {
        throw new Error('Health check failed');
      }
      return await response.json();
    } catch (error) {
      console.error('Health check error:', error);
      return null;
    }
  }
}

// 使用
const api = new TransitAPI('http://localhost:5000/api/v1');
const health = await api.checkHealth();
if (health && health.status === 'healthy') {
  console.log('✅ Backend is ready');
}
```

---

## 测试

### 测试清单

- [ ] 服务启动后能正常响应
- [ ] 返回状态码为 200
- [ ] 响应格式为 JSON
- [ ] 包含所有必填字段
- [ ] timestamp 格式正确

### 测试命令

```bash
# 测试接口可用性
curl -I http://localhost:5000/api/v1/health

# 查看完整响应
curl http://localhost:5000/api/v1/health

# 格式化输出（需要 jq）
curl http://localhost:5000/api/v1/health | jq
```

### 预期结果

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "timestamp": "2024-12-17T10:30:45",
  "version": "1.0.0"
}
```

---

## 单元测试

### Pytest 示例

```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_returns_200(client):
    """测试健康检查返回 200"""
    response = client.get('/api/v1/health')
    assert response.status_code == 200

def test_health_returns_json(client):
    """测试返回 JSON 格式"""
    response = client.get('/api/v1/health')
    assert response.content_type == 'application/json'

def test_health_has_required_fields(client):
    """测试包含必填字段"""
    response = client.get('/api/v1/health')
    data = response.get_json()
    
    assert 'status' in data
    assert 'timestamp' in data
    assert 'version' in data
    assert data['status'] == 'healthy'
```

---

## 性能要求

- **响应时间**: < 50ms
- **并发支持**: 1000 req/s
- **可用性**: 99.9%

---

## 变更历史

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2024-12-17 | 1.0 | 初始版本，作为接口设计示例 | Jingren |

---

## 相关文档

- [API 概览](./README.md)
- [后端开发指南](../../BACKEND_GUIDE.md)
- [测试与调试](../../TESTING_DEBUG.md)

---

**注意**: 这是一个示例文档，其他接口可以参考这个格式编写。
