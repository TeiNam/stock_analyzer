# modules/claude_client.py
from anthropic import Anthropic
from typing import List, Dict
import json
from utils.config import Config
from utils.logger import setup_logger
from utils.constants import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, MAX_NEWS_ITEMS
from fuzzywuzzy import fuzz

logger = setup_logger(__name__)
config = Config.get_instance()


class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = config.get('claude.model', CLAUDE_MODEL)
        self.max_tokens = config.get('claude.max_tokens', CLAUDE_MAX_TOKENS)

    def extract_json_from_response(response_content: str) -> str:
        # JSON 시작점을 찾는다
        start_index = response_content.find("[")
        if start_index == -1:
            # '[' 문자가 없으면 JSON이 아니라고 판단
            return ""

        # 혹시 끝 부분 ']'도 제대로 있는지 확인
        end_index = response_content.rfind("]")
        if end_index == -1 or end_index < start_index:
            return ""

        # 중간에 trim
        possible_json = response_content[start_index:end_index + 1].strip()
        return possible_json

    def analyze_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        1) 뉴스 리스트를 유사 기사 클러스터링
        2) 대표 기사만 Claude에 전달
        3) Claude 응답을 parsing
        """
        # ========================
        # 1) 유사 기사 클러스터링
        # ========================
        clustered = []
        used_indices = set()

        for i, news_item in enumerate(news_list):
            if i in used_indices:
                continue

            cluster = [news_item]
            for j, other_item in enumerate(news_list[i+1:], start=i+1):
                if j in used_indices:
                    continue
                ratio = fuzz.token_set_ratio(news_item['title'], other_item['title'])
                if ratio >= 65:  # 유사도 65% 이상이면 동일 그룹
                    cluster.append(other_item)
                    used_indices.add(j)
            clustered.append(cluster)

        # 대표 기사 목록 생성
        summarized_list = []
        for cluster in clustered:
            representative = cluster[0]
            representative['related_count'] = len(cluster) - 1
            summarized_list.append(representative)

        # 여기서 Claude에게 전달할 뉴스 목록을 summarized_list로 제한
        news_map = {str(news['news_id']): news for news in summarized_list}

        # titles_text 생성 등 기존 로직 유지...
        titles_text = "\n".join([
            f"- {item['news_id']}|||{item['title']}"
            for item in summarized_list
        ])

        prompt = f"""다음은 오늘의 뉴스 제목 목록입니다. 주식 투자자의 관점에서 가장 중요한 뉴스 {MAX_NEWS_ITEMS}개를 선별해주세요.

      다음 기준으로 뉴스를 평가해주세요:
      1. 시장 전반에 영향을 미치는 거시경제 뉴스 (금리, 환율, 정책 등)를 최우선으로 고려
      2. 주요 기업이나 산업 전반에 영향을 미치는 뉴스를 그 다음으로 고려
      3. 비슷한 내용을 다루는 기사가 많을수록 해당 이슈의 중요도가 높다고 판단
      4. 개별 기업의 경우, 시가총액이 크거나 산업 영향력이 큰 기업 위주로 선정
      5. 주요 기업들의 소식 (애플, 아마존, 엔비디아, SK하이닉스, openai의 소식)
      6. 미국 증시, 뉴욕 증시, 나스닥, S&P 소식 반드시 포함
      7. 요약 결과가 무조건 최소 20개의 기사를 보장     

      중복되는 내용의 기사들은 가장 핵심적인 제목 하나만 선택하되, 
      중복 기사가 많은 이슈일수록 더 높은 중요도 점수(1-10)를 부여해주세요.

      중요: |||를 기준으로 왼쪽의 뉴스 ID를 반드시 포함해서 응답해주세요.

      뉴스 목록:
      {titles_text}

      JSON 형식으로 다음과 같이 응답해주세요:
      [
          {{
              "news_id": "뉴스 ID (|||앞의 숫자)",
              "title": "뉴스 제목 (|||뒤의 제목)",
              "importance": 중요도(1-10),
              "reason": "투자 관점에서의 중요도 및 영향, 유사 기사 수 언급",
              "related_count": 유사한 기사 수
          }}
      ]

      Example response:
      {{
          "news_id": "12345",
          "title": "Fed, 올해 3차례 금리인하 시사...파월 '인플레이션 안정세'",
          "importance": 9,
          "reason": "시장 전반 영향을 미치는 금리 정책 관련 뉴스, 유사 기사 12건 발견",
          "related_count": 12
      }}
      """

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text
            logger.debug(f"Claude API Response: {content}")

            try:
                analyzed_news = json.loads(content)
                if isinstance(analyzed_news, list):
                    result_news = []
                    used_ids = set()

                    for item in analyzed_news:
                        news_id = str(item.get('news_id'))
                        if news_id and news_id not in used_ids:
                            original_news = news_map.get(news_id)
                            if original_news:
                                used_ids.add(news_id)
                                # 원본 정보로 업데이트
                                item.update({
                                    'link': original_news['link'],
                                    'section': original_news['section'],
                                    'news_id': original_news['news_id'],
                                    'pub_time': original_news['pub_time'],
                                    'title': original_news['title']
                                })
                                result_news.append(item)
                            else:
                                logger.warning(f"존재하지 않는 news_id: {news_id}")
                        else:
                            logger.info(f"중복된 news_id 제외 또는 누락: {news_id}")

                    if not result_news:
                        logger.error("매칭된 뉴스가 없습니다.")

                    return result_news

                else:
                    logger.error(f"Invalid response format. Expected list but got: {type(analyzed_news)}")
                    return []

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}\nResponse content: {content}")
                return []
            except Exception as e:
                logger.error(f"Claude API 호출 중 오류 발생: {str(e)}")
                return []

        except Exception as e:
            logger.error(f"Claude API 호출 중 오류 발생: {str(e)}")
            return []