# revDeepSeek
DeepSeek逆向API


## 安装
```bash
pip install revDeepSeek --upgrade
```

## 使用
具体用法可查看方法`Type Hint`

## 1.初始化
```python
from revDeepSeek import Chatbot
chatbot = Chatbot("USER_TOKEN")
```
USER_TOKEN获取:\
1.打开开发者工具，找到应用程序选项卡\
2.如下图
![](.github/res/usertoken.png)

## 2.使用

### 新建会话
```python
res = chatbot.create_session()
session_id = res["id"] #会话ID
```
### 发送消息
```python
res = chatbot.chat(
    conversation_id=session_id, # 会话ID
    prompt="你好", # 消息内容
    parent_message_id=None, # 父消息ID
    search=False, # 启用搜索
    thinking=False, # 启用深度思考
    file=None, # 文件二进制数据(上传文件需添加)
    stream=False, # 启用流式输出
)
```
响应示例:
```json
{
    "content": "内容",
    "type": "text",
    "message_id": 100
}
```

### 获取会话列表
```python
res = chatbot.get_session_list(count=100)
```

### 获取会话历史
```python
res = chatbot.get_session_history(session_id=session_id)
```

### 删除会话
```python
res = chatbot.delete_session(session_id=session_id)
```