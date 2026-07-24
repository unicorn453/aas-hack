# Public static DPP endpoint

`dpp-public-api` is a read-only proxy for the five static DPP submodels. It uses
its own admin token internally to read the protected AAS API, but it never
accepts or forwards a caller token.

The live `TimeSeries` submodel is intentionally not in the allowlist and is
therefore still available only through the authenticated AAS API.

Public URL pattern:

```text
https://<server>/public/submodels/<base64url-submodel-id>
```
