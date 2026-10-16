"""Database connection management with pooling"""

import mysql.connector
from mysql.connector import pooling, Error
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any
from src.config import Config
from src.logger import get_logger

logger = get_logger("database")


class DatabasePool:
    """Manages MySQL connection pool for efficient resource usage"""

    _pool: Optional[pooling.MySQLConnectionPool] = None

    @classmethod
    def initialize(cls):
        """Initialize the connection pool"""
        if cls._pool is not None:
            return

        try:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name=Config.DB_POOL_NAME,
                pool_size=Config.DB_POOL_SIZE,
                pool_reset_session=True,
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                autocommit=False,  # Manual transaction control
            )
            logger.info("Database connection pool initialized")
        except Error as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Context manager for database connections"""
        if cls._pool is None:
            cls.initialize()

        connection = None
        try:
            connection = cls._pool.get_connection()
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    @classmethod
    def close_all(cls):
        """Close all connections in the pool"""
        if cls._pool:
            logger.info("Closing all database connections")


class Database:
    """High-level database operations wrapper"""

    @staticmethod
    def execute_insert(
        table: str,
        columns: List[str],
        values: List[Any]
    ) -> int:
        """Insert a row and return the inserted ID"""
        placeholders = ", ".join(["%s"] * len(values))
        columns_str = ", ".join(columns)
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"

        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                conn.commit()
                inserted_id = cursor.lastrowid
                logger.debug(f"Inserted row {inserted_id} into {table}")
                return inserted_id
            except Error as e:
                conn.rollback()
                logger.error(f"Insert error in {table}: {e}")
                raise
            finally:
                cursor.close()

    @staticmethod
    def execute_update(
        table: str,
        updates: dict,
        where: dict
    ) -> int:
        """Update rows and return count of affected rows"""
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        values = list(updates.values()) + list(where.values())

        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                conn.commit()
                affected = cursor.rowcount
                logger.debug(f"Updated {affected} rows in {table}")
                return affected
            except Error as e:
                conn.rollback()
                logger.error(f"Update error in {table}: {e}")
                raise
            finally:
                cursor.close()

    @staticmethod
    def execute_delete(table: str, where: dict) -> int:
        """Delete rows and return count of affected rows"""
        where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"

        values = list(where.values())

        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                conn.commit()
                affected = cursor.rowcount
                logger.debug(f"Deleted {affected} rows from {table}")
                return affected
            except Error as e:
                conn.rollback()
                logger.error(f"Delete error in {table}: {e}")
                raise
            finally:
                cursor.close()

    @staticmethod
    def fetch_one(query: str, values: tuple = None) -> Optional[Tuple]:
        """Fetch a single row"""
        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values or ())
                result = cursor.fetchone()
                return result
            except Error as e:
                logger.error(f"Fetch error: {e}")
                raise
            finally:
                cursor.close()

    @staticmethod
    def fetch_all(query: str, values: tuple = None) -> List[Tuple]:
        """Fetch all matching rows"""
        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values or ())
                results = cursor.fetchall()
                return results
            except Error as e:
                logger.error(f"Fetch error: {e}")
                raise
            finally:
                cursor.close()

    @staticmethod
    def execute_transaction(operations: List[tuple]) -> bool:
        """Execute multiple operations as a single transaction"""
        with DatabasePool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                for query, values in operations:
                    cursor.execute(query, values)
                conn.commit()
                logger.info(f"Transaction completed with {len(operations)} operations")
                return True
            except Error as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
            finally:
                cursor.close()
