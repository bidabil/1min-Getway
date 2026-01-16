import tiktoken
import logging
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.protocol.instruct.messages import UserMessage

logger = logging.getLogger("1min-relay.tokens")

def calculate_token(sentence, model="DEFAULT"):
    """
    Calcule le nombre de tokens d'une phrase selon le modèle spécifié.
    Extrait de la logique originale du relais.
    """
    try:
        if model.startswith("mistral"):
            # Initialisation du tokenizer Mistral
            model_name = "open-mistral-nemo" 
            tokenizer = MistralTokenizer.from_model(model_name)
            tokenized = tokenizer.encode_chat_completion(
                ChatCompletionRequest(
                    messages=[UserMessage(content=sentence)],
                    model=model_name,
                )
            )
            return len(tokenized.tokens)

        elif model in ["gpt-3.5-turbo", "gpt-4"]:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(sentence))

        else:
            # Par défaut : OpenAI GPT-4
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(sentence))
            
    except Exception as e:
        logger.error(f"Erreur calcul tokens ({model}): {str(e)[:100]}")
        # Retourne une estimation simple en cas d'échec pour ne pas bloquer l'API
        return len(sentence) // 4