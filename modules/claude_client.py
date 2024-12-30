# modules/claude_client.py
from anthropic import Anthropic
from typing import List, Dict, Optional
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
        self.similarity_threshold = config.get('news.similarity_threshold', 65)

        # 토큰당 비용 설정
        self.input_token_cost = config.get('claude.input_token_cost', 0.003)
        self.output_token_cost = config.get('claude.output_token_cost', 0.015)

        # 뉴스 카테고리 키워드 정의
        self.keywords = {
            '시장_전반': ['금리', '환율', '증시', '코스피', '나스닥', 'ETF', '주가', '지수', '시장', '달러'],
            '기업_산업': ['실적', '투자', '계약', 'M&A', '기업', '매출', '영업이익', '사업', '합병', '인수'],
            '제도_정책': ['규제', '정책', '제도', '금융위', '감독', '개정', '법안', '법률', '시행']
        }

    def determine_category(self, title: str) -> str:
        """뉴스 제목을 기반으로 카테고리 판별"""
        title = title.lower()
        for category, keywords in self.keywords.items():
            if any(keyword in title for keyword in keywords):
                return category
        return '기타'

    def cluster_news(self, news_list: List[Dict]) -> Dict[str, List[Dict]]:
        """뉴스를 카테고리별로 클러스터링"""
        clustered = {
            '시장_전반': [],
            '기업_산업': [],
            '제도_정책': [],
            '기타': []
        }

        # 첫 번째 패스: 카테고리별 분류
        for news in news_list:
            category = self.determine_category(news['title'])
            news['category'] = category
            clustered[category].append(news)

        # 두 번째 패스: 각 카테고리 내에서 유사도 기반 클러스터링
        for category in clustered.keys():
            cluster_groups = []
            used_indices = set()

            for i, news in enumerate(clustered[category]):
                if i in used_indices:
                    continue

                current_cluster = [news]
                for j, other_news in enumerate(clustered[category][i + 1:], start=i + 1):
                    if j in used_indices:
                        continue

                    ratio = fuzz.token_set_ratio(news['title'], other_news['title'])
                    if ratio >= self.similarity_threshold:
                        current_cluster.append(other_news)
                        used_indices.add(j)

                if current_cluster:
                    # 클러스터의 대표 뉴스 선정 (가장 긴 제목을 가진 뉴스)
                    representative = max(current_cluster, key=lambda x: len(x['title']))
                    representative['related_count'] = len(current_cluster) - 1
                    cluster_groups.append(representative)

            clustered[category] = cluster_groups

        return clustered

    def select_news(self, clustered_news: Dict[str, List[Dict]], min_counts: Dict[str, int]) -> List[Dict]:
        """카테고리별 최소 요구사항을 충족하도록 뉴스 선별"""
        selected = []

        # Config에서 설정된 최대 뉴스 개수 사용
        max_items = self.max_news_items
        min_items = 10  # 최소 요구사항

        if max_items < min_items:
            logger.warning(f"설정된 max_news_items({max_items})가 최소 요구사항({min_items})보다 작습니다. {min_items}로 조정됩니다.")
            max_items = min_items

        # 1단계: 각 카테고리별 최소 요구사항 충족
        for category, required in min_counts.items():
            news_pool = clustered_news.get(category, [])
            if not news_pool:
                continue

            # 관련 기사 수와 제목 길이로 정렬
            sorted_news = sorted(
                news_pool,
                key=lambda x: (x.get('related_count', 0), len(x['title'])),
                reverse=True
            )

            # 최소 요구사항만큼 선택
            selected.extend(sorted_news[:required])

        # 2단계: 남은 슬롯 채우기 (max_items 제한)
        remaining_slots = max_items - len(selected)
        if remaining_slots > 0:
            remaining_pool = []
            for category, news_list in clustered_news.items():
                remaining_pool.extend([n for n in news_list if n not in selected])

            # 남은 뉴스들 중에서 중요도순으로 정렬
            additional_news = sorted(
                remaining_pool,
                key=lambda x: (x.get('related_count', 0), len(x['title'])),
                reverse=True
            )[:remaining_slots]

            selected.extend(additional_news)

        logger.info(f"뉴스 선별 완료: 총 {len(selected)}개 (max_items: {max_items})")
        return selected

    def validate_selection(self, selected_news: List[Dict]) -> bool:
        """선별된 뉴스가 요구사항을 충족하는지 검증"""
        if len(selected_news) < 10:
            return False

        categories = {
            '시장_전반': 0,
            '기업_산업': 0,
            '제도_정책': 0
        }

        for news in selected_news:
            category = news.get('category', self.determine_category(news['title']))
            if category in categories:
                categories[category] += 1

        # 카테고리별 최소 요구사항 검증
        return all([
            categories['시장_전반'] >= 4,
            categories['기업_산업'] >= 3,
            categories['제도_정책'] >= 3
        ])

    def clean_and_parse_json(self, content: str) -> Optional[Dict]:
        """Claude 응답의 JSON 파싱 및 정제"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            json_content = content[json_start:json_end]

            def escape_quotes_in_title(match):
                title = match.group(1)
                escaped_title = title.replace('"', '\\"')
                return f'"title": "{escaped_title}"'

            json_content = re.sub(r'"title":\s*"([^"]*(?:"[^"]*)*)"', escape_quotes_in_title, json_content)
            json_content = re.sub(r'\s+', ' ', json_content)
            json_content = json_content.replace('…', '...')
            json_content = json_content.replace('···', '...')
            json_content = json_content.replace('&amp;', '&')

            return json.loads(json_content)

        except Exception as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            return None

    def analyze_with_claude(self, selected_news: List[Dict]) -> Dict:
        """선별된 뉴스에 대한 Claude의 시장 영향도 분석"""
        titles_text = "\n".join([
            f"- {news['news_id']}|||{news['title']}"
            for news in selected_news
        ])

        prompt = f"""다음은 선별된 주요 뉴스 목록입니다. 시장 영향도를 분석해주세요.

        [시장 영향도 분석]
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
                messages=[{"role": "user", "content": prompt}]
            )
            end_time = time.time()

            usage_info = {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
                'api_time': round(end_time - start_time, 2)
            }
            usage_info['cost_usd'] = round(
                (usage_info['input_tokens'] * self.input_token_cost +
                 usage_info['output_tokens'] * self.output_token_cost) / 1000,
                4
            )

            logger.info(f"API 사용량: {usage_info['total_tokens']} tokens")
            logger.info(f"API 호출 시간: {usage_info['api_time']}초")
            logger.info(f"API 사용 비용: ${usage_info['cost_usd']}")

            content = response.content[0].text.strip()
            parsed_response = self.clean_and_parse_json(content)

            if not parsed_response:
                return {'market_analysis': [], 'usage_info': usage_info}

            return {
                'market_analysis': parsed_response.get('market_analysis', []),
                'usage_info': usage_info
            }

        except Exception as e:
            logger.error(f"Claude API 호출 중 오류 발생: {str(e)}")
            return {'market_analysis': [], 'usage_info': {}}

    def analyze_news(self, news_list: List[Dict]) -> Dict:
        """메인 분석 프로세스"""
        try:
            # 1. 뉴스 클러스터링
            clustered = self.cluster_news(news_list)
            logger.info(f"카테고리별 클러스터링 완료: {{k: len(v) for k, v in clustered.items()}}")

            # 2. 카테고리별 최소 요구사항 설정
            min_counts = {
                '시장_전반': 4,
                '기업_산업': 3,
                '제도_정책': 3
            }

            # 3. 뉴스 선별
            selected = self.select_news(clustered, min_counts)
            logger.info(f"1차 선별 완료: {len(selected)}개 뉴스")

            # 4. 선별 결과 검증
            if not self.validate_selection(selected):
                logger.warning("선별된 뉴스가 요구사항을 충족하지 못함")
                # 검증 실패시 카테고리 요구사항을 조정하여 재시도
                min_counts = {k: max(v - 1, 2) for k, v in min_counts.items()}
                selected = self.select_news(clustered, min_counts)

            # 5. Claude API 호출 및 분석
            analysis_result = self.analyze_with_claude(selected)

            logger.info(f"뉴스 분석 완료: {len(selected)}개 선별")
            return {
                'news_items': selected,
                'market_analysis': analysis_result.get('market_analysis', []),
                'usage_info': analysis_result.get('usage_info', {})
            }

        except Exception as e:
            logger.error(f"뉴스 분석 중 오류 발생: {str(e)}")
            return {
                'news_items': [],
                'market_analysis': [],
                'usage_info': {}
            }