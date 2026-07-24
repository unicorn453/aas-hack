# Digital Product Passport frontend

This Next.js frontend is the active product-focused UI. It reads AAS shell and
submodel data from the public DPP facade at runtime, so the sidebar reflects the
registered assets instead of local fixture data.

Run locally from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

The upload page authenticates against Keycloak and sends `.aasx` packages to the
protected `/upload` gateway.
