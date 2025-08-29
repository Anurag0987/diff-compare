import sqlite3
import os

def fix_database():
    db_path = 'progress.db'
    
    print("Fixing database schema...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Show current data
            print("Current database content:")
            cursor.execute('SELECT * FROM file_progress')
            rows = cursor.fetchall()
            for row in rows:
                print(f"  {row}")
            
            # Drop the old table
            print("\nDropping old table...")
            cursor.execute('DROP TABLE IF EXISTS file_progress')
            
            # Create new table with correct schema
            print("Creating new table with correct schema...")
            cursor.execute('''
                CREATE TABLE file_progress (
                    file_key TEXT PRIMARY KEY,
                    flag TEXT,
                    comment TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolved_diffs TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            print("Database schema fixed!")
            
            # Show the new empty table structure
            cursor.execute("PRAGMA table_info(file_progress)")
            columns = cursor.fetchall()
            print("\nNew table structure:")
            for col in columns:
                print(f"  {col}")
            
            conn.commit()
            
    except Exception as e:
        print(f"Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()