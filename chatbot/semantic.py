

import hashlib
import json
from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


@lru_cache(maxsize=8)
def _encoded_corpus(fingerprint, corpus):
    model = _encoder()
    return model.encode(list(corpus), normalize_embeddings=True)


def semantic_match(question, records):
    if not records:
        return None, 0.0
    # Article edits immediately change the fingerprint and invalidate matching.
    corpus = tuple(
        " ".join(
            [
                item.get("title", ""),
                item.get("keywords", ""),
                item.get("body", "")[:1800],
            ]
        )
        for item in records
    )
    fingerprint = hashlib.sha256(json.dumps(corpus).encode("utf-8")).hexdigest()
    vectors = _encoded_corpus(fingerprint, corpus)
    query = _encoder().encode([question], normalize_embeddings=True)[0]
    similarities = vectors @ query
    index = int(similarities.argmax())
    return records[index], float(similarities[index])
