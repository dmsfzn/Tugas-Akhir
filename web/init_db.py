import mysql.connector
import os

def init_db():
    print("Connecting to MySQL server...")
    try:
        # Connect to MySQL server without specifying database
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        cursor = conn.cursor()
        
        # Read the schema.sql file
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        print(f"Reading schema from: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Execute the SQL statements
        print("Executing schema...")
        # Split statements by ';' and execute them one by one
        # Because we have multiple statements, we need to handle them properly
        # mysql.connector has multi=True for this purpose
        results = cursor.execute(sql_script, multi=True)
        
        for result in results:
            if result.with_rows:
                result.fetchall()
                
        conn.commit()
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    init_db()
