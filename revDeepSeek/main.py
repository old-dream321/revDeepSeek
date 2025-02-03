import requests
from typing import List, Dict, Generator, Union
from io import BytesIO
import hashlib
import filetype
import json

from .solve_pow import DeepSeekPOW


class APIError(Exception):
    """API错误"""
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class ChatBot:
    """DeepSeek基类"""

    def __init__(self, user_token: str):
        """
        初始化
        :param user_token: 用户token
        """
        self.api_base = "https://chat.deepseek.com/api/v0"
        self.user_token = user_token

    def __get_header(self, pow_path: str = ""):
        headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'authorization': f'Bearer {self.user_token}',
            'origin': 'https://chat.deepseek.com',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'x-app-version': '20241129.1',
            'x-client-locale': 'zh_CN',
            'x-client-platform': 'web',
            'x-client-version': '1.0.0-always',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua-mobile': '?0',
            'priority': 'u=1, i',
            'pragma': 'no-cache',
            'cache-control': 'no-cache'
        }
        if pow_path:
            headers["x-ds-pow-response"] = self.__pow_challenge(pow_path)
        return headers

    def __pow_challenge(self, path: str) -> str:
        url = self.api_base + "/chat/create_pow_challenge"
        response = requests.post(
            url,
            headers=self.__get_header(),
            json={
                "target_path": path,
            }
        )
        if response.status_code == 200:
            res = response.json()
            challenge = res.get("data").get("biz_data").get("challenge")
            answer = DeepSeekPOW().solve_challenge(challenge)
            # base64编码
            return answer

    def create_session(self) -> Dict:
        """
        创建会话
        :return: 会话信息
        """
        url = self.api_base + "/chat_session/create"
        response = requests.post(
            url,
            headers=self.__get_header(),
            json={
                "character_id": None
            }
        )
        if response.status_code == 200:
            res = response.json()
            return res.get("data").get("biz_data")
        else:
            raise APIError("创建会话失败:" + response.text)

    def rename_session(self, session_id: str, name: str) -> None:
        """
        重命名会话
        :param session_id: 会话id
        :param name: 会话名称
        :return: None
        """
        url = self.api_base + "/chat_session/update_title"
        response = requests.post(
            url,
            headers=self.__get_header(),
            json={
                "chat_session_id": session_id,
                "title": name
            }
        )
        if response.status_code == 200:
            return
        else:
            raise APIError("重命名会话失败:" + response.text)

    def delete_session(self, session_id: str) -> None:
        """
        删除会话
        :param session_id: 会话id
        :return: None
        """
        url = self.api_base + "/chat_session/delete"
        response = requests.post(
            url,
            headers=self.__get_header(),
            json={
                "chat_session_id": session_id
            }
        )
        if response.status_code == 200:
            return
        else:
            raise APIError("删除失败:" + response.text)

    def get_history(self, session_id: str) -> List[Dict]:
        """
        获取会话历史
        :param session_id: 会话id
        :return: 会话历史
        """
        url = self.api_base + f"/chat/history_messages?chat_session_id={session_id}&cache_version=32"
        response = requests.get(
            url,
            headers=self.__get_header()
        )
        if response.status_code == 200:
            res = response.json()
            return res.get("data").get("biz_data").get("chat_messages")
        else:
            raise APIError("获取会话历史失败:" + response.text)

    def get_session_list(self, count: int = 100) -> List[Dict]:
        """
        获取会话列表
        :param count: 数量
        :return: 会话列表
        """
        url = self.api_base + f"/chat_session/fetch_page?count={count}"
        response = requests.get(
            url,
            headers=self.__get_header()
        )
        if response.status_code == 200:
            res = response.json()
            return res.get("data").get("biz_data").get("chat_sessions")

        else:
            raise APIError("获取会话列表失败:" + response.text)

    def __upload_file(self, file: Union[bytes, BytesIO]) -> str:
        """上传文件"""
        if isinstance(file, bytes):
            file_obj = BytesIO(file)
        elif isinstance(file, BytesIO):
            file_obj = file
        else:
            raise ValueError("文件类型必须是 bytes 或 BytesIO")

        file_obj.seek(0)

        file_type = filetype.guess_mime(file)
        file_name = "" + hashlib.md5(file).hexdigest() + "." + file_type.split("/")[1]

        url = self.api_base + "/file/upload_file"
        response = requests.post(
            url,
            headers=self.__get_header("/api/v0/file/upload_file"),
            files={
                "file": (file_name, file_obj, file_type)
            }
        )
        if response.status_code == 200:
            res = response.json()
            file_id = res.get("data").get("biz_data").get("id")
            while True:
                if self.__check_parse(file_id):
                    break
                else:
                    continue
            return file_id
        else:
            raise APIError("上传文件失败:" + response.text)

    def __check_parse(self, file_id: str) -> bool:
        url = self.api_base + f"/file/fetch_files?file_ids={file_id}"
        response = requests.get(
            url,
            headers=self.__get_header()
        )
        if response.status_code == 200:
            res = response.json()
            res = res.get("data").get("biz_data").get("files")[0]
            if res.get("status") == "SUCCESS":
                return True
            else:
                return False
        else:
            raise APIError("检查解析状态失败:" + response.text)

    def __stream_chat(
            self,
            session_id: str,
            prompt: str,
            parent_message_id: str = None,
            search: bool = False,
            thinking: bool = False,
            file: Union[bytes, BytesIO] = None
    ) -> Generator[Dict, None, None]:
        """
        流式对话
        :param session_id: 会话id
        :param prompt: 内容
        :param parent_message_id: 上一个消息id
        :param search: 是否开启搜索
        :param thinking: 是否开启思考
        :param file 上传的文件二进制数据
        :return: 回答
        """
        file_id = None

        if file:
            file_id = self.__upload_file(file)

        url = self.api_base + "/chat/completion"
        data = {
            "chat_session_id": session_id,
            "prompt": prompt,
            "parent_message_id": parent_message_id,
            "search_enabled": search,
            "thinking_enabled": thinking,
            "ref_file_ids": [file_id] if file_id else []
        }
        headers = self.__get_header("/api/v0/chat/completion")
        response = requests.post(
            url,
            headers=headers,
            json=data,
            stream=True,
            timeout=None
        )
        for chunk in response.iter_lines():
            if chunk:
                chunk = chunk.decode("utf-8")
                if chunk.startswith("data:"):
                    chunk = chunk[5:]
                    if "[DONE]" in str(chunk):
                        return
                    else:
                        chunk = json.loads(chunk)
                        message_id = chunk.get("message_id")
                        res = chunk.get("choices")[0].get("delta")
                        res["message_id"] = message_id
                        yield res

    def chat(
            self,
            session_id: str,
            prompt: str,
            parent_message_id: str = None,
            search: bool = False,
            thinking: bool = False,
            file: Union[bytes, BytesIO] = None,
            stream: bool = False
    ) -> Union[Dict, Generator[Dict, None, None]]:
        """
        对话
        :param session_id: 会话id
        :param prompt: 内容
        :param parent_message_id: 上一个消息id
        :param search: 是否开启搜索
        :param thinking: 是否开启思考
        :param file 上传的文件二进制数据
        :param stream: 是否流式对话
        :return: 回答
        """
        if stream:
            res = self.__stream_chat(
                session_id,
                prompt,
                parent_message_id,
                search,
                thinking,
                file
            )

            def response() -> Generator[Dict, None, None]:
                res_content = ""
                prev_type = ""
                for chunk in res:
                    message_type = chunk.get("type")
                    content = chunk.get("content")
                    if prev_type == "thinking" and message_type == "text":
                        res_content = ""
                    if content:
                        res_content = res_content + content
                    message_id = chunk.get("message_id")
                    prev_type = message_type
                    yield {
                        "content": res_content,
                        "type": message_type,
                        "message_id": message_id
                    }
            return response()

        else:
            res = self.__stream_chat(
                session_id,
                prompt,
                parent_message_id,
                search,
                thinking,
                file
            )
            res_content = ""
            think_content = ""
            message_id = None
            for chunk in res:
                message_type = chunk.get("type")
                if message_type == "text":
                    content = chunk.get("content")
                    if content:
                        res_content = res_content + content
                elif message_type == "thinking":
                    if chunk.get("content"):
                        think_content = think_content + chunk.get("content")
                message_id = chunk.get("message_id")
            if thinking:
                return {
                    "content": res_content,
                    "thinking_content": think_content,
                    "message_id": message_id
                }
            return {
                "content": res_content,
                "message_id": message_id
            }

