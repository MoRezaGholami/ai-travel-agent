from __future__ import annotations
import json 
import uuid

from datetime import date , datetime
from pathlib import Path

from .database import get_connection , init_db , seed_if_empty


from .models import FlightOffer , HotelOffer , Booking






# def _parse_date(value : str) -> date :
#     try:
#         return date.fromisoformat(value)
#     except ValueError as e:
#         raise ValueError(f"Invalid date format: {value}") from e



# def _night_between(check_in : str , check_out : str) -> int:
#     start = _parse_date(check_in)
#     end = _parse_date(check_out)

#     nights = (end - start).days
#     if nights < 1:
#         raise ValueError("Check-out date must be after check-in date")
#     return nights





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

        



   @staticmethod
   def _row_to_flight(row : object) -> FlightOffer:
    r= dict(row)
    return FlightOffer(
        id = r["id"],
        origin = r["origin"],
        destination = r["destination"],
        departure_date = r["departure_date"],
        departure_time = r["departure_time"],
        arrival_time = r["arrival_time"],
        duration_minutes = int(r["duration_minutes"]),
        airline = r["airline"],
        flight_number = r["flight_number"],
        price = float(r["price"]),
        seats_available = int(r["seats_available"]),

    )

    
    