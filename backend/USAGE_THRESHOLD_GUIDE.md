# Unified Server - Usage Threshold Configuration Guide

## Overview
The unified server now supports granular control over chat usage limits with separate thresholds for:
- Chats **WITH** document retrieval
- Chats **WITHOUT** document retrieval  
- **TOTAL** chats

## Configuration

Located at the top of `src/api/unified_server.py` (lines 34-42):

```python
# 📊 USAGE THRESHOLDS - Control how many chats allowed for each type
# Set to -1 to disable limit for that type
THRESHOLD_WITH_RETRIEVAL = 100        # ← Max chats WITH document retrieval (set -1 to disable)
THRESHOLD_WITHOUT_RETRIEVAL = 50      # ← Max chats WITHOUT document retrieval (set -1 to disable)
THRESHOLD_TOTAL = 150                 # ← Max total chats (set -1 to disable)
```

## How It Works

### Testing Mode (DEPLOYMENT_MODE = "testing")

When a user sends a message:
1. System retrieves documents using the RAG pipeline
2. Checks **THREE thresholds**:
   - If `has_documents`: Checks `THRESHOLD_WITH_RETRIEVAL`
   - If no documents: Checks `THRESHOLD_WITHOUT_RETRIEVAL`
   - Always checks: `THRESHOLD_TOTAL`
3. Returns usage statistics showing:
   - `total` - Total chats
   - `with_retrieval` - Chats with documents
   - `without_retrieval` - Chats without documents

### Android Mode (DEPLOYMENT_MODE = "android")

1. Checks both `THRESHOLD_WITH_RETRIEVAL` and `THRESHOLD_TOTAL`
2. Returns simplified response with usage count
3. Assumes retrieval is always used (increments `with_retrieval`)

## Examples

### Example 1: Disable All Limits (Unlimited Free Tier)
```python
THRESHOLD_WITH_RETRIEVAL = -1         # Unlimited with retrieval
THRESHOLD_WITHOUT_RETRIEVAL = -1      # Unlimited without retrieval
THRESHOLD_TOTAL = -1                  # Unlimited total
```

### Example 2: Generous Free Plan
```python
THRESHOLD_WITH_RETRIEVAL = 200        # 200 chats with documents
THRESHOLD_WITHOUT_RETRIEVAL = 100     # 100 chats without documents
THRESHOLD_TOTAL = 300                 # 300 total chats
```

### Example 3: Conservative Free Plan (Android)
```python
THRESHOLD_WITH_RETRIEVAL = 50         # 50 chats with documents
THRESHOLD_WITHOUT_RETRIEVAL = 25      # 25 chats without documents
THRESHOLD_TOTAL = 75                  # 75 total chats
```

### Example 4: Asymmetric Limits
```python
THRESHOLD_WITH_RETRIEVAL = 150        # Generous with retrieval (more valuable)
THRESHOLD_WITHOUT_RETRIEVAL = 30      # Limited without retrieval (less valuable)
THRESHOLD_TOTAL = 200                 # Overall cap
```

## Response Examples

### Testing Mode - Within Limits (Success)
```json
{
  "reply": "Your answer here",
  "documents": [...],
  "has_retrieval": true,
  "usage_stats": {
    "total": 5,
    "with_retrieval": 3,
    "without_retrieval": 2
  },
  "error": null
}
```

### Testing Mode - With Retrieval Limit Exceeded
```json
{
  "error": "With-retrieval limit (100) reached. Please subscribe to continue.",
  "used_with_retrieval": 100,
  "limit_with_retrieval": 100,
  "reply": null
}
```

### Testing Mode - Without Retrieval Limit Exceeded
```json
{
  "error": "Without-retrieval limit (50) reached. Please subscribe to continue.",
  "used_without_retrieval": 50,
  "limit_without_retrieval": 50,
  "reply": null
}
```

### Android Mode - Within Limits (Success)
```json
{
  "allowed": true,
  "reply": "Your answer here",
  "usage_now": 11,
  "usage_with_retrieval": 8,
  "limit": 100,
  "processing_time": 1.23,
  "error": null
}
```

### Android Mode - Limit Exceeded
```json
{
  "allowed": false,
  "error": "With-retrieval limit (100) reached. Please subscribe to continue.",
  "used": 100,
  "limit": 100,
  "reply": null
}
```

## Error Codes

- **HTTP 429** (Testing Mode): Limit exceeded - rate limiting applies
- **Boolean False** (Android Mode): Limit exceeded - `"allowed": false`

## Key Features

✅ **Separate Thresholds**: Control different types of queries independently  
✅ **Flexible Disabling**: Set to -1 to disable any threshold  
✅ **Three-Layer Control**: With retrieval, without retrieval, and total  
✅ **Transparent Reporting**: Users see their current usage  
✅ **Production Ready**: Works with both testing and Android modes  

## Switching Between Plans

To implement a subscription system:
1. Store user tier in database (free, premium, enterprise)
2. Dynamically calculate thresholds based on tier
3. Fetch thresholds from database instead of hardcoded values

Example:
```python
def get_user_thresholds(email):
    user = get_user(email)
    tier = get_user_tier(email)  # free, premium, enterprise
    
    if tier == "free":
        return {"with_retrieval": 100, "without_retrieval": 50, "total": 150}
    elif tier == "premium":
        return {"with_retrieval": 500, "without_retrieval": 250, "total": 750}
    else:  # enterprise
        return {"with_retrieval": -1, "without_retrieval": -1, "total": -1}
```
