import time
import logging

# Logger aligned with the new service-oriented architecture
logger = logging.getLogger("1min-gateway.image-service")

def format_image_generation_response(one_min_response):
    """
    Transforms the 1min.ai API response into the OpenAI Image API format.
    Includes safety checks against malformed or empty responses.
    """
    try:
        # Secure extraction using .get() to prevent crashes if keys are missing
        ai_record = one_min_response.get('aiRecord', {})
        detail = ai_record.get('aiRecordDetail', {})
        image_urls = detail.get('resultObject', [])

        if not image_urls:
            logger.warning("1min.ai provider returned an empty resultObject (no images).")
            return {
                "created": int(time.time()),
                "data": []
            }

        logger.info(f"Image Service: Successfully mapped {len(image_urls)} image(s) to OpenAI format.")
        
        # Mapping to OpenAI standard: {"url": "..."}
        return {
            "created": int(time.time()),
            "data": [{"url": url} for url in image_urls]
        }

    except Exception as e:
        logger.error(f"Image Service Transformation Error: {str(e)}")
        # Returns a fallback compatible OpenAI structure instead of crashing the gateway
        return {
            "created": int(time.time()),
            "data": []
        }