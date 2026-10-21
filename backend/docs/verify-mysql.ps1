param([Parameter(Mandatory=$true)][string]$DatabaseUrl)
$env:DATABASE_URL = $DatabaseUrl
python -m alembic upgrade head
python -c "from sqlalchemy import create_engine,inspect; import os; e=create_engine(os.environ['DATABASE_URL']); print(sorted(inspect(e).get_table_names()))"
