# nl2cypher_mcp.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import openai
from dotenv import load_dotenv
import re

# 1. 환경 변수 불러오기
load_dotenv()

# 2. OpenAI 클라이언트 설정
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 3. FastAPI 앱 생성 및 CORS 허용(port 다를 경우 대비)
app = FastAPI()
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
  - (u:User)-[:PROVIDED]->(a:Answer)
  - (a:Answer)-[:ANSWERED]->(q:Question)
  - (q:Question)-[:TAGGED]->(t:Tag)
  - (u:User)-[:COMMENTED]->(c:Comment)
  - (c:Comment)-[:COMMENTED_ON]->(q:Question)
  - (c:Comment)-[:COMMENTED_ON]->(a:Answer)
"""


# 6. 자연어 → Cypher 변환 함수
def natural_language_to_cypher(nl_query: str) -> str:
    # [수정됨] 시스템 프롬프트를 더욱 명확하고 강력한 규칙으로 변경합니다.
    system_prompt = f"""
You are an expert Neo4j Cypher query translator, creating queries for a graph visualization tool.
Your primary goal is to write queries that return all the necessary data to draw a graph.

**Core Principles:**
- You MUST assign a variable to every relationship in a MATCH pattern (e.g., `[r:ASKED]`).
- The `RETURN` clause MUST include all variables for nodes and relationships defined in the `MATCH` clause.
- For aggregation queries (like counting), you MUST use a `WITH` clause to compute the aggregation before the final `RETURN`.

**See the following examples:**

---
**Example 1: Simple relationship query**
Natural language: "What are the latest questions from user 'A. L'?"
Correct Cypher: `MATCH (u:User {{display_name: 'A. L'}})-[r:ASKED]->(q:Question) RETURN u, r, q ORDER BY q.creation_date DESC LIMIT 3`

---
**Example 2: Aggregation query**
Natural language: "Which user asked the most questions?"
Correct Cypher: `MATCH (u:User)-[:ASKED]->(q:Question) WITH u, count(q) AS questionCount RETURN u.display_name, questionCount ORDER BY questionCount DESC LIMIT 1`

---
**Example 3: Multi-hop query**
Natural language: "Who answered questions tagged 'python'?"
Correct Cypher: `MATCH (u:User)-[r1:PROVIDED]->(a:Answer)-[r2:ANSWERED]->(q:Question)-[r3:TAGGED]->(t:Tag {{name: 'python'}}) RETURN u, r1, a, r2, q, r3, t`
---

Now, using the provided schema, translate the following question. Output ONLY the raw Cypher query.
"""

    user_prompt = f"""
Schema:
{STACKOVERFLOW_SCHEMA}

Natural language question:
"{nl_query}"

Cypher query:
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )

        query_text = response.choices[0].message.content.strip()
        query_text = re.sub(r'^```(?:cypher)?\n', '', query_text)
        query_text = re.sub(r'```$', '', query_text).strip()

        return query_text

    except openai.AuthenticationError:
        return "[ERROR] OpenAI API 인증에 실패했습니다. API 키를 확인하세요."
    except openai.RateLimitError:
        return "[ERROR] OpenAI API 사용량 한도를 초과했습니다. 잠시 후 다시 시도하세요."
    except openai.APIConnectionError:
        return "[ERROR] OpenAI 서버에 연결할 수 없습니다. 네트워크 상태를 확인하세요."
    except openai.APIError as e:
        return f"[ERROR] OpenAI API가 에러를 반환했습니다: {e}"
    except Exception as e:
        return f"[ERROR] 쿼리 생성 중 예상치 못한 에러가 발생했습니다: {e}"

# 7. MCP 서버 API 엔드포인트
@app.post("/generate-query")
def generate_query(request: QueryRequest):
    query = natural_language_to_cypher(request.message)
    return {"query": query, "parameters": {}}

# 8. 서버 실행
if __name__ == "__main__":
    uvicorn.run("nl2cypher_mcp:app", host="0.0.0.0", port=8000, reload=True)