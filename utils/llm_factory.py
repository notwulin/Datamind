import os
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature=0.0):
    """
    统一的大模型获取工厂类。
    通过读取环境变量 DEFAULT_LLM 来决定返回哪个模型提供商的实例。
    """
    llm_type = os.getenv("DEFAULT_LLM", "gemini").lower()

    if llm_type == "openai":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o",  # 或 gpt-4o-mini
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        except ImportError:
            raise ImportError("你需要安装 langchain-openai 来使用 OpenAI: pip install langchain-openai")

    elif llm_type == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-3-5-sonnet-latest",
                temperature=temperature,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        except ImportError:
            raise ImportError("你需要安装 langchain-anthropic 来使用 Anthropic: pip install langchain-anthropic")

    elif llm_type == "dashscope":
        # 阿里通义千问示例
        try:
            from langchain_community.chat_models import ChatTongyi
            return ChatTongyi(
                model="qwen-max",
                temperature=temperature,
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            )
        except ImportError:
            raise ImportError("你需要配置大模型对应的依赖")

    else:
        # Default fallback to Gemini provider
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-3.1-flash-lite-preview",
                temperature=temperature,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
            )
        except ImportError:
            raise ImportError("你需要安装 langchain-google-genai 来使用 Gemini: pip install langchain-google-genai")
