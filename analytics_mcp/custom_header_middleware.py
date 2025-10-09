
from fastmcp.server.middleware import Middleware, MiddlewareContext
from contextvars import ContextVar
import logging

logger = logging.getLogger(__name__)

request_headers_context: ContextVar[dict] = ContextVar('request_headers_context', default={})


class CustomHeaderMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        logger.info(f"Processing method: {context.method}")
        
        fastmcp_ctx = context.fastmcp_context
        
        headers = {}
        try:
            http_request = fastmcp_ctx.get_http_request()
            if http_request:
                headers = dict(http_request.headers)
        except Exception as e:
            logger.error(f"get_http_request() failed: {e}")
        
        request_headers_context.set({
            'headers': headers,
        })
        
        result = await call_next(context)
        return result



