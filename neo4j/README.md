# Neo4j — Local Graph Database

Local Neo4j deployment for the **clawd** workspace. Intended for graph-based modeling (e.g. Homey home automation: devices, rooms, automations, relationships).

## Quick start

```bash
cd /Users/shailja/clawd/neo4j
docker compose up -d
```

Open **Neo4j Browser**: http://localhost:7474

## Connection details

| Setting | Value |
|---------|-------|
| Browser | http://localhost:7474 |
| Bolt | `bolt://localhost:7687` |
| Username | `neo4j` |
| Password | `neo4j_local_dev` |
| Image | `neo4j:5-community` |
| Container | `neo4j` |

## Verify

```bash
# Container status
docker ps --filter name=neo4j

# HTTP check
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:7474

# Cypher test
docker exec neo4j cypher-shell -u neo4j -p neo4j_local_dev \
  "RETURN 'Neo4j is live' AS message, datetime() AS time;"
```

## Management

```bash
# Stop
docker compose down

# Start
docker compose up -d

# Logs
docker logs neo4j --tail 50

# Interactive shell
docker exec -it neo4j cypher-shell -u neo4j -p neo4j_local_dev
```

## Persistence

Data and logs are stored in Docker volumes:

- `neo4j_data` → `/data`
- `neo4j_logs` → `/logs`

## Memory settings

Configured in `docker-compose.yml` for local dev:

- Heap initial: 512m
- Heap max: 1G
- Page cache: 512m

## Example: Homey graph model

```cypher
CREATE (living:Room {name: 'Living Room'})
CREATE (bedroom:Room {name: 'Bedroom'})
CREATE (light:Device {name: 'Ceiling Light', type: 'light', homey_id: 'abc123'})
CREATE (thermostat:Device {name: 'Thermostat', type: 'climate', homey_id: 'def456'})
CREATE (light)-[:IN_ROOM]->(living)
CREATE (thermostat)-[:IN_ROOM]->(bedroom)
RETURN living, bedroom, light, thermostat;
```

## Related projects

- **n8n** — workflow automation (`../n8n/`)
- **Homey** — smart home hub (external; integrate via API/webhooks)

## Repo path

`clawd/neo4j/docker-compose.yml`
