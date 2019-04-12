#!/usr/bin/python3
import os
import sqlite3
class SpabModel:

    def __init__(self):
        self.Waypoints = []
        self.pendingWaypoints = [] # Expect each pending waypoint as a tuple in the form (id, latitude, longitude)
        self.Home = ()
        self.LastLocation = {}
        self.mode = None
        self.is_armed = None
        self.is_enabled = None
        self.channels = None
        self.attitude_data = None
        self.databaseFilePath = 'SpabModel.sqlite3'

    def create_or_recreate_database(self):
        # Delete any pre-existing database from the filesystem
        if (os.path.exists(self.databaseFilePath)):
            os.remove(self.databaseFilePath)
        # Create a new database
        db_conn = sqlite3.connect(self.databaseFilePath)
        db_cursor = db_conn.cursor()
        db_cursor.execute('CREATE TABLE waypoints(id INTEGER PRIMARY KEY, latitude REAL, longitude REAL)')
        db_conn.close()

    def persist_waypoints(self):
        # Connect with database
        db_conn = sqlite3.connect(self.databaseFilePath)
        db_cursor = db_conn.cursor()
        # Clear old values
        db_cursor.execute('DELETE FROM waypoints')
        db_conn.commit()
        # Store current values
        for waypoint in self.pendingWaypoints:
            db_cursor.execute('''INSERT INTO waypoints(id, latitude, longitude)
                VALUES(?,?,?)''', waypoint)
        db_conn.commit()
        # Close database connection
        db_conn.close()

    def load_waypoints(self):
        db_conn = sqlite3.connect(self.databaseFilePath)
        db_cursor = db_conn.cursor()
        # Retrieve waypoint data from database
        db_cursor.execute('SELECT id, latitude, longitude FROM waypoints')
        all_waypoint_rows = db_cursor.fetchall()
        # Clear internal representation of waypoints, and recreate from database data
        self.pendingWaypoints.clear()
        for row in all_waypoint_rows:
            self.pendingWaypoints.append((row[0], row[1], row[2]))
        db_conn.close()
