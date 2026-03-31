"""
Product service for product analysis APIs.
"""

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from ..constants import (
    ENDPOINT_MARKETING_PRODUCT_INFO,
    ENDPOINT_MARKETING_REPORT_INFO,
    ENDPOINT_PRODUCT_CATEGORIES,
    ENDPOINT_PRODUCT_CREATE,
    PRODUCT_POLL_INTERVAL,
    PRODUCT_POLL_MAX_ATTEMPTS,
    PRODUCT_STATUS_COMPLETED,
)
from ..errors import APIError
from ..models import (
    CreateProductRequest,
    CreateProductResponse,
    Industry,
    ProductInfo,
    ProductReport,
)

if TYPE_CHECKING:
    from ..client import Client


class ProductService:
    """Product analysis APIs (create, poll info, report, categories)."""

    def __init__(self, client: "Client"):
        self.client = client

    def _unwrap(self, resp: dict) -> Any:
        if resp.get("code") != 0:
            raise APIError(
                message=resp.get("msg", "Unknown error"), code=resp.get("code")
            )
        return resp.get("data")

    def create(self, req: CreateProductRequest) -> CreateProductResponse:
        """POST /dashboard/product/create"""
        resp = self.client.post(
            endpoint=ENDPOINT_PRODUCT_CREATE,
            body=req.model_dump(by_alias=True),
            result_model=dict,
        )
        data = self._unwrap(resp)
        return CreateProductResponse.model_validate(data)

    def get_info(self, product_id: str) -> ProductInfo:
        """GET /dashboard/product/candidates/{product_id}/info"""
        endpoint = ENDPOINT_MARKETING_PRODUCT_INFO.format(product_id=product_id)
        resp = self.client.get(endpoint=endpoint, result_model=dict)
        data = self._unwrap(resp)
        return ProductInfo.model_validate(data)

    def get_report(self, report_id: str) -> ProductReport:
        """GET /dashboard/report/info/{report_id}"""
        endpoint = ENDPOINT_MARKETING_REPORT_INFO.format(report_id=report_id)
        resp = self.client.get(endpoint=endpoint, result_model=dict)
        data = self._unwrap(resp)
        return ProductReport.model_validate(data)

    def get_categories(self) -> List[Industry]:
        """GET /dashboard/categories"""
        resp = self.client.get(endpoint=ENDPOINT_PRODUCT_CATEGORIES, result_model=dict)
        data = self._unwrap(resp)
        if not isinstance(data, list):
            raise APIError("Invalid categories response: expected list")
        return [Industry.model_validate(item) for item in data]

    def create_and_wait(
        self,
        product: str,
        attachments: Optional[List[Dict[str, str]]] = None,
        poll_interval: int = PRODUCT_POLL_INTERVAL,
        max_attempts: int = PRODUCT_POLL_MAX_ATTEMPTS,
        on_poll: Optional[Callable[[int, str], None]] = None,
    ) -> ProductReport:
        """Create product and poll until the report is ready."""
        if not product or not product.strip():
            raise ValueError("product must not be empty")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")

        req = CreateProductRequest(product=product, attachments=attachments or [])
        created = self.create(req)

        for attempt in range(1, max_attempts + 1):
            info = self.get_info(created.product_id)

            if on_poll:
                on_poll(attempt, info.status)

            if info.status == PRODUCT_STATUS_COMPLETED:
                report_id = (
                    info.analysis_result.report_id
                    if info.analysis_result
                    else None
                )
                if report_id:
                    return self.get_report(report_id)
                raise APIError("Product analysis completed but report_id is missing")

            if attempt < max_attempts:
                time.sleep(poll_interval)

        total_seconds = poll_interval * max_attempts
        raise APIError(
            f"Product analysis timeout after {max_attempts} attempts ({total_seconds}s)"
        )
