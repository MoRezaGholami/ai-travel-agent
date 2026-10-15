from __future__ import annotations
import json 
import uuid

from datetime import date , datetime
from pathlib import Path

from .database import get_connection , init_db , seed_if_empty


from .models import FlightOffer , HotelOffer , Booking






def _parse_date(value : str) -> date :
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"Invalid date format: {value}") from e



def _night_between(check_in : str , check_out : str) -> int:
    start = _parse_date(check_in)
    end = _parse_date(check_out)

    nights = (end - start).days
    if nights < 1:
        raise ValueError("Check-out date must be after check-in date")
    return nights





class TravelService:
    def __init__(self . db_path : Path |None = None):
        self.db_path = db_path
        with get_connection(self.db_path) as conn:
            init_db(conn)
            seed_if_empty(conn)




    def searech_flights(self , origin : str | None = None , destination : str |None = None , departure_date : str |None = None , max_price : float |None = None , only_available : bool = True  ) -> list[Flight]:
        clauses = list[str] = []
        params = list[object] = []


        if origin:
            clauses.append("LOWER(origin) = LOWER(?)")
            params.append(origin.strip())

        if destination:
            clauses.append("LOWER(destination) = LOWER(?)")
            params.append(destination.strip())

        if departure_date:
            clauses.append("departure_date = ?")
            params.append(departure_date)

        if max_price is not None:
            clauses.append("price <= ?")
            params.append(max_price)

        if only_available:
            clauses.append("seats_available > 0")


        where = f"WHERE {' AND '.join(clauses)}" if clauses else "
        sql = f"SELECT * FROM flights {where} ORDER BY price ASC"
        with get_connection(self.db_path) as conn:
            rows= conn.execute(sql , params).fetchall()
        return [self._row_to_flight(row) for row in rows]



    def search_hotels(self , city : str , check_in  :str , check_out : str , rooms : int = 1 , max_price_per_night : float | None =None , min_stars : int |None = None , only_available : bool = True  ) -> list[HotelOffer]:

        if rooms < 1 :
            raise ValueError("Rooms must be at least 1")
        nights = _night_between(check_in , check_out)
        clauses = list[str] = []
        params = list[object] = []
        if city:
            clauses.append("LOWER(city) = LOWER(?)")
            params.append(city.strip())
        if max_price_per_night is not None:
            clauses.append("price_per_night <= ?")
            params.append(max_price_per_night)
        if min_stars is not None:
            clauses.append("stars >= ?")
            params.append(min_stars)
        if only_available:
            clauses.append("rooms_available > 0")
            params.append(rooms)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else "
        sql = f"SELECT * FROM hotels {where} ORDER BY price_per_night ASC"
        with get_connection(self.db_path) as conn:
            rows= conn.execute(sql , params).fetchall()


        offers = list[HotelOffer] = []
        for row in rows : 
            price_per_night = float(row["price_per_night"])
            offers.append(HotelOffer(
                id = row["id"],
                name = row["name"],
                city = row["city"],
                stars = int(row["stars"]),
                check_in = check_in,
                check_out = check_out , 
                nights = nights ,
                rooms = rooms ,
                price_per_night = price_per_night,
                total_price = price_per_night * nights * rooms,
                rooms_available = int(row["rooms_available"]),

            ))

        return offers




    def create_booking(
        self,
        booking_type: str,
        item_id: str,
        user_name: str,
        *,
        check_in: str | None = None,
        check_out: str | None = None,
        rooms: int = 1,
    ) -> Booking:

        booking_type = booking_type.lower().strip()
        if booking_type not in ["flight" , "hotel"] :
            raise ValueError(f"Invalid booking type: {booking_type}")
        if not user_name.strip():
            raise ValueError("User name is required")


        with get_connection(self.db_path) as conn:
            if booking_type == "flight":
                row = conn.execute("SELECT * FROM flights WHERE id = ?" , (item_id ,)).fetchone()
                if row is None : 
                    raise ValueError(f"Flight not found: {item_id}")
                if row["seats_available"] <= 0:
                    raise ValueError(f"flight {item_id} is sold out!")

                total_price = float(row["price"])
                                details = {
                        "origin": row["origin"],
                        "destination": row["destination"],
                        "departure_date": row["departure_date"],
                        "departure_time": row["departure_time"],
                        "arrival_time": row["arrival_time"],
                        "duration_minutes": int(row["duration_minutes"]),
                        "airline": row["airline"],
                        "flight_number": row["flight_number"],
                        "seats": 1,
                    }
                    conn.execute("UPDATE flights SET seats_available = seats_available - 1 WHERE id = ?" , (item_id ,))


            else : 
                if not check_in or not check_out:
                    raise ValueError("Check-in and check-out dates are required for hotel bookings")
                if rooms < 1:
                    raise ValueError("Rooms must be at least 1")
                nights = _night_between(check_in , check_out)
                row = conn.execute("SELECT * FROM hotels WHERE id = ?" , (item_id ,)).fetchone()
                if row is None :
                    raise ValueError(f"Hotel not found: {item_id}")

                if row["rooms_available"] < rooms:
                    raise ValueError(f"Hotel {item_id} has only {row['rooms_available']} rooms available")
                total_price = float(row["price_per_night"]) * nights * rooms
                details = {
                    "hotel_name": row["name"],
                    "city": row["city"],
                    "stars": int(row["stars"]),
                    "check_in": check_in,
                    "check_out": check_out,
                    "nights": nights,
                    "rooms": rooms,
                    "price_per_night": price_per_night,
                }

                conn.execute("UPDATE hotels SET rooms_available = rooms_available - ? WHERE id = ?" , (rooms , item_id))



            booking_id = f"BK-{uuid.uuid4().hex[:8].upper()}"
            created_at = datetime.now(timezone.utc).isoformat()


            conn.execute(
                """
                INSERT INTO bookings
                (id, booking_type, item_id, user_name, status,
                    total_price, details_json, created_at)
                VALUES (?, ?, ?, ?, 'confirmed', ?, ?, ?)
                """,
                (
                    booking_id,
                    booking_type,
                    item_id,
                    user_name.strip(),
                    total_price,
                    json.dumps(details, ensure_ascii=False),
                    created_at,
                ),
            )
            conn.commit()

            return Booking(
                id = booking_id,
                booking_type = booking_type,
                item_id = item_id,
                user_name = user_name.strip(),
                status = "confirmed",
                total_price = total_price,
                created_at = created_at,
                details = details,
                
            )

    @staticmethod
    def _row_to_booking(row: object) -> Booking:
        r = dict(row)  # type: ignore[arg-type]
        return Booking(
            id=r["id"],
            booking_type=r["booking_type"],
            item_id=r["item_id"],
            user_name=r["user_name"],
            status=r["status"],
            total_price=float(r["total_price"]),
            created_at=r["created_at"],
            details=json.loads(r["details_json"]),
        )


    
    