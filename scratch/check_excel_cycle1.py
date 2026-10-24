import io, openpyxl
from app.presentation.api.dependencies import initialize_database_engine, get_session
from app.infrastructure.repositories.admin_console_repository_impl import SqlAlchemyAdminConsoleRepository

initialize_database_engine()
s = next(get_session())
repo = SqlAlchemyAdminConsoleRepository(s)

# Let's export for division_id=None, cycle_id=1
content, filename = repo.export_assessment_gaps_excel(1, None, 1, None)
wb = openpyxl.load_workbook(io.BytesIO(content))

for name in wb.sheetnames:
    ws = wb[name]
    print(f"Sheet: {name}, Rows: {ws.max_row}")
    # Print rows 1 to 5
    for r in range(1, min(6, ws.max_row + 1)):
        row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        print(f"  R{r}: {row_vals}")

s.close()
