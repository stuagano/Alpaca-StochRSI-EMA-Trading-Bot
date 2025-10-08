# Grafana Dashboards

Place JSON dashboard definitions in this directory to have them provisioned automatically when Grafana starts.

A minimal example is shown below:

```json
{
  "annotations": {"list": []},
  "editable": true,
  "panels": [],
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["alpaca-scalper"],
  "time": {"from": "now-6h", "to": "now"},
  "timezone": "",
  "title": "Local Crypto Scalper",
  "version": 1
}
```
