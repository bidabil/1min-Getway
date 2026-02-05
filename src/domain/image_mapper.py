# domain/image_mapper.py
import logging
import time

logger = logging.getLogger("1min-gateway.image-mapper")


def format_image_generation_response(result_data):
    """
    LOGIQUE DE DOMAINE PURE :
    Prend une liste de résultats (URLs ou objets) et les normalise au format OpenAI.
    Ne sait pas ce qu'est 'aiRecord' ou '1min.ai'.
    """
    try:
        image_urls = []

        # 1. Normalisation (Logique métier de ton application)
        if isinstance(result_data, list):
            for item in result_data:
                if isinstance(item, str):
                    image_urls.append(item)
                elif isinstance(item, dict) and "url" in item:
                    image_urls.append(item["url"])
        elif isinstance(result_data, str):
            image_urls.append(result_data)

        # 2. Construction de la réponse standard (Indépendant du fournisseur)
        return {"created": int(time.time()), "data": [{"url": url} for url in image_urls]}

    except Exception as e:
        logger.error(f"DOMAIN | Erreur de normalisation image : {str(e)}")
        return {"created": int(time.time()), "data": []}
