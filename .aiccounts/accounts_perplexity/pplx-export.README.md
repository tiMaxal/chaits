# Perplexity Exporter README

**Note:** Not currently any maintained official Perplexity Chat API for exporting chat history (as of 2026-02-02).

## What this tool does
A local GUI that attempts to export Perplexity chats via API endpoints. If your deployment does not expose chat history endpoints, exports will be empty or fail.

## Key limitations
- The async API endpoint that lists async jobs is not a chat history export.
- Some deployments return 404 for /chats and do not provide a chat history API.

## Configuration
- Add an account with API key and Base API URL.
- Optionally override:
  - Chat List Path (default /chats)
  - Chat Detail Path (default /chats/{id})

## Date filtering
You can optionally limit exports by date (From/To). The exporter filters the chat list by any timestamp fields present in list results, then only downloads matching chats.

## Cost notes (example)
If your plan charges USD $5 per 1,000 requests:
- One export uses 1 request for the chat list plus 1 request per chat.
- Estimated cost: (1 + number_of_chats) * 0.005 USD.

## Troubleshooting
- 404 on /chats: your deployment may not expose chat history; try alternate endpoints if provided by Perplexity.
  - THIS ENDPOINT DOES NOT CURRENTLY EXIST
- Empty list: endpoint exists but returns no history for your account.
