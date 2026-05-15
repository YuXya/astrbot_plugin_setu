# AstrBot LLM Tool 笔记

## 核心概念

AstrBot 的 LLM Tool 是给大语言模型调用外部功能的接口。

普通插件命令通常依赖消息事件和命令前缀，例如用户发送 `/xxx` 后触发对应处理函数。LLM Tool 则不同，它会作为“工具能力”暴露给对话中的大模型。模型可以根据用户的自然语言请求决定是否调用某个 Tool。

因此，LLM Tool 适合用于这些场景：

- 用户不想记具体命令，只想自然语言触发功能
- 功能需要被 AI 在对话流程中主动调用
- 插件能力需要参与 Agent 或工具调用循环
- bot 自己发送的命令文本无法触发普通用户消息监听时

## 调用大模型

AstrBot v4.5.7 之后推荐使用新的 LLM 调用方式。

获取当前会话使用的聊天模型 ID：

```python
umo = event.unified_msg_origin
provider_id = await self.context.get_current_chat_provider_id(umo=umo)
```

调用大模型：

```python
llm_resp = await self.context.llm_generate(
    chat_provider_id=provider_id,
    prompt="Hello, world!",
)
```

返回文本可通过 `llm_resp.completion_text` 获取。

## 方式一：定义 FunctionTool

可以通过继承 `FunctionTool` 定义一个 Tool。

```python
from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class ExampleTool(FunctionTool[AstrAgentContext]):
    name: str = "example_tool"
    description: str = "A tool to execute an example action."
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Keyword for the action.",
                },
            },
            "required": ["keyword"],
        }
    )

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        keyword = kwargs["keyword"]
        return f"Result for: {keyword}"
```

## 注册 FunctionTool

在插件的 `__init__` 方法中注册。

AstrBot v4.5.1 及之后：

```python
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context.add_llm_tools(ExampleTool())
```

AstrBot v4.5.1 之前：

```python
tool_mgr = self.context.provider_manager.llm_tools
tool_mgr.func_list.append(ExampleTool())
```

## 方式二：装饰器定义 Tool

也可以用装饰器直接定义并注册 Tool。

```python
@filter.llm_tool(name="get_weather")
async def get_weather(self, event: AstrMessageEvent, location: str) -> MessageEventResult:
    '''获取天气信息。

    Args:
        location(string): 地点
    '''
    resp = self.get_weather_from_api(location)
    yield event.plain_result("天气信息: " + resp)
```

如果 `name` 不填，AstrBot 会使用函数名作为 Tool 名称。

## Docstring 格式

使用装饰器方式时，AstrBot 会解析函数注释生成 Tool 描述和参数说明。因此 docstring 格式很重要。

推荐格式：

```python
'''工具功能说明。

Args:
    参数名(参数类型): 参数说明
'''
```

参数示例：

```python
'''搜索指定关键词。

Args:
    keyword(string): 搜索关键词
    limit(number): 返回数量
    include_detail(boolean): 是否包含详细信息
'''
```

支持的参数类型：

- `string`
- `number`
- `object`
- `boolean`
- `array`
- `array[string]`，AstrBot v4.5.7 之后支持

## Tool 返回结果

装饰器方式的 Tool 可以像普通事件处理函数一样返回消息结果。

```python
yield event.plain_result("文本结果")
```

也可以返回消息链等 AstrBot 支持的结果类型，具体取决于插件已有的消息发送逻辑。

继承 `FunctionTool` 的方式通常在 `call()` 中直接返回字符串或 `ToolExecResult`。

## 调用 Agent

AstrBot v4.5.7 之后，可以使用 `tool_loop_agent()` 让模型在推理过程中自动调用工具。

```python
llm_resp = await self.context.tool_loop_agent(
    event=event,
    chat_provider_id=prov_id,
    prompt="搜索一下相关信息。",
    tools=ToolSet([ExampleTool()]),
    max_steps=30,
    tool_call_timeout=60,
)
```

`tool_loop_agent()` 会自动处理模型请求、工具调用和继续推理，直到模型不再调用工具或达到最大步骤数。

## Multi-Agent 思路

Multi-Agent 可以把多个子智能体封装成 Tool，让主智能体根据用户请求决定调用哪个子智能体。

常见结构：

- 主智能体负责理解任务和分配任务
- 子智能体作为 Tool 暴露给主智能体
- 每个子智能体可以继续使用自己的 ToolSet
- 主智能体通过 `tool_loop_agent()` 完成工具调用循环

这种方式适合更复杂的插件或自动化流程。

## 对话管理

AstrBot 提供会话管理器，可以读取和维护当前会话历史。

获取当前对话：

```python
uid = event.unified_msg_origin
conv_mgr = self.context.conversation_manager
curr_cid = await conv_mgr.get_curr_conversation_id(uid)
conversation = await conv_mgr.get_conversation(uid, curr_cid)
```

常用方法：

- `new_conversation`
- `switch_conversation`
- `delete_conversation`
- `get_curr_conversation_id`
- `get_conversation`
- `get_conversations`
- `update_conversation`

## 人格设定管理

人格设定可通过 `self.context.persona_manager` 管理。

常用方法：

- `get_persona`
- `get_all_personas`
- `create_persona`
- `update_persona`
- `delete_persona`
- `get_default_persona_v3`

其中创建人格时，`tools` 参数可控制人格允许使用的工具：

- `None`：允许全部工具
- `[]`：禁用全部工具
- 指定工具列表：只允许部分工具

## 注意事项

- 文档中的装饰器是 `@filter.llm_tool(...)`。
- 装饰器方式需要写清楚函数 docstring，AstrBot 会解析它。
- Tool 名称应简短明确，方便模型理解和调用。
- Tool 描述应说明“什么时候该调用”，而不只是说明函数做了什么。
- 对高风险功能要谨慎暴露给模型，必要时加权限、配置或参数校验。
- 普通命令和 LLM Tool 是两套触发路径，可以复用内部业务函数，但触发机制不同。

