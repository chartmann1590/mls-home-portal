# API

## Health

- `GET /health`

## Search

- `POST /api/search`
- Body: `SearchRequest`
- Returns affordability + listings + notes

## Listing Details

- `POST /api/listing-details`
- Returns description, photos, realtor info, AI explanation

## Saved Searches

- `GET /api/saved-searches`
- `POST /api/saved-searches`
- `POST /api/saved-searches/{id}/run`
- `DELETE /api/saved-searches/{id}`

## Saved Listings

- `GET /api/saved-listings`
- `POST /api/saved-listings`
- `DELETE /api/saved-listings/{id}`
