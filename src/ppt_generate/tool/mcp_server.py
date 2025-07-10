from typing import Callable, Dict, Any, Type, Literal, Union, List
from typing import get_type_hints, get_origin, get_args
import inspect
from mcp.server.fastmcp import FastMCP
# from ppt_generate.tool.tool import pdf_to_text


class MCPServer():
    """MCPServer类，目标就是将一组函数封装成MCP Server，还要满足OpenAI接口的规范
    """

    def __init__(self,
                 *,
                 funcs: List[Callable],
                 server_name: str = "mcp_server",
                 host: str = "127.0.0.1",
                 port: int = 8888):
        # 搞个工具字典，key是工具名，value是工具函数，方便后面访问到函数
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        self.mcp_server = FastMCP(name=server_name, host=host, port=port)

        # 添加工具
        for func in funcs:
            self.tool_schemas[func.__name__] = self._get_tool_schema(func)
            self.mcp_server.add_tool(
                fn=func,
                name=func.__name__,
                description=self._get_tool_description(func))

    def run(self,
            transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
            mount_path: str | None = None):
        self.mcp_server.run(transport, mount_path)

    def _get_tool_name(self, func: Callable) -> str:
        """获取工具名称"""
        return func.__name__

    def _get_tool_description(self, func: Callable) -> str:
        """按照不同注释风格，Google和Numpy风格，都要能提取tool_description
        
        Args:
            func (Callable): 函数对象
            
        Returns:
            str: 工具描述
        """
        if not func.__doc__:
            return ""

        doc = func.__doc__

        # 处理Google风格文档
        if "Args:" in doc:
            # 取Args:之前的内容作为描述
            description = doc.split("Args:")[0].strip()
            return description

        # 处理NumPy风格文档
        if "Parameters" in doc:
            # 取Parameters之前的内容作为描述
            description = doc.split("Parameters")[0].strip()
            return description

        # 如果都不是，就取第一行作为描述
        return doc.split("\n")[0].strip()

    def _get_param_type_for_tool_schema(self,
                                        type_hint: Type) -> Dict[str, Any]:
        """获取参数类型，并转换为openai工具schema兼容的类型，考虑到部分非标准化编程的情况
        这个函数能用，但绝对没有涵盖所有情况^_^
        
        Args:
            type_hint (Type): 由get_type_hints函数获取的参数的【类型】，兼容python源生类型和typing类

        Returns:
            (Dict[str, Any]): 参数类型schema
            例如：
            {
                "type": "array",
                "items": {
                    "type": "integer"
                }
            }
        """
        # 首先必须要搞清楚get_origin函数和get_args函数的作用
        # get_origin函数：获取给予typing类的类型提示的python原始类型（如list、dict、tuple等），但如果类型提示是python内置类型或者其他玩意，则返回None。此外，无论这个类型被嵌套了多少层，get_origin函数都仅返回最外层的类型，如List[List[List[int]]]，get_origin函数仅返回list
        # get_args函数：如果出现类型嵌套，就返回嵌套的全部类型，如果没嵌套，就返回空tuple。例如List[List[List[int]]]，get_args函数返回(typing.List[typing.List[int]],)；Dict[str, List[int]]，get_args函数返回(<class 'str'>, typing.List[int])。对于Literal[a, b, c]，get_args函数返回(a, b, c)

        # 思路：结合ori_type和args_type来处理参数类型，因为各种嵌套咱们无法估计，所以采用递归是一个好办法，既然采用递归，那我们实际上只用考虑最简单的情况即可，把原子化能力解决完，剩下的就是递归调用自己

        # 接下来我们就用get_origin和get_args来
        ori_type = get_origin(type_hint)
        args_type = get_args(type_hint)

        if ori_type in [list, tuple] or type_hint in [
                list, tuple
        ]:  # 处理List、List[T]、Tuple、Tuple[T]，T代表任意类型（递归调用不用管T到底是什么）
            # 判断有没有嵌套
            # List和Tuple的嵌套只会有一个参数，比如List[str]或List[List[str]]，而不可能是List[str, int]，所以args_type = (T,)，args_type[0]就能取到元素的类型
            # List是和Tuple需要一个额外的items字段表明每个元素的类型
            item_type = args_type[0] if args_type else None
            if item_type:  # 有type就加，没有type就不加这个items就好了
                return {
                    "type": "array",
                    "items": self._get_param_type_for_tool_schema(
                        item_type)  # 递归调用，万一又是一个List
                }
            else:
                return {"type": "array"}
        elif ori_type == dict or type_hint == dict:  # 处理Dict或Dict[K, V]这种情况
            # 同样判断有没有嵌套，K不太可能嵌套，但V还可能嵌套，比如Dict[str, List[int]]
            # 这里args_type = (K, V)，args_type[0]取到K的类型，args_type[1]取到V的类型，我们只需要分析V的类型
            value_type = args_type[1] if args_type else None
            if value_type:
                return {
                    "type":
                    "object",
                    "additionalProperties":
                    self._get_param_type_for_tool_schema(value_type)
                }
            else:
                return {"type": "object"}
        elif ori_type == Literal:  # 处理Literal[a, b, c]这种情况，a、b、c同种类型
            # 这里特殊，a、b、c直接放到enum字段里就可以
            # 获得a、b、c的类型，注意_get_param_type_for_tool_schema函数返回的是一个字典，字典的type字段才是类型
            literal_type = self._get_param_type_for_tool_schema(
                type(args_type[0]))["type"]
            return {
                "type": literal_type,
                "enum": list(args_type) if args_type else []
            }
        elif ori_type == Union:  # 处理Union或者Optional情况
            # 用anyOf来处理，把所有可能的类型都列出来
            return {
                "anyOf": [
                    self._get_param_type_for_tool_schema(arg)
                    for arg in args_type
                ]
            }

        # 到目前为止，ori_type生成typing类型的情况就处理完了，那其他情况大概率返回就是None了，我们无法从ori_type获取信息，只能从type_hint获取信息了
        # 为啥没有list和dict？
        if type_hint == int:
            return {"type": "integer"}
        elif type_hint == float:
            return {"type": "number"}
        elif type_hint == bool:
            return {"type": "boolean"}
        elif type_hint == type(None):
            return {"type": "null"}
        elif type_hint == str:
            return {"type": "string"}
        elif type_hint == list:
            return {"type": "array"}

        return {"type": "string"}  # 保底！

    def _get_tool_schema(self, func: Callable) -> Dict[str, Any]:
        """tool都是以函数代码的形式存在，但大模型并不能直接认识"代码"，得把代码转成大模型能认识的格式（通常都是json格式字符串），也即tool（function） schema。
       
        Args:
            func (Callable): 函数对象
            
        Returns:
            (Dict[str, Any]): 工具schema

        openai接口的工具schema样式（字典）,背诵并默写：
        {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Retrieves current weather for the given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and country e.g. Bogotá, Colombia",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Units the temperature will be returned in."
                    }
                    },
                    "required": ["location", "units"],
                    "additionalProperties": False
                },
            }
        }
        """
        # 构建一个基本的工具schema模板，后面缺啥补啥
        schema_template = {
            "type": "function",
            "function": {
                "name": self._get_tool_name(func),
                "description": self._get_tool_description(func),
                "parameters": {
                    "type": "object",
                    "properties": {},  # 后面获取工具入参类型和描述
                    "required": [],
                    "additionalProperties": False
                },
            }
        }

        # 获取函数签名
        # 例如：(location: str, units: Optional[str] = 'celsius') -> str
        # 目标就是可以遍历所有的入参 问题：为什么出参不用分析？
        sig = inspect.signature(func)

        # 获取所有入参的类型，通过get_type_hints函数获取的类型可以兼容typing类
        # 例如：{'location': <class 'str'>, 'units': <class 'typing.Optional'>, 'return': <class 'str'>}
        # 等价于inspect.get_annotations(func)
        type_hints = get_type_hints(func)

        # 遍历所有入参
        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, Any)
            # 先把这个参数放到字典里，然后update键值对
            schema_template["function"]["parameters"]["properties"][
                param_name] = {}
            schema_template["function"]["parameters"]["properties"][
                param_name].update(
                    self._get_param_type_for_tool_schema(param_type))
            schema_template["function"]["parameters"]["properties"][
                param_name]['description'] = self._get_param_description(
                    func, param_name)

            # 判断是不是必要值，没有默认值就是必要值
            if param.default == inspect.Parameter.empty:
                schema_template["function"]["parameters"]["required"].append(
                    param_name)
            else:
                schema_template["function"]["parameters"]["properties"][
                    param_name]['default'] = param.default

        return schema_template

    def _get_param_description(self, func: Callable, param_name: str) -> str:
        """从函数文档中提取函数的描述，目前仅支持Google风格注释

        Args:
            func (Callable): 工具函数
            param_name (str): 参数名称

        Returns:
           参数描述
        """
        if not func.__doc__:
            return ""

        # 从函数文档中提取参数描述
        doc = func.__doc__
        doc_lines = doc.split('\n')

        # 先找到Args出现的地方，然后下面每行冒号后面都是参数的描述，冒号有可能是中文的冒号也可能是英文的冒号
        arg_start_line_index = -1
        for i, line in enumerate(doc_lines):
            if 'Args' in line:
                arg_start_line_index = i
                break

        if arg_start_line_index == -1:
            return ""

        for i in range(arg_start_line_index + 1, len(doc_lines)):
            line = doc_lines[i].strip()
            # 空行跳过
            if line == '':
                continue

            # 如果遇到下一个主要部分（如Returns:），则停止循环，因为参数信息都有了
            # 同时考虑中文和英文冒号
            if line and not line.startswith(' ') and (line.endswith(':')
                                                      or line.endswith('：')):
                break

            # 如果遇到参数名称，则提取参数名称后面的内容，同时考虑中文和英文冒号
            if line.startswith(param_name):
                # 如果存在中文冒号，则提取中文冒号后面的内容
                if '：' in line:
                    description = line.split('：')[-1].strip()
                else:
                    description = line.split(':')[-1].strip()
                return description

        return ""
