# Dashboarddeelmobiliteit policy api

This api is developed to make it possible for municipalities to create policies and share them via MDS with operators. This api is part of the dashboarddeelmobiliteit (dashboarddeelmobiliteit.nl).  

## How to test

### ssh tunnels
```bash
ssh -L 5433:10.133.75.95:5432 root@auth.deelfietsdashboard.nl
```

# UV

This project is migrated to uv, you can run fastapi in dev environment with

uv run fastapi dev

In prod you can use

uv run fastapi run
