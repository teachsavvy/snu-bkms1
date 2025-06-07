# ├── 1. 스키마 Prompt 정의
# ├── 2. Few-shot 예시 정의 (필요 시)
# ├── 3. 자연어 → Cypher 함수
# ├── 4. 예외처리 포함 실행 블록 (필요 시)

# nl2cypher_mcp.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import openai

# 1. OpenAI 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. FastAPI 앱 생성 및 CORS 허용(port 다를 경우 대비)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 제한할 수도 있음
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 데이터 입력 형식 정의
class QueryRequest(BaseModel):
    message: str

# 4. StackOverflow 스키마 프롬프트
STACKOVERFLOW_SCHEMA = """
Graph Schema for StackOverflow Neo4j:

🟦 Nodes:
  - (q:Question)
      Properties:
        - uuid
        - title
        - creation_date
        - accepted_answer_id
        - link
        - view_count
        - answer_count
        - body_markdown

  - (u:User)
      Properties:
        - uuid
        - display_name

  - (a:Answer)
      Properties:
        - uuid
        - title
        - link
        - is_accepted
        - body_markdown
        - score

  - (t:Tag)
      Properties:
        - name
        - link

  - (c:Comment)
      Properties:
        - uuid
        - link
        - score

🟨 Relationships (You may assume or infer):
  - (u:User)-[:ASKED]->(q:Question)
  - (u:User)-[:ANSWERED]->(a:Answer)
  - (a:Answer)-[:ANSWERS]->(q:Question)
  - (q:Question)-[:HAS_TAG]->(t:Tag)
  - (q:Question)-[:HAS_COMMENT]->(c:Comment)
  - (a:Answer)-[:HAS_COMMENT]->(c:Comment)
"""


# 5. 자연어 → Cypher 변환 함수
def natural_language_to_cypher(nl_query: str) -> str:
    system_prompt = f"""
You are an expert Neo4j Cypher query translator. Your task is to convert natural language questions into Cypher queries based on the provided schema.
Always adhere to the following rules:
- Only use the nodes, relationships, and properties explicitly defined in the schema.
- Do not infer or invent any details not present in the schema.
- Output ONLY the raw Cypher query, without any additional text, explanations, or markdown formatting like ```cypher.
"""

    user_prompt = f"""
Schema:
{STACKOVERFLOW_SCHEMA}

Natural language question:
"{nl_query}"

Cypher query:
"""
    # [개선] 안정성을 위해 상세 에러 처리만 추가
    try:
        # 이전 버전(v0.x)의 openai 라이브러리 호출 방식을 사용합니다.
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "system_prompt"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        return response.choices[0].message["content"].strip()

    # openai 라이브러리의 구체적인 에러 유형을 처리
    except openai.error.AuthenticationError:
        return "[ERROR] OpenAI API 인증에 실패했습니다. API 키를 확인하세요."
    except openai.error.RateLimitError:
        return "[ERROR] OpenAI API 사용량 한도를 초과했습니다. 잠시 후 다시 시도하세요."
    except openai.error.APIConnectionError:
        return "[ERROR] OpenAI 서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요."
    except openai.error.APIError as e:
        return f"[ERROR] OpenAI API가 에러를 반환했습니다: {e}"
    except Exception as e:
        return f"[ERROR] 쿼리 생성 중 예상치 못한 에러가 발생했습니다: {e}"

# 6. MCP 서버 API 엔드포인트
@app.post("/generate-query")
def generate_query(request: QueryRequest):
    query = natural_language_to_cypher(request.message)
    return {"query": query, "parameters": {}}

# 7. 서버 실행
if __name__ == "__main__":
    uvicorn.run("nl2cypher_mcp:app", host="0.0.0.0", port=8000, reload=True)