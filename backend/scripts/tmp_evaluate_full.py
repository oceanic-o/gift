import asyncio
import sys
from pathlib import Path

repo_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_backend))

from app.core.database import AsyncSessionLocal
from app.services.admin_service import AdminService
import json

async def run_eval():
    async with AsyncSessionLocal() as db:
        admin = AdminService(db)
        print("Running full-cohort evaluation...")
        result = await admin.evaluate_model(cross_validate=False)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(run_eval())
