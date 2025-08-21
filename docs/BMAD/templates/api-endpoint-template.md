# {{method}} {{endpoint_path}}

## Overview
{{description}}

**Method**: `{{method}}`  
**Endpoint**: `{{endpoint_path}}`  
**Version**: {{api_version}}  
**Authentication**: {{authentication_required}}  

## Authentication

{{#if authentication_required}}
### Required Headers
```http
Authorization: Bearer {{api_token}}
Content-Type: application/json
X-API-Version: {{api_version}}
```

### API Key Requirements
- **Scope**: {{required_scopes}}
- **Rate Limit**: {{rate_limit_tier}}
{{/if}}

## Request

### URL Parameters
{{#if url_parameters}}
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
{{#each url_parameters}}
| {{name}} | {{type}} | {{required}} | {{description}} |
{{/each}}
{{/if}}

### Query Parameters
{{#if query_parameters}}
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
{{#each query_parameters}}
| {{name}} | {{type}} | {{required}} | {{default}} | {{description}} |
{{/each}}
{{/if}}

### Request Headers
{{#if request_headers}}
| Header | Required | Description |
|--------|----------|-------------|
{{#each request_headers}}
| {{name}} | {{required}} | {{description}} |
{{/each}}
{{/if}}

### Request Body
{{#if request_body}}
```json
{{request_body_schema}}
```

#### Request Body Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
{{#each request_body_fields}}
| {{name}} | {{type}} | {{required}} | {{description}} |
{{/each}}
{{/if}}

### Request Example

#### cURL
```bash
curl -X {{method}} "{{base_url}}{{endpoint_path}}{{#if query_example}}?{{query_example}}{{/if}}" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json"{{#if request_body}} \
  -d '{{request_body_example}}'{{/if}}
```

#### Python
```python
import requests

url = "{{base_url}}{{endpoint_path}}"
headers = {
    "Authorization": "Bearer YOUR_API_TOKEN",
    "Content-Type": "application/json"
}

{{#if request_body}}
data = {{request_body_example}}
response = requests.{{method_lower}}(url, headers=headers, json=data)
{{else}}
response = requests.{{method_lower}}(url, headers=headers)
{{/if}}

print(response.json())
```

#### JavaScript
```javascript
const response = await fetch('{{base_url}}{{endpoint_path}}', {
  method: '{{method}}',
  headers: {
    'Authorization': 'Bearer YOUR_API_TOKEN',
    'Content-Type': 'application/json'
  }{{#if request_body}},
  body: JSON.stringify({{request_body_example}}){{/if}}
});

const data = await response.json();
console.log(data);
```

## Response

### Success Response ({{success_status_code}})

```json
{{success_response_example}}
```

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
{{#each response_fields}}
| {{name}} | {{type}} | {{description}} |
{{/each}}

### Error Responses

{{#each error_responses}}
#### {{status_code}} - {{status_text}}
{{description}}

```json
{{error_example}}
```
{{/each}}

### Response Headers
{{#if response_headers}}
| Header | Description |
|--------|-------------|
{{#each response_headers}}
| {{name}} | {{description}} |
{{/each}}
{{/if}}

## Rate Limiting

- **Rate Limit**: {{rate_limit}}
- **Rate Limit Window**: {{rate_limit_window}}
- **Rate Limit Headers**:
  - `X-RateLimit-Limit`: {{rate_limit}}
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

### Rate Limit Exceeded (429)
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again later.",
  "retry_after": 60
}
```

## Trading-Specific Information

{{#if trading_specific}}
### Market Hours
- **Trading Hours**: {{trading_hours}}
- **Timezone**: {{timezone}}
- **Market Status Dependency**: {{market_dependency}}

### Data Freshness
- **Update Frequency**: {{update_frequency}}
- **Latency**: {{typical_latency}}
- **Historical Data**: {{historical_data_availability}}

### Position/Order Requirements
{{#if position_requirements}}
- **Minimum Order Size**: {{min_order_size}}
- **Maximum Order Size**: {{max_order_size}}
- **Supported Order Types**: {{supported_order_types}}
{{/if}}
{{/if}}

## SDK Examples

{{#if sdk_examples}}
### Python SDK
```python
from trading_client import TradingClient

client = TradingClient(api_key="YOUR_API_KEY")
{{sdk_python_example}}
```

### Node.js SDK
```javascript
const { TradingClient } = require('trading-sdk');

const client = new TradingClient({ apiKey: 'YOUR_API_KEY' });
{{sdk_nodejs_example}}
```
{{/if}}

## Webhook Integration

{{#if supports_webhooks}}
This endpoint supports real-time updates via webhooks.

### Webhook Configuration
```json
{
  "webhook_url": "https://your-app.com/webhooks/{{webhook_event}}",
  "events": ["{{webhook_events}}"]
}
```

### Webhook Payload
```json
{{webhook_payload_example}}
```
{{/if}}

## Testing

### Test Endpoint
**Sandbox URL**: `{{sandbox_base_url}}{{endpoint_path}}`

### Test Data
```json
{{test_data_example}}
```

### Postman Collection
[Download Postman Collection]({{postman_collection_url}})

## Error Handling Best Practices

```python
def handle_api_request():
    try:
        response = requests.{{method_lower}}(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            # Handle authentication error
            refresh_token()
            return retry_request()
        elif response.status_code == 429:
            # Handle rate limiting
            wait_time = int(response.headers.get('Retry-After', 60))
            time.sleep(wait_time)
            return retry_request()
        else:
            raise
    
    except requests.exceptions.RequestException as e:
        # Handle network errors
        log_error(f"Network error: {e}")
        return None
```

## Performance Considerations

- **Caching**: {{caching_recommendations}}
- **Batch Requests**: {{batch_support}}
- **Compression**: {{compression_support}}
- **Connection Pooling**: {{connection_pooling_recommendations}}

## Security Notes

- **HTTPS Required**: All requests must use HTTPS
- **API Key Security**: Store API keys securely, never in client-side code
- **Request Signing**: {{request_signing_required}}
- **IP Whitelisting**: {{ip_whitelisting_available}}

## Changelog

{{#each changelog}}
### {{version}} - {{date}}
{{changes}}
{{/each}}

## Related Endpoints

{{#each related_endpoints}}
- [{{method}} {{path}}]({{documentation_link}}) - {{description}}
{{/each}}

## Support

- **Documentation**: [API Documentation]({{documentation_url}})
- **Support Email**: {{support_email}}
- **Status Page**: [API Status]({{status_page_url}})

---

*API Endpoint Documentation Template v2.0.0*  
*Generated: {{generation_timestamp}}*  
*BMAD Methodology Documentation*