# 项目环境与配置管理指南

本项目采用了 **“环境变量 (.env) + 结构化配置 (YAML)”** 的混合配置管理方案。这种方案能够有效地将敏感信息与公共业务配置分离，既保证了代码的安全性，又提升了配置的可读性和维护性。

## 1. 环境变量 (.env)

环境变量主要用于存储**敏感信息**（如 API 密钥、数据库密码等）以及特定于本地运行环境的私有配置。

### 1.1 使用方法
1. 在项目根目录下，找到 `.env.example` 文件作为参考模板。
2. 复制该文件并重命名为 `.env`。
3. 在 `.env` 文件中填入真实的密钥信息。例如：
   ```env
   # DashScope API Key
   DASHSCOPE_API_KEY=your_real_api_key_here
   ```

> **安全警告**：`.env` 文件已被添加到 `.gitignore` 中，**绝对不要**将其提交到版本控制系统中，以防敏感信息泄露。

### 1.2 加载机制
项目在主服务启动时（如 `src/main_api.py`），会通过 `python-dotenv` 库的 `load_dotenv()` 方法自动读取 `.env` 文件，将其注入到系统环境变量中。
随后，在代码中可以通过 `os.getenv("DASHSCOPE_API_KEY")` 来安全地获取这些敏感值（例如在 `src/model/factory.py` 中的 `check_api_ket_set()` 函数）。

## 2. 业务配置 (YAML)

对于非敏感的、与业务逻辑相关的公共配置，项目使用 YAML 文件进行管理。YAML 文件支持丰富的数据结构（如列表、嵌套字典），非常适合复杂配置的声明与维护。

### 2.1 配置文件位置
所有的 YAML 配置文件都统一存放在 `src/config/` 目录下：
- **`app.yml`**: 应用基础配置（如应用名称、允许上传的文件类型、文件上传数量限制等）。
- **`model.yml`**: 大模型相关配置（如聊天模型名称、向量模型名称、Temperature 等生成参数设置）。
- **`rag.yml`**: RAG（检索增强生成）流程相关参数。

### 2.2 加载机制
项目中提供了一个统一的配置加载工具类 `ConfigLoader`（位于 `src/utils/config_loader.py`）。通过该工具，可以将 YAML 文件直接解析为 Python 字典供程序使用。

**使用示例：**
```python
from src.storage.paths import CONFIG_DIR
from src.utils.config_loader import ConfigLoader

# 加载模型配置文件
model_conf = ConfigLoader.load_yaml(CONFIG_DIR / "model.yml")

# 获取具体配置项
chat_model_name = model_conf["chat_model_name"]
temperature = model_conf.get("temperature", 0.7)
```

## 3. 方案优势总结

相比于将所有配置项揉捏在单一的 `.env` 文件中，本项目的混合管理方案具有以下显著优势：

1. **安全性高**：敏感密钥仅保留在本地未追踪的 `.env` 中，杜绝了硬编码或误提交导致的代码泄露风险。
2. **结构清晰**：YAML 原生支持复杂的层级数据结构，避免了 `.env` 中只能使用扁平字符串（并且需要在代码中手动做字符串解析分割）的局限性。
3. **高内聚低耦合**：将不同业务模块（如 app、model、rag）的配置拆分到不同的 YAML 文件中，修改配置时不会相互干扰，符合单一职责原则。
4. **团队协作友好**：公开的 YAML 业务配置可以直接提交到 Git，确保团队所有成员拥有相同的运行基准，而本地私有配置则互不影响。
