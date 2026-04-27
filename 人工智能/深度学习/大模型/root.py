import os

from dotenv import load_dotenv
from openai import OpenAI
import time


def convert(messages):
    # 批量转换任意消息类型为模型格式
    mapping ={
        "system":"system",
        "human":"user",
        "ai":"assistant",
        "user":"user",
        "assistant":"assistant"
    }

    if hasattr(messages,'type'):
        return [
            {
                "role":mapping[msg.type],
                "content":msg.content
            }
            for msg in messages
        ]
    else:
        return messages
load_dotenv()
class Model:
    def __init__(self,model_name='deepseek-chat',
                 base_url="https://api.deepseek.com",
                 api_key = os.getenv('api_key')):
        self.model_name = model_name
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key,base_url=self.base_url)

    def invoke(self,prompt,temperature=1,top_p = 0.95,max_tokens = 1000,
               stop = None,system_role = "You are a helpful assistant"):
        # 1.调API可以设置参数，更精准控制大模型输出
        print('正在推理中，请您稍等...')
        time1 = time.time()
        if not isinstance(prompt,list):
            # 如果prompt不是列表形式，则将其转化为列表
            prompt = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ]
        prompt = convert(prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=prompt,
            temperature=temperature,
            top_p = top_p,
            max_tokens=max_tokens,
            stop=stop
        )
        time2 = time.time()
        print(f'本次推理，一共耗时：{time2-time1:.1f}秒')
        return response.choices[0].message.content
llm = Model()