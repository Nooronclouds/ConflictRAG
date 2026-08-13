import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# An NLI-fine-tuned DeBERTa. Start with -base (lighter, ~750MB); switch the name
# to ...DeBERTa-v3-large-mnli-fever-anli-ling-wanli for the final, more accurate run.
_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
_device = "cuda" if torch.cuda.is_available() else "cpu"

_tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
_model = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME).to(_device)
_id2label = _model.config.id2label   # {0:'entailment', 1:'neutral', 2:'contradiction'}


def check_pair(premise: str, hypothesis: str) -> dict:
    """Run Natural Language Inference on two statements.
    Returns {label, scores} where label is entailment / neutral / contradiction.
    """
    inputs = _tokenizer(premise, hypothesis, return_tensors="pt",
                        truncation=True, max_length=256).to(_device)
    with torch.no_grad():
        logits = _model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0].tolist()
    scores = {_id2label[i].lower(): round(p, 3) for i, p in enumerate(probs)}
    label = max(scores, key=scores.get)
    return {"label": label, "scores": scores}