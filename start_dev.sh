#!/bin/bash
#ssh root@test.dashboarddeelmobiliteit.nl -L 5432:localhost:5432
uvicorn main:app --reload
