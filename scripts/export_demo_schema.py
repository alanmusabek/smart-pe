"""Compile PostgreSQL schema from project models; never read student records."""
from pathlib import Path
from sqlalchemy import create_mock_engine
from db.db_config import Base
import db.models  # Register all table and enum definitions.


def main():
    statements = []
    def collect(statement, *args, **kwargs):
        statements.append(str(statement.compile(dialect=engine.dialect)).strip() + ';')
    engine = create_mock_engine('postgresql://', collect)
    Base.metadata.create_all(engine, checkfirst=False)
    target = Path(__file__).resolve().parents[1] / 'deployment' / 'demo_schema.sql'
    target.parent.mkdir(exist_ok=True)
    target.write_text('-- Generated from db/models. Contains schema only, no student records.\n\n' + '\n\n'.join(statements) + '\n', encoding='utf-8')
    print(f'Generated {len(statements)} schema statements.')


if __name__ == '__main__':
    main()
