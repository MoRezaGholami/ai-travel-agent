"""SQLite persistence + seed data for the mock travel backend.

Schema v3:
  flights / hotels  -> searchable catalog
  bookings          -> real reservations (id, status, JSON details)
  meta              -> schema version for migrations
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "travel.db"
SCHEMA_VERSION = 3


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection to the travel database.

    Creates the data/ folder if needed. Enables foreign keys and
    returns rows as sqlite3.Row (dict-like access by column name).
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _current_schema_version(conn: sqlite3.Connection) -> int:
    """Read schema_version from meta table, or 0 if not set yet."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    return int(row["value"]) if row else 0


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables, or rebuild them when schema version changes.

    If the stored version != SCHEMA_VERSION, catalog and booking tables
    are dropped and recreated so column definitions stay in sync with code.
    """
    version = _current_schema_version(conn)
    if version != SCHEMA_VERSION:
        conn.executescript(
            """
            DROP TABLE IF EXISTS bookings;
            DROP TABLE IF EXISTS hotels;
            DROP TABLE IF EXISTS flights;
            """
        )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS flights (
            id TEXT PRIMARY KEY,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            airline TEXT NOT NULL,
            flight_number TEXT NOT NULL,
            price REAL NOT NULL,
            seats_available INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hotels (
            id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            name TEXT NOT NULL,
            stars INTEGER NOT NULL,
            price_per_night REAL NOT NULL,
            rooms_available INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            booking_type TEXT NOT NULL CHECK (booking_type IN ('flight', 'hotel')),
            item_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
            total_price REAL NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def seed_if_empty(conn: sqlite3.Connection) -> None:
    """Ensure full flight/hotel catalog exists (INSERT OR IGNORE).

    Safe on existing DBs: adds new ids without wiping bookings or inventory.
    """
    conn.executemany(
            """
            INSERT OR IGNORE INTO flights (
                id, origin, destination, departure_date,
                departure_time, arrival_time, duration_minutes,
                airline, flight_number, price, seats_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("FL001", "Tehran", "Istanbul", "2026-11-10", "08:30", "11:45", 195, "Turkish Airlines", "TK873", 320.0, 12),
                ("FL002", "Tehran", "Istanbul", "2026-11-10", "14:10", "17:20", 190, "Pegasus", "PC513", 210.0, 8),
                ("FL003", "Tehran", "Istanbul", "2026-11-12", "09:00", "12:15", 195, "Mahan Air", "W5104", 280.0, 5),
                ("FL004", "Istanbul", "Tehran", "2026-11-17", "18:40", "21:55", 195, "Turkish Airlines", "TK874", 310.0, 10),
                ("FL005", "Istanbul", "Tehran", "2026-11-17", "22:05", "01:15", 190, "Pegasus", "PC514", 195.0, 15),
                ("FL006", "Tehran", "Dubai", "2026-11-10", "07:20", "09:50", 150, "Emirates", "EK978", 450.0, 6),
                ("FL007", "Tehran", "Dubai", "2026-11-11", "13:15", "15:45", 150, "Flydubai", "FZ192", 295.0, 18),
                ("FL008", "Dubai", "Tehran", "2026-11-18", "10:30", "13:00", 150, "Emirates", "EK979", 425.0, 9),
                ("FL009", "Tehran", "Doha", "2026-11-12", "06:45", "09:15", 150, "Qatar Airways", "QR499", 390.0, 7),
                ("FL010", "Doha", "Tehran", "2026-11-19", "16:20", "18:50", 150, "Qatar Airways", "QR498", 370.0, 11),
                ("FL011", "Tehran", "Baku", "2026-11-13", "08:00", "10:00", 120, "Iran Air", "IR452", 180.0, 14),
                ("FL012", "Baku", "Tehran", "2026-11-20", "12:40", "14:40", 120, "Azerbaijan Airlines", "J2145", 205.0, 4),
                ("FL013", "Tehran", "Yerevan", "2026-11-14", "09:25", "11:05", 100, "Armenia Airways", "6A712", 165.0, 16),
                ("FL014", "Yerevan", "Tehran", "2026-11-21", "17:10", "18:50", 100, "Armenia Airways", "6A713", 175.0, 13),
                ("FL015", "Tehran", "Tbilisi", "2026-11-15", "07:50", "10:20", 150, "Georgian Airways", "A9791", 230.0, 8),
                ("FL016", "Tbilisi", "Tehran", "2026-11-22", "14:30", "17:00", 150, "Georgian Airways", "A9792", 245.0, 6),
                ("FL017", "Tehran", "Ankara", "2026-11-16", "11:15", "14:20", 185, "Pegasus", "PC1736", 260.0, 19),
                ("FL018", "Ankara", "Tehran", "2026-11-23", "19:00", "22:05", 185, "Turkish Airlines", "TK788", 285.0, 3),
                ("FL019", "Tehran", "Paris", "2026-11-18", "05:30", "10:15", 315, "Air France", "AF738", 680.0, 10),
                ("FL020", "Paris", "Tehran", "2026-11-25", "12:00", "20:30", 300, "Lufthansa", "LH600", 720.0, 5),
                ("FL021", "Tehran", "Frankfurt", "2026-11-19", "06:20", "10:10", 280, "Lufthansa", "LH601", 590.0, 12),
                ("FL022", "Frankfurt", "Tehran", "2026-11-26", "15:45", "23:35", 290, "Austrian Airlines", "OS871", 615.0, 7),
                ("FL023", "Tehran", "London", "2026-11-20", "04:50", "09:15", 295, "British Airways", "BA152", 750.0, 9),
                ("FL024", "London", "Tehran", "2026-11-27", "13:10", "21:40", 330, "Lufthansa", "LH903", 710.0, 14),
                ("FL025", "Tehran", "Rome", "2026-11-21", "08:15", "12:00", 255, "ITA Airways", "AZ704", 480.0, 11),
                ("FL026", "Rome", "Tehran", "2026-11-28", "16:30", "00:15", 285, "Turkish Airlines", "TK1864", 455.0, 6),
                ("FL027", "Tehran", "Mumbai", "2026-11-22", "02:30", "08:15", 225, "IndiGo", "6E1708", 340.0, 17),
                ("FL028", "Mumbai", "Tehran", "2026-11-29", "10:40", "14:55", 225, "IndiGo", "6E1709", 355.0, 8),
                ("FL029", "Tehran", "Bangkok", "2026-11-24", "23:10", "07:30", 320, "Thai Airways", "TG527", 620.0, 4),
                ("FL030", "Bangkok", "Tehran", "2026-11-30", "11:20", "16:00", 310, "Qatar Airways", "QR831", 595.0, 13),
                ("FL031", "Tehran", "Kuala Lumpur", "2026-11-25", "01:45", "10:15", 300, "Malaysia Airlines", "MH451", 570.0, 15),
                ("FL032", "Kuala Lumpur", "Tehran", "2026-12-02", "14:20", "19:00", 310, "Malaysia Airlines", "MH450", 550.0, 9),
                ("FL033", "Tehran", "Tokyo", "2026-11-26", "00:30", "14:10", 490, "Japan Airlines", "JL720", 890.0, 5),
                ("FL034", "Tokyo", "Tehran", "2026-12-03", "16:00", "22:30", 510, "Japan Airlines", "JL721", 920.0, 7),
                ("FL035", "Tehran", "New Delhi", "2026-11-27", "09:10", "13:00", 200, "Air India", "AI952", 310.0, 20),
                ("FL036", "New Delhi", "Tehran", "2026-12-04", "15:30", "19:20", 200, "Air India", "AI953", 325.0, 12),
                ("FL037", "Tehran", "Moscow", "2026-11-28", "07:40", "11:20", 220, "Aeroflot", "SU513", 365.0, 10),
                ("FL038", "Moscow", "Tehran", "2026-12-05", "13:50", "17:30", 220, "Aeroflot", "SU514", 345.0, 8),
                ("FL039", "Tehran", "Vienna", "2026-11-29", "06:00", "09:50", 260, "Austrian Airlines", "OS872", 510.0, 6),
                ("FL040", "Vienna", "Tehran", "2026-12-06", "14:15", "22:05", 290, "Austrian Airlines", "OS873", 495.0, 16),
                ("FL041", "Tehran", "Zurich", "2026-11-30", "05:45", "10:05", 290, "Swiss International Air Lines", "LX184", 640.0, 7),
                ("FL042", "Zurich", "Tehran", "2026-12-07", "12:30", "20:40", 310, "Swiss International Air Lines", "LX185", 625.0, 10),
                ("FL043", "Tehran", "Athens", "2026-12-01", "08:35", "12:15", 220, "Aegean Airlines", "A3927", 380.0, 11),
                ("FL044", "Athens", "Tehran", "2026-12-08", "17:25", "22:55", 240, "Aegean Airlines", "A3928", 395.0, 4),
                ("FL045", "Tehran", "Beijing", "2026-12-02", "02:15", "11:30", 375, "Air China", "CA702", 720.0, 8),
                ("FL046", "Beijing", "Tehran", "2026-12-09", "14:45", "20:00", 375, "Air China", "CA703", 695.0, 13),
                ("FL047", "Tehran", "Singapore", "2026-12-03", "00:50", "12:30", 360, "Singapore Airlines", "SQ491", 780.0, 6),
                ("FL048", "Singapore", "Tehran", "2026-12-10", "15:10", "21:20", 370, "Singapore Airlines", "SQ492", 760.0, 9),
                ("FL049", "Tehran", "Kuwait City", "2026-12-04", "10:20", "12:15", 115, "Kuwait Airways", "KU516", 240.0, 18),
                ("FL050", "Kuwait City", "Tehran", "2026-12-11", "16:40", "18:35", 115, "Kuwait Airways", "KU517", 225.0, 7),
                ("FL051", "Tehran", "Istanbul", "2026-11-11", "06:00", "09:15", 195, "Turkish Airlines", "TK875", 305.0, 9),
                ("FL052", "Tehran", "Istanbul", "2026-11-11", "19:40", "22:55", 195, "Pegasus", "PC515", 199.0, 14),
                ("FL053", "Tehran", "Istanbul", "2026-11-13", "10:20", "13:35", 195, "Mahan Air", "W5106", 265.0, 7),
                ("FL054", "Istanbul", "Tehran", "2026-11-18", "07:15", "10:30", 195, "Turkish Airlines", "TK876", 300.0, 11),
                ("FL055", "Istanbul", "Tehran", "2026-11-19", "23:50", "03:05", 195, "Pegasus", "PC516", 185.0, 16),
                ("FL056", "Tehran", "Dubai", "2026-11-12", "08:00", "10:30", 150, "Emirates", "EK980", 430.0, 8),
                ("FL057", "Tehran", "Dubai", "2026-11-13", "22:10", "00:40", 150, "Flydubai", "FZ194", 275.0, 20),
                ("FL058", "Dubai", "Tehran", "2026-11-19", "15:20", "17:50", 150, "Emirates", "EK981", 410.0, 6),
                ("FL059", "Dubai", "Tehran", "2026-11-20", "01:00", "03:30", 150, "Flydubai", "FZ195", 260.0, 12),
                ("FL060", "Tehran", "Doha", "2026-11-14", "11:30", "14:00", 150, "Qatar Airways", "QR501", 375.0, 10),
                ("FL061", "Doha", "Tehran", "2026-11-21", "20:00", "22:30", 150, "Qatar Airways", "QR500", 355.0, 9),
                ("FL062", "Tehran", "Antalya", "2026-11-15", "05:40", "08:50", 190, "Pegasus", "PC1800", 245.0, 18),
                ("FL063", "Antalya", "Tehran", "2026-11-22", "21:10", "00:20", 190, "Pegasus", "PC1801", 235.0, 15),
                ("FL064", "Tehran", "Izmir", "2026-11-16", "09:00", "12:00", 180, "Turkish Airlines", "TK890", 255.0, 11),
                ("FL065", "Izmir", "Tehran", "2026-11-23", "16:30", "19:30", 180, "Turkish Airlines", "TK891", 250.0, 8),
                ("FL066", "Tehran", "Cairo", "2026-11-17", "04:20", "07:40", 200, "EgyptAir", "MS709", 360.0, 7),
                ("FL067", "Cairo", "Tehran", "2026-11-24", "14:00", "17:20", 200, "EgyptAir", "MS710", 350.0, 10),
                ("FL068", "Tehran", "Beirut", "2026-11-18", "12:45", "14:45", 120, "Middle East Airlines", "ME365", 290.0, 13),
                ("FL069", "Beirut", "Tehran", "2026-11-25", "18:00", "20:00", 120, "Middle East Airlines", "ME366", 285.0, 9),
                ("FL070", "Tehran", "Muscat", "2026-11-19", "07:10", "09:50", 160, "Oman Air", "WY234", 320.0, 6),
                ("FL071", "Muscat", "Tehran", "2026-11-26", "13:20", "16:00", 160, "Oman Air", "WY235", 310.0, 8),
                ("FL072", "Tehran", "Riyadh", "2026-11-20", "06:30", "08:40", 130, "Saudia", "SV501", 280.0, 14),
                ("FL073", "Riyadh", "Tehran", "2026-11-27", "17:50", "20:00", 130, "Saudia", "SV502", 270.0, 11),
                ("FL074", "Tehran", "Jeddah", "2026-11-21", "03:15", "06:00", 165, "Saudia", "SV510", 300.0, 12),
                ("FL075", "Jeddah", "Tehran", "2026-11-28", "22:40", "01:25", 165, "Saudia", "SV511", 295.0, 7),
                ("FL076", "Tehran", "Barcelona", "2026-11-22", "05:00", "10:30", 330, "Vueling", "VY7890", 520.0, 9),
                ("FL077", "Barcelona", "Tehran", "2026-11-29", "12:00", "21:00", 360, "Turkish Airlines", "TK1854", 505.0, 5),
                ("FL078", "Tehran", "Madrid", "2026-11-23", "04:40", "10:20", 340, "Iberia", "IB3456", 540.0, 8),
                ("FL079", "Madrid", "Tehran", "2026-11-30", "14:10", "23:00", 350, "Iberia", "IB3457", 530.0, 6),
                ("FL080", "Tehran", "Amsterdam", "2026-11-24", "06:10", "10:40", 270, "KLM", "KL433", 580.0, 10),
                ("FL081", "Amsterdam", "Tehran", "2026-12-01", "15:20", "23:30", 310, "KLM", "KL434", 565.0, 7),
                ("FL082", "Tehran", "Berlin", "2026-11-25", "07:00", "11:20", 260, "Lufthansa", "LH602", 500.0, 11),
                ("FL083", "Berlin", "Tehran", "2026-12-02", "13:40", "22:00", 320, "Lufthansa", "LH603", 490.0, 8),
                ("FL084", "Tehran", "Prague", "2026-11-26", "08:20", "12:00", 220, "Czech Airlines", "OK780", 420.0, 9),
                ("FL085", "Prague", "Tehran", "2026-12-03", "16:10", "23:40", 270, "Czech Airlines", "OK781", 410.0, 6),
                ("FL086", "Tehran", "Budapest", "2026-11-27", "05:50", "09:40", 230, "Wizz Air", "W62401", 380.0, 15),
                ("FL087", "Budapest", "Tehran", "2026-12-04", "18:30", "02:00", 270, "Wizz Air", "W62402", 370.0, 12),
                ("FL088", "Tehran", "Milan", "2026-11-28", "06:40", "10:50", 250, "ITA Airways", "AZ720", 460.0, 8),
                ("FL089", "Milan", "Tehran", "2026-12-05", "14:50", "23:00", 310, "ITA Airways", "AZ721", 450.0, 5),
                ("FL090", "Tehran", "Lisbon", "2026-11-29", "03:30", "10:00", 390, "TAP Air Portugal", "TP790", 610.0, 7),
                ("FL091", "Lisbon", "Tehran", "2026-12-06", "12:20", "22:40", 400, "TAP Air Portugal", "TP791", 600.0, 4),
                ("FL092", "Tehran", "Seoul", "2026-11-30", "01:00", "14:30", 510, "Korean Air", "KE958", 850.0, 6),
                ("FL093", "Seoul", "Tehran", "2026-12-07", "16:40", "22:10", 450, "Korean Air", "KE959", 830.0, 5),
                ("FL094", "Tehran", "Hong Kong", "2026-12-01", "02:40", "14:20", 460, "Cathay Pacific", "CX601", 800.0, 7),
                ("FL095", "Hong Kong", "Tehran", "2026-12-08", "15:00", "21:30", 450, "Cathay Pacific", "CX602", 785.0, 8),
                ("FL096", "Tehran", "Shanghai", "2026-12-02", "01:20", "12:50", 450, "China Eastern", "MU708", 740.0, 9),
                ("FL097", "Shanghai", "Tehran", "2026-12-09", "14:00", "20:30", 450, "China Eastern", "MU709", 725.0, 6),
                ("FL098", "Tehran", "Isfahan", "2026-12-03", "09:00", "10:10", 70, "Iran Air", "IR340", 95.0, 22),
                ("FL099", "Isfahan", "Tehran", "2026-12-10", "18:00", "19:10", 70, "Iran Air", "IR341", 90.0, 20),
                ("FL100", "Tehran", "Shiraz", "2026-12-04", "07:30", "09:00", 90, "Mahan Air", "W5100", 110.0, 18),

            ],
        )

    conn.executemany(
            """
            INSERT OR IGNORE INTO hotels
            (id, city, name, stars, price_per_night, rooms_available)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("HT001", "Istanbul", "Bosphorus View Hotel", 4, 95.0, 7),
                ("HT002", "Istanbul", "Sultanahmet Inn", 3, 55.0, 10),
                ("HT003", "Istanbul", "Galata Boutique", 4, 80.0, 4),
                ("HT004", "Istanbul", "Budget Stay Kadikoy", 2, 35.0, 12),
                ("HT005", "Istanbul", "Grand Pera Palace", 5, 180.0, 3),
                ("HT006", "Dubai", "Marina Bay Hotel", 4, 120.0, 8),
                ("HT007", "Dubai", "Desert Pearl Resort", 5, 250.0, 5),
                ("HT008", "Dubai", "Downtown Comfort Suites", 3, 75.0, 14),
                ("HT009", "Dubai", "Palm Horizon Hotel", 5, 310.0, 4),
                ("HT010", "Dubai", "Creekside Budget Inn", 2, 45.0, 16),
                ("HT011", "Tehran", "Persian Garden Hotel", 4, 85.0, 9),
                ("HT012", "Tehran", "Grand Azadi Residence", 5, 160.0, 6),
                ("HT013", "Tehran", "Central Avenue Inn", 3, 48.0, 15),
                ("HT014", "Tehran", "Niloofar Budget Hotel", 2, 30.0, 11),
                ("HT015", "Tehran", "Royal Saadatabad Suites", 4, 105.0, 5),
                ("HT016", "Baku", "Caspian Sea Grand Hotel", 5, 190.0, 4),
                ("HT017", "Baku", "Old City Boutique Stay", 4, 90.0, 7),
                ("HT018", "Baku", "Flame Towers Residence", 5, 220.0, 3),
                ("HT019", "Baku", "Nizami Street Hotel", 3, 60.0, 12),
                ("HT020", "Baku", "Seaside Budget Rooms", 2, 38.0, 10),
                ("HT021", "Paris", "Eiffel Garden Suites", 5, 280.0, 3),
                ("HT022", "Paris", "Montmartre Boutique Hotel", 4, 145.0, 6),
                ("HT023", "Paris", "Left Bank Comfort Inn", 3, 95.0, 11),
                ("HT024", "Paris", "Petit Louvre Stay", 2, 65.0, 14),
                ("HT025", "Paris", "Champs Elysees Palace", 5, 350.0, 2),
                ("HT026", "London", "Royal Westminster Hotel", 5, 320.0, 4),
                ("HT027", "London", "Thames View Suites", 4, 180.0, 6),
                ("HT028", "London", "Covent Garden Inn", 3, 110.0, 9),
                ("HT029", "London", "Paddington Budget Lodge", 2, 70.0, 13),
                ("HT030", "London", "Kensington Park Hotel", 4, 155.0, 5),
                ("HT031", "Rome", "Colosseum Heritage Hotel", 5, 230.0, 3),
                ("HT032", "Rome", "Trastevere Boutique Stay", 4, 125.0, 7),
                ("HT033", "Rome", "Via Veneto Comfort Hotel", 3, 85.0, 10),
                ("HT034", "Rome", "Roman Holiday Inn", 2, 50.0, 12),
                ("HT035", "Tokyo", "Shinjuku Skyline Hotel", 5, 260.0, 4),
                ("HT036", "Tokyo", "Sakura Garden Suites", 4, 170.0, 6),
                ("HT037", "Tokyo", "Shibuya City Inn", 3, 105.0, 9),
                ("HT038", "Tokyo", "Asakusa Budget Rooms", 2, 55.0, 15),
                ("HT039", "Bangkok", "Orchid River Resort", 5, 175.0, 5),
                ("HT040", "Bangkok", "Sukhumvit Grand Hotel", 4, 90.0, 8),
                ("HT041", "Bangkok", "Golden Temple Inn", 3, 45.0, 13),
                ("HT042", "Bangkok", "Chao Phraya Budget Stay", 2, 28.0, 17),
                ("HT043", "Tbilisi", "Old Town Heritage Hotel", 4, 85.0, 7),
                ("HT044", "Tbilisi", "Mtatsminda Grand Suites", 5, 140.0, 4),
                ("HT045", "Tbilisi", "Rustaveli City Inn", 3, 50.0, 12),
                ("HT046", "Yerevan", "Ararat View Hotel", 5, 155.0, 3),
                ("HT047", "Yerevan", "Cascade Boutique Suites", 4, 95.0, 6),
                ("HT048", "Yerevan", "Republic Square Inn", 3, 55.0, 10),
                ("HT049", "Vienna", "Imperial Vienna Palace", 5, 290.0, 2),
                ("HT050", "Vienna", "Danube Comfort Hotel", 4, 135.0, 8),
                ("HT051", "Istanbul", "Taksim Square Hotel", 4, 88.0, 9),
                ("HT052", "Istanbul", "Balat Riverside Inn", 3, 52.0, 11),
                ("HT053", "Istanbul", "Uskudar Sea Lodge", 3, 60.0, 8),
                ("HT054", "Istanbul", "Nisantasi Design Hotel", 5, 200.0, 3),
                ("HT055", "Istanbul", "Aksaray Transit Stay", 2, 32.0, 16),
                ("HT056", "Dubai", "JBR Beach Suites", 4, 140.0, 7),
                ("HT057", "Dubai", "Business Bay Tower Hotel", 4, 115.0, 10),
                ("HT058", "Dubai", "Al Fahidi Heritage Inn", 3, 68.0, 12),
                ("HT059", "Dubai", "World Islands Resort", 5, 360.0, 2),
                ("HT060", "Dubai", "Deira Metro Budget", 2, 40.0, 18),
                ("HT061", "Tehran", "Valiasr Boutique Hotel", 4, 92.0, 8),
                ("HT062", "Tehran", "Tajrish Hill Suites", 4, 110.0, 5),
                ("HT063", "Tehran", "Enghelab City Inn", 3, 45.0, 14),
                ("HT064", "Tehran", "Mehrabad Transit Lodge", 2, 28.0, 20),
                ("HT065", "Antalya", "Lara Beach Resort", 5, 210.0, 6),
                ("HT066", "Antalya", "Kaleici Old Town Hotel", 4, 95.0, 9),
                ("HT067", "Antalya", "Konyaalti Budget Stay", 2, 40.0, 15),
                ("HT068", "Izmir", "Kordon Seaside Hotel", 4, 100.0, 7),
                ("HT069", "Izmir", "Alsancak City Inn", 3, 58.0, 11),
                ("HT070", "Cairo", "Nile View Palace", 5, 175.0, 4),
                ("HT071", "Cairo", "Zamalek Boutique", 4, 95.0, 8),
                ("HT072", "Cairo", "Downtown Cairo Inn", 3, 50.0, 13),
                ("HT073", "Beirut", "Corniche Grand Hotel", 5, 190.0, 3),
                ("HT074", "Beirut", "Hamra Street Suites", 4, 105.0, 6),
                ("HT075", "Muscat", "Muttrah Harbour Hotel", 4, 130.0, 5),
                ("HT076", "Muscat", "Qurum Beach Inn", 3, 70.0, 10),
                ("HT077", "Riyadh", "Kingdom Tower Suites", 5, 240.0, 4),
                ("HT078", "Riyadh", "Olaya Business Hotel", 4, 120.0, 8),
                ("HT079", "Jeddah", "Red Sea Corniche Hotel", 5, 200.0, 3),
                ("HT080", "Jeddah", "Balad Heritage Inn", 3, 65.0, 12),
                ("HT081", "Barcelona", "Gothic Quarter Hotel", 4, 150.0, 6),
                ("HT082", "Barcelona", "Sagrada Vista Suites", 5, 260.0, 3),
                ("HT083", "Barcelona", "El Raval Budget Stay", 2, 55.0, 14),
                ("HT084", "Madrid", "Gran Via Grand Hotel", 5, 240.0, 4),
                ("HT085", "Madrid", "Retiro Park Inn", 4, 130.0, 7),
                ("HT086", "Amsterdam", "Canal House Boutique", 4, 175.0, 5),
                ("HT087", "Amsterdam", "Museumplein Suites", 3, 110.0, 9),
                ("HT088", "Berlin", "Mitte Design Hotel", 4, 140.0, 8),
                ("HT089", "Berlin", "Kreuzberg Urban Inn", 3, 85.0, 12),
                ("HT090", "Prague", "Charles Bridge Hotel", 5, 195.0, 3),
                ("HT091", "Prague", "Old Town Square Inn", 4, 115.0, 7),
                ("HT092", "Budapest", "Danube Bank Suites", 4, 120.0, 6),
                ("HT093", "Budapest", "Ruin Bar District Inn", 3, 70.0, 11),
                ("HT094", "Milan", "Duomo Luxury Hotel", 5, 280.0, 2),
                ("HT095", "Milan", "Navigli Boutique Stay", 4, 145.0, 5),
                ("HT096", "Lisbon", "Alfama Hill Hotel", 4, 125.0, 6),
                ("HT097", "Lisbon", "Belem River Inn", 3, 80.0, 10),
                ("HT098", "Seoul", "Myeongdong Central Hotel", 4, 130.0, 8),
                ("HT099", "Hong Kong", "Victoria Harbour Suites", 5, 290.0, 3),
                ("HT100", "Shanghai", "Bund Heritage Hotel", 5, 220.0, 4),

            ],
        )

    conn.commit()


def reset_db(db_path: Path | None = None) -> None:
    """Delete the DB file and recreate schema + seed data from scratch."""
    path = db_path or DB_PATH
    if path.exists():
        path.unlink()
    with get_connection(path) as conn:
        init_db(conn)
        seed_if_empty(conn)
