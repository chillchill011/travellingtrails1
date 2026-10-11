# LeadGen OAuth public pages

This branch contains only the public-facing OAuth disclosure website for **LeadGen Outreach Automation**, to be deployed to a separate Netlify site at `leadgen.travellingtrails.in`.

This branch was created from the proven `jce-oauth-pages` static-site branch, but all JCE-specific content has been replaced. It is deliberately independent of the Travelling Trails production `main` branch and the JCE deployment. Do **not** merge this branch into `main` or `jce-oauth-pages`.

## Netlify deployment settings

- Repository: `chillchill011/travellingtrails1`
- Production branch: `leadgen-oauth-pages`
- Base directory: leave blank
- Build command: leave blank
- Publish directory: `.`
- Custom domain: `leadgen.travellingtrails.in`
- DNS: follow the Netlify custom-domain verification/instructions for the new site
- HTTPS: verify the certificate and all three URLs are publicly accessible

## Google Auth Platform branding

Use these only after the site has been deployed and tested:

- App name: LeadGen Outreach Automation
- Application home page: `https://leadgen.travellingtrails.in/`
- Privacy policy: `https://leadgen.travellingtrails.in/privacy/`
- Terms of service: `https://leadgen.travellingtrails.in/terms/`
- Authorized domain: `travellingtrails.in`

The n8n OAuth redirect URI is **not** hosted here. Retain the real callback URL supplied by the existing n8n Gmail credential unless a separately tested OAuth/callback migration is explicitly approved. Never point the callback at these static pages.

## Application boundary and Gmail permissions

LeadGen is a privately hosted system for discovery, contact evidence, website/SEO analysis, AI-assisted email drafting, human review, separately authorized outbound Gmail sending and inbound reply/opt-out processing.

Proposed least-privilege Gmail OAuth scopes, subject to confirming the live n8n Gmail nodes:
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.readonly`

Do not request `https://mail.google.com/`, `gmail.modify`, or other broader Gmail scopes without validating a live need. Google may require additional verification for restricted scopes.

This public site **does not** authenticate Gmail accounts, serve the private Campaign Explorer, handle OAuth callbacks, expose n8n, store any OAuth secrets, send messages or access the lead database. All business workflows and credentials remain on the private LeadGen server.

## Safety and maintenance

- Do not change JCE OAuth configuration or its Netlify site.
- Do not modify the `main` Travelling Trails website.
- Do not commit Gmail tokens, OAuth secrets, database exports, private contacts or mailbox content.
- Keep WF-08 globally DISARMED during OAuth migration.
- Preserve WF-09 inbound monitoring, historical sends and active suppressions.
- Historical Telegram approval is not live-send authorization.
- Review public policy content if data handling or third-party processors change.
- The public site being online does **not** mean the OAuth migration, verification, or live email-sending approval is complete.

## Files

- `index.html` — what LeadGen does and Gmail data use
- `privacy/index.html` — data practices and user controls
- `terms/index.html` — private authorized-use terms
- `styles.css` — shared minimal static styling
- `netlify.toml` — Netlify static publish and security headers
- `robots.txt`, `sitemap.xml` — public site discovery metadata
