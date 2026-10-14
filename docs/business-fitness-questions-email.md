# Draft email: questions for Business Fitness

Status: draft, not sent. Fill in the bracketed parts before sending. The questions are tracked in [connector-guide.md](connector-guide.md#questions-for-business-fitness-developers--supportbusinessfitnesscom).

---

**To:** developers@businessfitness.com
**Cc:** support@businessfitness.com
**Subject:** Active API – questions before requesting a Power Platform integration

Hi Business Fitness team,

We're building a Microsoft Power Platform custom connector for the Active API, so our Power Automate flows can work with clients, jobs, workpapers and documents in Active. We've generated it from your published Postman collection. Before we submit an integration request, could you help with the questions below?

**Authentication**

1. Your docs describe the authorisation code flow with PKCE. Power Platform connectors exchange the code server-side with a client ID and secret, and Microsoft doesn't document PKCE support for them. Can you issue a confidential client (client ID and secret) for this integration, or is PKCE mandatory?
2. Each Power Platform connector gets its own Microsoft-hosted redirect URL, in the form `https://global.consent.azure-apim.net/redirect/<connector-id>`. Does that meet your requirement for "a Microsoft first-party endpoint tied to your tenant"?
3. Power Platform has no post-logout redirect. Is the post-logout URL optional, or what should we provide?
4. How long do access tokens and refresh tokens (with `offline_access`) last, and do refresh tokens expire if they aren't used?

**Access and environment**

5. Is API access included in our Active subscription, or is it only for partners?
6. Is there a sandbox we can test against, and can it be seeded with demo clients?

**Behaviour**

7. Some list endpoints show a filter repeated in the query string, such as `ExternalId` and `Code` on `GET /workflow/v1/deliverables`. Should several values be sent as repeated keys (`ExternalId=a&ExternalId=b`) or comma-separated?
8. Would writing to clients through the API conflict with Active Sync, our practice-management import? For example, could Active Sync overwrite fields updated through the API?
9. We'll keep within the firm limits of 120 requests per minute and 10 concurrent. Could a grace period be arranged for occasional bulk loads?

**A possible issue in the collection**

10. In the Documents API, "Create document" is listed as `GET {{base_url}}/documents/v1/documents`, the same as "List documents". Should it be `POST`?

Once we have your answers, we'll send the integration request with the integration name, scopes, logo, service-account user and redirect URL.

Thanks,
[Your name]
[Firm name]
[Phone]
