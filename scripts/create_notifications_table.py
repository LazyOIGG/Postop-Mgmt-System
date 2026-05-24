"""Create missing notifications table — run AFTER stopping the backend"""
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'RAG'),
)
cursor = conn.cursor()

# notifications table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        type ENUM('doctor_message','alert','reminder','system') NOT NULL,
        title VARCHAR(255) NOT NULL,
        content TEXT,
        related_id INT,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_username_read (username, is_read),
        INDEX idx_created_at (created_at),
        FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
conn.commit()
print("notifications table created")

# Verify
cursor.execute("SHOW TABLES LIKE 'notifications'")
if cursor.fetchone():
    print("Verified: table exists")

cursor.close()
conn.close()
