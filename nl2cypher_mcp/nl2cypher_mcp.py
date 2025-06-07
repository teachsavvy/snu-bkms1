# ├── 1. 스키마 Prompt 정의
# ├── 2. Few-shot 예시 정의 (선택)
# ├── 3. 자연어 → Cypher 함수
# ├── 4. 예외처리 포함 실행 블록 (선택)

# nl2cypher_mcp.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import openai

# 1. OpenAI 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. FastAPI 앱 생성
app = FastAPI()

# 3. CORS 허용(port 다를 경우 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 제한할 수도 있음
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 데이터 입력 형식 정의
class QueryRequest(BaseModel):
    message: str

# 5. StackOverflow 스키마 프롬프트
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

# --. Few-shot 예시 정의 (선택 사항)
# GPT의 쿼리 정확도를 높이고 싶다면 아래 예시를 활성화하세요

# """
# FEW_SHOT_EXAMPLES = '''
# Example 1:
# Q: 가장 많이 질문한 사용자는 누구야?
# A:
# MATCH (u:User)-[:ASKED]->(q:Question)
# RETURN u.display_name, COUNT(q) AS questions
# ORDER BY questions DESC
# LIMIT 1

# Example 2:
# Q: 자바 태그가 붙은 질문 중 조회수 높은 거 알려줘
# A:
# MATCH (q:Question)-[:HAS_TAG]->(t:Tag)
# WHERE t.name = "java"
# RETURN q.title, q.view_count
# ORDER BY q.view_count DESC
# LIMIT 1

# Example 3:
# Q: 가장 높은 점수를 받은 답변은?
# A:
# MATCH (a:Answer)
# RETURN a.title, a.score
# ORDER BY a.score DESC
# LIMIT 1
# '''
# """

# 6. 자연어 → Cypher 변환 함수
def natural_language_to_cypher(nl_query: str) -> str:
    prompt = f"""
You are an assistant that converts natural language questions into Cypher queries
for a StackOverflow-like Neo4j graph database.

Use the following schema:
{STACKOVERFLOW_SCHEMA}

⚠️ Important Notes:
- Only use the provided schema.
- Do NOT invent properties or relationships not listed in the schema.
- If a relationship or attribute is not described, do not assume it exists.
- Stick to the exact node labels and property names given.

Convert the following natural language question into a Cypher query:
\"{nl_query}\"

Only output the Cypher query. Do not include explanations.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"[ERROR] GPT failed: {str(e)}"

# 7. MCP 서버 API 엔드포인트
@app.post("/generate-query")
def generate_query(request: QueryRequest):
    query = natural_language_to_cypher(request.message)
    return {"query": query, "parameters": {}}  # Streamlit과 계약된 포맷
  
if __name__ == "__main__":
    uvicorn.run("nl2cypher_mcp:app", host="0.0.0.0", port=8000, reload=True)