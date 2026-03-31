"""
Marketing service for the WyseOS SDK Python.
"""

from typing import TYPE_CHECKING, Any, Dict

from ..constants import (
    ENDPOINT_MARKETING_PRODUCT_INFO,
    ENDPOINT_MARKETING_REPORT_INFO,
    ENDPOINT_MARKETING_REPORT_UPDATE,
    ENDPOINT_MARKETING_RESEARCH_TWEETS,
)

if TYPE_CHECKING:
    from ..client import Client


class MarketingService:
    """Marketing-related API operations: product info, reports, research tweets."""

    def __init__(self, client: "Client"):
        self.client = client

    def _unwrap(self, resp: dict) -> Any:
        if resp.get("code") != 0:
            from ..errors import APIError
            raise APIError(message=resp.get("msg", "Unknown error"), code=resp.get("code"))
        return resp.get("data")

    def get_product_info(self, product_id: str) -> Dict[str, Any]:
        """GET /dashboard/product/candidates/{product_id}/info"""
        endpoint = ENDPOINT_MARKETING_PRODUCT_INFO.format(product_id=product_id)
        resp = self.client.get(endpoint=endpoint, result_model=dict)
        return self._unwrap(resp)

    def get_report_detail(self, report_id: str) -> Dict[str, Any]:
        """GET /dashboard/report/info/{report_id}"""
        endpoint = ENDPOINT_MARKETING_REPORT_INFO.format(report_id=report_id)
        resp = self.client.get(endpoint=endpoint, result_model=dict)
        return self._unwrap(resp)

    def update_report(self, report_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST /dashboard/report/update/{report_id}"""
        endpoint = ENDPOINT_MARKETING_REPORT_UPDATE.format(report_id=report_id)
        resp = self.client.post(endpoint=endpoint, body=data, result_model=dict)
        return self._unwrap(resp)

    def get_research_tweets(self, query_id: str) -> Any:
        """GET /dashboard/product/query/results/{query_id}/lists"""
        endpoint = ENDPOINT_MARKETING_RESEARCH_TWEETS.format(query_id=query_id)
        resp = self.client.get(endpoint=endpoint, result_model=dict)
        return self._unwrap(resp)
