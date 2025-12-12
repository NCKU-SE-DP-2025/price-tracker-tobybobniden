import json
from openai import OpenAI
from src.core.config import settings


class AIService:
    """處理所有 OpenAI 相關操作"""
    
    def __init__(self, api_key: str):
        self.openai_client = OpenAI(api_key=api_key)
    
    def evaluate_relevance(self, title: str) -> str:
        """評估新聞標題相關度"""
        try:
            prompt_message = [
                {
                    "role": "system",
                    "content": "你是一個關鍵度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
                },
                {"role": "user", "content": f"{title}"},
            ]
            ai = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt_message,
            )
            return ai.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error evaluating relevance: {e}")
            return "high"
    
    def extract_keywords(self, prompt: str) -> str:
        """從用戶輸入提取關鍵字"""
        try:
            message = [
                {
                    "role": "system",
                    "content": "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)",
                },
                {"role": "user", "content": f"{prompt}"},
            ]
            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=message,
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return ""
    
    def generate_summary(self, content: str) -> dict:
        """生成新聞摘要"""
        try:
            message = [
                {
                    "role": "system",
                    "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                },
                {"role": "user", "content": f"{content}"},
            ]
            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=message,
            )
            result = completion.choices[0].message.content
            if result:
                result = json.loads(result)
                return {"summary": result.get("影響", ""), "reason": result.get("原因", "")}
            return {"summary": "", "reason": ""}
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {"summary": "", "reason": ""}