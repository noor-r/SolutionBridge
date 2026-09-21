"""Build historical incident embeddings and FAISS index for similarity retrieval."""

import json
from pathlib import Path
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

HISTORICAL_INCIDENTS_BASE = [
    {
        "incident_id": "INC-421",
        "title": "Database Connection Pool Exhaustion",
        "summary": "POST /orders returned 500. Database connection timeout. DB latency 4.8s. Order record not persisted.",
        "category": "Database",
        "resolution": "Connection pool exhaustion on Aurora cluster. Increased pool size from 20 to 60 and restarted affected worker service.",
    },
    {
        "incident_id": "INC-382",
        "title": "API Key Authorization Header Malformation",
        "summary": "POST /orders failed with HTTP 401. Invalid API key error. Customer sent Bearer prefix instead of raw X-API-Key token.",
        "category": "Authentication",
        "resolution": "Customer client configured with Bearer auth instead of custom header. Sent updated Postman collection with correct X-API-Key header format.",
    },
    {
        "incident_id": "INC-519",
        "title": "Table Lock Contention on External Order Index",
        "summary": "Elevated response times (4500ms) on GET /orders. Slow SQL query detected. Full table scan on unindexed external_order_id.",
        "category": "Performance",
        "resolution": "Created composite B-tree index on (customer_id, external_order_id). Query latency dropped from 4500ms to 8ms.",
    },
    {
        "incident_id": "INC-604",
        "title": "Ingress Container Out Of Memory (OOM)",
        "summary": "HTTP 503 Service Unavailable returned. CPU 98% and RAM 96%. Kubernetes worker node terminated by OOM killer.",
        "category": "Infrastructure",
        "resolution": "Memory leak identified in legacy XML payload parser. Scaled worker pods from 2 to 5 and updated JSON streaming parser.",
    },
    {
        "incident_id": "INC-215",
        "title": "Silent Write Rollback / Asynchronous Commit Race",
        "summary": "API acknowledged 201 Created but database SELECT returned 0 rows. Transaction rolled back silently before commit phase.",
        "category": "Data Consistency",
        "resolution": "Discovered race condition in async event emitter which dispatched HTTP response before database commit handler finished. Fixed transaction ordering.",
    },
    {
        "incident_id": "INC-198",
        "title": "Missing Required Schema Parameter",
        "summary": "Customer payload rejected with HTTP 422 Unprocessable Entity. Missing required field 'currency_code' in JSON body.",
        "category": "Integration",
        "resolution": "Customer updated ERP export pipeline to include 'currency_code: USD'. Validated payload in staging sandbox.",
    },
    {
        "incident_id": "INC-712",
        "title": "Unhandled Null Pointer in Discount Engine",
        "summary": "HTTP 500 internal server error. NullPointerException in PricingCalculationEngine.applyDiscounts() on null customer tier.",
        "category": "Application",
        "resolution": "Added fallback null-check in pricing engine to default missing tier to standard retail pricing.",
    },
    {
        "incident_id": "INC-820",
        "title": "Customer Webhook Endpoint Timeout",
        "summary": "HTTP 504 Gateway Timeout on POST /webhooks/orders. Customer endpoint timed out after 10000ms. Retries exhausted.",
        "category": "Integration",
        "resolution": "Customer firewall was dropping inbound webhook packets from our IP block. Customer whitelisted gateway CIDR range.",
    },
    {
        "incident_id": "INC-445",
        "title": "Deadlock on Concurrent Order Submissions",
        "summary": "POST /orders failed with 500 DB_DEADLOCK. Deadlock detected during concurrent row updates with identical external order ID.",
        "category": "Database",
        "resolution": "Implemented distributed Redis mutex locking on (customer_id, external_order_id) to serialize duplicate submissions.",
    },
    {
        "incident_id": "INC-332",
        "title": "Stale Cached API Key After Rotation",
        "summary": "Customer received 401 Unauthorized immediately after generating new API credentials. Redis cache held expired key hash.",
        "category": "Authentication",
        "resolution": "Implemented instant Redis cache invalidation webhook on API key rotation in partner portal.",
    },
]


def build_embeddings_and_faiss():
    print("Generating comprehensive corpus of historical incidents...")
    # Expand base templates to 110 diverse historical cases
    incidents_corpus = []
    idx = 100
    for base in HISTORICAL_INCIDENTS_BASE:
        incidents_corpus.append(base)
        # Generate 10 variations per template with realistic details
        for v in range(1, 11):
            idx += 1
            variation = {
                "incident_id": f"INC-{idx}",
                "title": f"{base['title']} (Variation {v})",
                "summary": f"{base['summary']} Environment: us-east-prod-{v % 3 + 1}. Observed impact on cluster {v}.",
                "category": base["category"],
                "resolution": base["resolution"],
            }
            incidents_corpus.append(variation)

    print(f"Total historical incidents in corpus: {len(incidents_corpus)}")

    print("Loading SentenceTransformer model ('all-MiniLM-L6-v2')...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    summaries = [inc["summary"] for inc in incidents_corpus]
    print(f"Encoding {len(summaries)} incident summaries into dense vectors...")
    embeddings = model.encode(summaries, convert_to_numpy=True, normalize_embeddings=True)

    dimension = embeddings.shape[1]
    print(f"Vector dimension: {dimension}")

    # Build FAISS Index (Cosine similarity via inner product on normalized vectors)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    print(f"FAISS index built with {index.ntotal} vectors.")

    # Save artifacts
    index_file = ARTIFACTS_DIR / "faiss_index.bin"
    corpus_file = ARTIFACTS_DIR / "historical_incidents.json"

    faiss.write_index(index, str(index_file))
    with open(corpus_file, "w", encoding="utf-8") as f:
        json.dump(incidents_corpus, f, indent=2)

    print(f"Saved FAISS index to {index_file}")
    print(f"Saved historical incidents to {corpus_file}")

    # Test top-3 query
    test_query = "POST /orders failed with database timeout and high DB latency"
    test_vec = model.encode([test_query], convert_to_numpy=True, normalize_embeddings=True)
    distances, indices = index.search(test_vec, 3)

    print("\n--- Test FAISS Similarity Search ---")
    print(f"Query: '{test_query}'")
    for rank, (idx_match, score) in enumerate(zip(indices[0], distances[0]), start=1):
        matched = incidents_corpus[idx_match]
        print(f"  #{rank} [{matched['incident_id']}] Similarity: {score:.4f} | {matched['title']}")
    print("------------------------------------\n")


if __name__ == "__main__":
    build_embeddings_and_faiss()
