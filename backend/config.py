import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# FAISS C++ 底层不支持路径含空格，数据目录统一放到无空格路径
_DATA_ROOT = Path("C:/HealthQA")
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"   # 原始文档留在项目内
VECTOR_STORE_DIR = _DATA_ROOT / "vector_store"     # 向量库移到无空格路径
LOGS_DIR = _DATA_ROOT / "logs"                     # 日志移到无空格路径

ASSETS_DIR = BASE_DIR / "assets"

for _d in [KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR, LOGS_DIR, ASSETS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@2024")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 4
MAX_HISTORY_TURNS = 5

DB_PATH = LOGS_DIR / "query_logs.db"

MEDICAL_DISCLAIMER = (
    "⚠️ **医疗免责声明**：本回答仅供参考，不能替代专业医生的诊疗意见。"
    "如有健康问题，请及时前往正规医疗机构就诊。"
)

MEDICAL_KEYWORDS = [
    "诊断", "治疗", "用药", "药物", "剂量", "服药", "症状", "病情",
    "手术", "化疗", "处方", "副作用", "并发症", "化验单", "检查结果",
    "血压多少", "血糖多少", "病因", "怎么治", "能治好吗",
]

MODULES = {
    "all": "全部知识库",
    "policy": "政策问答（医保/家庭医生）",
    "vaccine": "疫苗接种咨询",
    "appointment": "预约与办事指南",
    "notice": "社区通知公告",
}

CENTER_INFO = {
    "name": "昆明市五华区大观街道社区卫生服务中心",
    "address": "昆明市五华区大观街道",
    "phone": "0871-66052416",
    "hours": "星期一-星期天 8:30-17:00",
}
