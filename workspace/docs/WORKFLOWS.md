# ComfyGram 工作流配置指南

ComfyGram 使用 ComfyUI 的 JSON 工作流来定义图像生成任务。

## 目录

- [预配置工作流](#预配置工作流)
- [自定义工作流](#自定义工作流)
- [工作流参数](#工作流参数)
- [LoRA 配置](#lora-配置)
- [提示词模板](#提示词模板)

---

## 预配置工作流

ComfyGram 包含以下预配置工作流：

### Flux 文生图

**文件**: `workflows/flux_t2i_api.json`

**用途**: 文本到图像生成

**示例**:
```
/t2i 一只猫在阳光下
--workflow flux_t2i
```

---

### Flux 图生图

**文件**: `workflows/flux_i2i_api.json`

**用途**: 图像到图像转换

**示例**:
```
[i2i] 转换为油画风格
--workflow flux_i2i
```

---

### IP-Adapter

**文件**: `workflows/flux_i2i_ipadapter_mask_api.json`

**用途**: 使用参考图像进行精确控制

**示例**:
```
[i2i] 保持构图，改变风格
--workflow ipadapter
```

---

### 风格迁移

**文件**: `workflows/flux_i2i_style_api.json`

**用途**: 艺术风格迁移

**支持的风格**:
- anime（动漫）
- oil_painting（油画）
- watercolor（水彩）
- sketch（素描）
- cyberpunk（赛博朋克）

---

### 图生视频

**文件**: `workflows/wan_i2v_api.json`

**用途**: 将图像转换为短视频

**示例**:
```
/i2v 生成 3 秒视频
--duration 3
--fps 8
```

---

## 自定义工作流

### 创建自定义工作流

#### 步骤 1：在 ComfyUI 中设计工作流

1. 打开 ComfyUI 网页界面
2. 构建你的工作流
3. 测试直到满意
4. 点击 "Save (API Format)" 保存

#### 步骤 2：添加到 ComfyGram

```bash
# 将 JSON 文件复制到工作流目录
cp your_workflow.json /path/to/comfygram/workspace/workflows/
```

#### 步骤 3：注册工作流

编辑 `workspace/workflows/registry.json`：

```json
{
  "workflows": [
    {
      "name": "my_custom_workflow",
      "display_name": "我的自定义工作流",
      "description": "做一些很酷的事情",
      "file": "your_workflow.json",
      "category": "custom",
      "parameters": {
        "required": ["prompt"],
        "optional": ["steps", "cfg", "seed"]
      }
    }
  ]
}
```

#### 步骤 4：使用自定义工作流

```
/custom my_custom_workflow 一张美丽的图片
```

---

## 工作流参数

### 标准参数

所有工作流都支持以下参数：

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `prompt` | string | 文本描述 | - |
| `steps` | int | 生成步数 | 20 |
| `cfg` | float | CFG 强度 | 7.0 |
| `seed` | int | 随机种子 | -1 (随机) |
| `width` | int | 图像宽度 | 1024 |
| `height` | int | 图像高度 | 1024 |
| `batch_size` | int | 批量大小 | 1 |

---

### 工作流特定参数

每个工作流可以定义自己的额外参数。

**示例**：

```json
{
  "workflow_params": {
    "denoise": {
      "type": "float",
      "default": 0.9,
      "description": "去噪强度"
    },
    "sampler": {
      "type": "string",
      "default": "euler",
      "options": ["euler", "ddim", "dpm++"]
    }
  }
}
```

---

## LoRA 配置

### LoRA 注册表

编辑 `workspace/configs/lora_registry.json`：

```json
{
  "loras": {
    "anime_lora": {
      "file": "anime_style_v1.safetensors",
      "strength": 0.8,
      "trigger_word": "anime_style",
      "description": "动漫风格 LoRA"
    },
    "portrait_lora": {
      "file": "portrait_enhancer.safetensors",
      "strength": 0.7,
      "trigger_word": "portrait",
      "description": "人像增强 LoRA"
    }
  }
}
```

---

### 使用 LoRA

**方式 1：在提示词中使用**

```
/t2i anime_style 一个可爱的女孩
```

**方式 2：显式指定**

```
/t2i 一个女孩 --lora anime_lora:0.8
```

**方式 3：组合多个 LoRA**

```
/t2i 一个女孩
--lora anime_lora:0.7
--lora portrait_lora:0.5
```

---

### LoRA 强度指南

| 强度范围 | 效果 |
|---------|------|
| 0.0 - 0.3 | 轻微影响 |
| 0.4 - 0.6 | 适度影响（推荐起始点） |
| 0.7 - 0.9 | 强烈影响 |
| 1.0+ | 可能过度影响 |

---

## 提示词模板

### 创建提示词模板

编辑 `workspace/configs/prompt_library.json`：

```json
{
  "templates": {
    "portrait": {
      "name": "人像摄影",
      "template": "{subject}，专业人像摄影，柔和光照，景深效果，85mm 镜头",
      "description": "用于生成专业人像照片"
    },
    "landscape": {
      "name": "风景照片",
      "template": "{scene}，广角镜头，黄金时段光线，国家地理风格",
      "description": "用于生成风景照片"
    }
  }
}
```

---

### 使用提示词模板

```
/t2i template:portrait 一个微笑的女孩
```

---

## 高级配置

### 条件工作流

基于条件选择不同的工作流：

```json
{
  "conditional_workflow": {
    "if_image": "flux_i2i_api.json",
    "if_text": "flux_t2i_api.json",
    "conditions": {
      "min_resolution": 512,
      "max_resolution": 2048
    }
  }
}
```

---

### 工作流链

串联多个工作流：

```json
{
  "workflow_chain": [
    "flux_t2i_api.json",
    "flux_i2i_upscale.json",
    "flux_i2i_enhance.json"
  ]
}
```

---

## 工作流调试

### 测试工作流

```bash
# 使用测试脚本
python workspace/bot/test_workflow.py \
  --workflow flux_t2i_api.json \
  --prompt "测试提示词" \
  --dry-run
```

### 查看工作流日志

```bash
tail -f workspace/tmp/workflow.log
```

---

## 常见问题

**Q: 工作流执行失败？**

A:
1. 检查 JSON 格式是否正确
2. 验证所有必需的节点都存在
3. 确认模型文件已下载
4. 查看错误日志

**Q: 如何优化工作流性能？**

A:
- 减少节点数量
- 使用更快的采样器
- 降低分辨率
- 减少步数

**Q: 如何导出工作流？**

A:
1. 在 ComfyUI 中打开工作流
2. 点击 "Save (API Format)"
3. 保存到 `workspace/workflows/`

---

## 更多资源

- [ComfyUI 官方文档](https://docs.comfyanonymous.top/)
- [ComfyUI Examples](https://comfyanonymous.github.io/ComfyUI_examples/)
- [工作流分享社区](https://civitai.com/)
