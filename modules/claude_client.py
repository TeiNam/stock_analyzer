# modules/claude_client.py
from anthropic import Anthropic
from typing import List, Dict
import json
import re
import time
from utils.config import Config
from utils.logger import setup_logger
from fuzzywuzzy import fuzz

logger = setup_logger(__name__)
config = Config.get_instance()


class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = config.get('claude.model')
        self.max_tokens = config.get('claude.max_tokens')
        self.max_news_items = config.get('claude.max_news_items')
        self.similarity_threshold = config.get('news.similarity_threshold', 65)  # 유사도 임계값

        # 토큰당 비용 설정
        self.input_token_cost = config.get('claude.input_token_cost', 0.003)
        self.output_token_cost = config.get('claude.output_token_cost', 0.015)

    # modules/claude_client.py의 clean_and_parse_json 메소드 수정

    def clean_and_parse_json(self, content: str) -> Dict:
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_content = content[json_start:json_end]

            # 제목에 포함된 따옴표 이스케이프 처리
            def escape_quotes_in_title(match):
                title = match.group(1)
                # 제목 내의 따옴표를 이스케이프
                escaped_title = title.replace('"', '\\"')
                return f'"title": "{escaped_title}"'

            # "title": "..." 패턴에서 따옴표 처리
            json_content = re.sub(r'"title":\s*"([^"]*(?:"[^"]*)*)"', escape_quotes_in_title, json_content)

            # 기본 정리
            json_content = re.sub(r'\s+', ' ', json_content)
            json_content = json_content.replace('…', '...')
            json_content = json_content.replace('···', '...')
            json_content = json_content.replace('&amp;', '&')

            try:
                return json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {str(e)}")
                logger.error(f"오류 위치: 라인 {e.lineno}, 컬럼 {e.colno}")
                problem_area = e.doc[max(0, e.pos - 30):min(len(e.doc), e.pos + 30)]
                logger.error(f"문제의 문자: {problem_area}")

                # 백업 방법: 더 강력한 따옴표 처리
                json_content = re.sub(r'(?<="title":\s*")(.*?)(?="(?:\s*,|\s*}))',
                                      lambda m: m.group(1).replace('"', '\\"'),
                                      json_content)

                try:
                    return json.loads(json_content)
                except json.JSONDecodeError as e2:
                    logger.error(f"백업 JSON 파싱 오류: {str(e2)}")
                    return None

        except Exception as e:
            logger.error(f"JSON 처리 중 예외 발생: {str(e)}")
            return None

    def analyze_news(self, news_list: List[Dict]) -> Dict:
        """
        1) 뉴스 리스트를 유사 기사 클러스터링
        2) 대표 기사만 Claude에 전달
        3) Claude 응답을 parsing
        """
        # 유사 기사 클러스터링
        clustered = []
        used_indices = set()

        for i, news_item in enumerate(news_list):
            if i in used_indices:
                continue

            cluster = [news_item]
            for j, other_item in enumerate(news_list[i + 1:], start=i + 1):
                if j in used_indices:
                    continue
                ratio = fuzz.token_set_ratio(news_item['title'], other_item['title'])
                if ratio >= self.similarity_threshold:
                    cluster.append(other_item)
                    used_indices.add(j)
            clustered.append(cluster)

        # 대표 기사 목록 생성
        summarized_list = []
        for cluster in clustered:
            representative = cluster[0]
            representative['related_count'] = len(cluster) - 1
            summarized_list.append(representative)

        news_map = {str(news['news_id']): news for news in summarized_list}

        titles_text = "\n".join([
            f"- {item['news_id']}|||{item['title']}"
            for item in summarized_list
        ])

        prompt = f"""다음은 오늘의 뉴스 제목 목록입니다. 두 파트로 나누어 분석해주세요.

        [파트 1] 주요 뉴스 선별
        주식 투자자의 관점에서 가장 중요한 뉴스 {self.max_news_items}개를 선별해주세요.
        다음 기준으로 뉴스를 평가해주세요:
        1. 시장 전반에 영향을 미치는 거시경제 뉴스 (금리, 환율, 정책 등)를 최우선으로 고려
        2. 주요 기업이나 산업 전반에 영향을 미치는 뉴스를 그 다음으로 고려
        3. 비슷한 내용을 다루는 기사가 많을수록 해당 이슈의 중요도가 높다고 판단
        4. 개별 기업의 경우, 시가총액이 크거나 산업 영향력이 큰 기업 위주로 선정
        5. 주요 기업들의 소식 (애플, 아마존, 엔비디아, SK하이닉스, openai, 브로드컴, MS, SK텔레콤의 소식)
        6. 미국 증시, 뉴욕 증시, 나스닥, S&P 소식 반드시 포함
        7. 비트코인에 대한 소식 제외     

        [파트 2] 시장 영향도 분석
        선별된 뉴스들을 종합적으로 분석하여 3-5개의 주요 시장 영향 포인트를 도출해주세요.
        각 포인트별로 다음 내용을 포함해주세요:
        - 주제 (예: 환율 리스크, 반도체 업황 등)
        - 시장 영향 (Positive/Negative/Neutral)
        - 영향력 점수 (-5 ~ +5, 숫자가 클수록 긍정적)
        - 영향 받을 것으로 예상되는 섹터나 종목들
        - 영향의 지속 기간 (단기/중기/장기)
        - 구체적인 분석 내용

        뉴스 목록:
        {titles_text}

        JSON 형식으로 다음과 같이 응답해주세요:
        {{
            "news_list": [
                {{
                    "news_id": "뉴스 ID (|||앞의 숫자)",
                    "title": "뉴스 제목 (|||뒤의 제목)",
                    "importance": 중요도(1-10),
                    "reason": "선정 이유",
                    "related_count": 유사한 기사 수
                }}
            ],
            "market_analysis": [
                {{
                    "topic": "분석 주제",
                    "impact": "Positive/Negative/Neutral",
                    "score": 영향력 점수(-5 ~ +5),
                    "affected_sectors": ["영향 받을 섹터/종목 목록"],
                    "duration": "단기/중기/장기",
                    "analysis": "상세 분석 내용"
                }}
            ]
        }}"""

        try:
            start_time = time.time()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            end_time = time.time()

            # API 사용량 로깅
            usage_info = {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
                'api_time': round(end_time - start_time, 2)
            }

            # Claude 비용 계산
            cost = (usage_info['input_tokens'] * self.input_token_cost / 1000) + \
                   (usage_info['output_tokens'] * self.output_token_cost / 1000)
            usage_info['cost_usd'] = round(cost, 4)

            logger.info(f"API 사용량: {usage_info['total_tokens']} tokens "
                        f"(입력: {usage_info['input_tokens']}, "
                        f"출력: {usage_info['output_tokens']})")
            logger.info(f"API 호출 시간: {usage_info['api_time']}초")
            logger.info(f"API 사용 비용: ${usage_info['cost_usd']}")

            content = response.content[0].text.strip()
            parsed_response = self.clean_and_parse_json(content)

            if not parsed_response:
                logger.error("JSON 응답 처리 실패")
                return {
                    'news_items': [],
                    'market_analysis': [],
                    'usage_info': usage_info
                }

            # 뉴스 항목 처리
            result_news = []
            used_ids = set()

            for item in parsed_response.get('news_list', []):
                news_id = str(item.get('news_id'))
                if news_id and news_id not in used_ids:
                    original_news = news_map.get(news_id)
                    if original_news:
                        used_ids.add(news_id)
                        item.update({
                            'link': original_news['link'],
                            'section': original_news['section'],
                            'news_id': original_news['news_id'],
                            'pub_time': original_news['pub_time'],
                            'title': original_news['title']
                        })
                        result_news.append(item)
                        logger.info(f"뉴스 매칭 성공: {item['title']}")
                    else:
                        logger.warning(f"존재하지 않는 news_id: {news_id}")
                else:
                    logger.info(f"중복된 news_id 제외 또는 누락: {news_id}")

            if not result_news:
                logger.error("매칭된 뉴스가 없습니다.")
            else:
                logger.info(f"총 {len(result_news)}개의 뉴스가 선택되었습니다.")

            return {
                'news_items': result_news,
                'market_analysis': parsed_response.get('market_analysis', []),
                'usage_info': usage_info
            }

        except Exception as e:
            logger.error(f"API 호출 중 오류 발생: {str(e)}")
            return {
                'news_items': [],
                'market_analysis': [],
                'usage_info': usage_info
            }